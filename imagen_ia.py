#!/usr/bin/env python3
"""Generadores de imagen detrás de una sola interfaz, para la matriz cruzada.

La pregunta del experimento no es "qué IA hace mejores imágenes" —eso ya está
contestado y aburre— sino qué PAREJA funciona: quien escribe el prompt no
tiene por qué ser quien lo dibuja. Con 4 diseñadores y 2 generadores hay 8
combinaciones, y cada una se sigue hasta el CTR en `imagenes_matriz`.

Para que la comparación signifique algo, las dos APIs se llaman con el MISMO
prompt, el MISMO tamaño y ninguna instrucción extra por proveedor: en cuanto
se le añade a una un "y hazlo bonito" que la otra no lleva, la matriz mide el
andamiaje en vez de los modelos.

Claves, deliberadamente aparte de las del motor SEO para que un pico de gasto
en imágenes no toque el presupuesto de los turnos:
    OPENAI_IMAGE_API_KEY
    GEMINI_IMAGE_API_KEY
Si falta una, ese generador queda "no disponible" y la matriz corre con el
otro. Nunca es motivo de fallo de un turno: una imagen que no sale es una
imagen que no sale.
"""
import base64
import os
import time

import httpx

TIMEOUT = 180
# La og:image final es 1200x630 (1.91:1), pero NINGUNA de las dos APIs la
# genera nativamente: OpenAI solo admite 1024x1024, 1024x1536 y 1536x1024, y
# los modelos de imagen de Gemini devuelven lo que les parece. Así que cada
# una genera en lo más cercano que sabe y las DOS pasan por el mismo recorte
# centrado y la misma compresión. Tratarlas distinto aquí sería medir el
# andamiaje en vez de los modelos.
OG_ANCHO, OG_ALTO = 1200, 630
TAMANO_OPENAI = "1536x1024"

# Modelos fijados a propósito: si uno cambia de versión por su cuenta, las
# filas viejas de la matriz dejan de ser comparables con las nuevas y no habría
# forma de saberlo. Al subirlos, se anota la fecha y se compara solo dentro de
# cada tramo.
MODELO_OPENAI = "gpt-image-1"
# No es un modelo Imagen: esta clave da acceso a los modelos de imagen de
# Gemini por `generateContent`, no al endpoint `:predict` de Imagen — eso
# devolvía 404 y parecía un nombre de modelo mal escrito. Se elige el pro
# para que compita de tú a tú con gpt-image-1; el flash costaría menos pero
# entonces la matriz mediría gamas distintas.
MODELO_GEMINI = "gemini-3-pro-image"


class NoDisponible(RuntimeError):
    """El generador no tiene clave o no está configurado."""


def _clave(nombre: str) -> str:
    v = os.environ.get(nombre, "").strip()
    if not v:
        raise NoDisponible(f"falta {nombre} en el entorno")
    return v


def generar_openai(prompt: str) -> dict:
    clave = _clave("OPENAI_IMAGE_API_KEY")
    t0 = time.monotonic()
    resp = httpx.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {clave}", "Content-Type": "application/json"},
        json={"model": MODELO_OPENAI, "prompt": prompt, "size": TAMANO_OPENAI, "n": 1},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    datos = resp.json()["data"][0]
    crudo = base64.b64decode(datos["b64_json"]) if "b64_json" in datos else httpx.get(datos["url"], timeout=TIMEOUT).content
    return {"bytes": crudo, "modelo": MODELO_OPENAI, "segundos": round(time.monotonic() - t0, 2)}


def generar_gemini(prompt: str) -> dict:
    clave = _clave("GEMINI_IMAGE_API_KEY")
    t0 = time.monotonic()
    resp = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO_GEMINI}:generateContent",
        headers={"x-goog-api-key": clave, "Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"imageConfig": {"aspectRatio": "16:9"}}},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    partes = resp.json()["candidates"][0]["content"]["parts"]
    crudo = next(
        (base64.b64decode(p["inlineData"]["data"]) for p in partes if "inlineData" in p),
        None)
    if crudo is None:
        texto = " ".join(p.get("text", "") for p in partes)[:200]
        raise RuntimeError(f"Gemini no devolvió imagen: {texto or 'respuesta vacía'}")
    return {"bytes": crudo, "modelo": MODELO_GEMINI, "segundos": round(time.monotonic() - t0, 2)}


# 300 KB, tope duro. Una og:image la descarga el rastreador de cada red social
# y de cada buscador, muchas veces, para algo que se ve a 500 px de ancho en un
# timeline. Un PNG de 1200x630 recién salido de estas APIs pesa entre 1 y 2 MB:
# unas 5 veces más de lo que aporta. Y no es solo peso — Twitter/X y WhatsApp
# descartan la vista previa por encima de ciertos tamaños, así que una imagen
# demasiado grande no es una imagen pesada, es una imagen que no se ve.
MAX_BYTES = 300 * 1024


def _comprimir(crudo: bytes, tope: int = MAX_BYTES) -> tuple[bytes, str]:
    """Deja la imagen por debajo del tope. Devuelve (bytes, formato).

    WebP primero, que para fotografía da la mitad de tamaño que JPEG a igual
    calidad y lo entienden todas las redes desde hace años. Se baja la calidad
    por pasos y, solo si ni al mínimo entra, se reduce el ancho: perder nitidez
    es preferible a perder encuadre, porque el recorte cambia la composición
    que el diseñador pidió y entonces la fila de la matriz ya no mide el prompt
    que se escribió.

    Nunca lanza por no poder comprimir: si algo va mal devuelve el original y
    el guardarraíl lo cazará después. Fallar aquí tiraría la imagen entera."""
    from io import BytesIO

    from PIL import Image

    try:
        img = Image.open(BytesIO(crudo))
        img.load()
    except Exception:
        return crudo, "png"
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Recorte centrado a la proporción de og:image ANTES de comprimir: cada
    # API entrega la suya (3:2 en OpenAI, 16:9 en Gemini) y una vista previa
    # con la proporción equivocada se ve con bandas o recortada por la red
    # social, que decide por ti dónde cortar. Mejor decidirlo aquí, igual para
    # las dos.
    objetivo = OG_ANCHO / OG_ALTO
    actual_prop = img.width / img.height
    if abs(actual_prop - objetivo) > 0.01:
        if actual_prop > objetivo:      # demasiado ancha: recorto a los lados
            nuevo_ancho = round(img.height * objetivo)
            izq = (img.width - nuevo_ancho) // 2
            img = img.crop((izq, 0, izq + nuevo_ancho, img.height))
        else:                            # demasiado alta: recorto arriba y abajo
            nuevo_alto = round(img.width / objetivo)
            arriba = (img.height - nuevo_alto) // 2
            img = img.crop((0, arriba, img.width, arriba + nuevo_alto))
    if img.width > OG_ANCHO:
        img = img.resize((OG_ANCHO, OG_ALTO), Image.LANCZOS)

    for ancho in (img.width, 1200, 1000, 800):
        actual = img if ancho >= img.width else img.resize(
            (ancho, round(img.height * ancho / img.width)), Image.LANCZOS)
        for calidad in (88, 80, 72, 64, 55, 45):
            buf = BytesIO()
            actual.save(buf, format="WEBP", quality=calidad, method=6)
            datos = buf.getvalue()
            if len(datos) <= tope:
                return datos, "webp"
    return datos, "webp"  # el más pequeño que hemos conseguido


GENERADORES = {"openai": generar_openai, "gemini": generar_gemini}

# Precio por imagen, en dólares. Va aquí y no calculado por tokens porque
# estas APIs cobran por imagen y tamaño, no por token. Revisar al cambiar de
# modelo: un precio desactualizado en la matriz es peor que ninguno, porque
# nadie lo duda.
PRECIO_USD = {"openai": 0.04, "gemini": 0.03}


def disponibles() -> list[str]:
    """Qué generadores tienen clave ahora mismo. Sin llamar a nadie."""
    salida = []
    for nombre in GENERADORES:
        try:
            _clave("OPENAI_IMAGE_API_KEY" if nombre == "openai" else "GEMINI_IMAGE_API_KEY")
            salida.append(nombre)
        except NoDisponible:
            pass
    return salida


def generar(generador: str, prompt: str) -> dict:
    """Devuelve {bytes, modelo, segundos, coste_usd}. Lanza NoDisponible si no
    hay clave; deja subir cualquier otro error para que quien llama decida."""
    if generador not in GENERADORES:
        raise ValueError(f"generador desconocido: {generador!r}")
    r = GENERADORES[generador](prompt)
    r["coste_usd"] = PRECIO_USD.get(generador)
    r["bytes_originales"] = len(r["bytes"])
    if len(r["bytes"]) > MAX_BYTES:
        r["bytes"], r["formato"] = _comprimir(r["bytes"])
    else:
        r["formato"] = "png"
    r["comprimida"] = r["bytes_originales"] != len(r["bytes"])
    return r


if __name__ == "__main__":
    import sys
    disp = disponibles()
    print(f"generadores con clave: {disp or 'ninguno'}")
    if len(sys.argv) > 2:
        r = generar(sys.argv[1], sys.argv[2])
        destino = f"/tmp/prueba-{sys.argv[1]}.png"
        with open(destino, "wb") as fh:
            fh.write(r["bytes"])
        print(f"{destino}  {len(r['bytes'])} bytes  {r['segundos']}s  ${r['coste_usd']}")
