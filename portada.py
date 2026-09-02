"""Genera la imagen de portada (Open Graph) de cada pieza, como PNG.

Era SVG hasta el 2026-09-02, y ese era el fallo: **ninguna red social
renderiza SVG en una tarjeta**. Ni LinkedIn, ni X, ni Facebook, ni WhatsApp,
ni Slack. Durante los primeros días los 4 sitios se compartieron exactamente
igual que si no tuvieran imagen — que es justo lo que esta pieza existía para
evitar. Se dibuja el mismo diseño con Pillow y se escribe PNG, que sí
renderizan todas.

De paso desaparece el peor apaño del módulo: para partir el título en líneas
había que ESTIMAR el ancho de cada carácter (`ANCHO_CAR = TAM_TITULO * 0.60`,
ajustado a ojo porque "con 0.52 el título se salía"). Pillow mide el texto de
verdad, así que ahora se parte por su ancho real y el tamaño baja solo cuando
un título no cabe, en vez de recortarlo con puntos suspensivos.

Por qué dibujarlo aquí y no con un proveedor de imagen de pago:
  - 0€ y sin clave de API de la que depender durante 10 meses.
  - Determinista: una llamada de generación de imagen que falla te deja la
    pieza sin portada y no te enteras hasta que alguien comparte el enlace.
  - Evita el problema de simetría ya cerrado en el diseño: cualquier
    proveedor de imagen de una de las cuatro casas (Anthropic/OpenAI/Google/
    DeepSeek) le daría ventaja de integración a esa IA.
  - Refuerza la identidad visual propia de cada agente, que ya es parte del
    diseño del experimento.

Lo que resuelve una portada aquí es concreto: que el enlace no se comparta
como un bloque de texto gris en LinkedIn. Para eso, tipografía grande y buen
contraste basta — no hace falta una ilustración.

Si más adelante se ve que la portada mueve clics, la imagen generada por IA
es una mejora encima de esto, no un requisito para arrancar.
"""
import io
import re
from pathlib import Path

from PIL import Image, ImageDraw

import tipografia

ANCHO, ALTO = 1200, 630

# Color de cada agente: los mismos slots categóricos que usa el dashboard,
# para que una pieza compartida se reconozca como suya de un vistazo.
COLOR_IA = {
    "claude": "#2a78d6",
    "gpt": "#eb6834",
    "gemini": "#1baf7a",
    "deepseek": "#eda100",
}
NOMBRE_IA = {"claude": "Claude", "gpt": "GPT", "gemini": "Gemini", "deepseek": "DeepSeek"}

FONDO = "#12120f"
TEXTO = "#ffffff"
TEXTO_2 = "#b9b8ae"

# El título arranca a 58 y baja de escalón si no cabe en 4 líneas. Antes
# había un único tamaño y lo que no cabía se cortaba con "…": perder la mitad
# de un titular en la tarjeta es peor que enseñarlo dos puntos más pequeño.
TAMANOS_TITULO = (58, 52, 46, 40)
MAX_LINEAS = 4
MARGEN = 80
ANCHO_TEXTO = ANCHO - MARGEN * 2


def _ancho(texto: str, fuente) -> int:
    return int(fuente.getbbox(texto)[2] - fuente.getbbox(texto)[0])


def _partir(titulo: str, fuente, max_lineas: int = MAX_LINEAS) -> list[str] | None:
    """Parte el título por el ancho REAL del texto. Devuelve None si no cabe
    en `max_lineas` a ese tamaño, para que el llamador pruebe uno menor."""
    lineas, actual = [], ""
    for palabra in titulo.split():
        prueba = f"{actual} {palabra}".strip()
        if _ancho(prueba, fuente) <= ANCHO_TEXTO:
            actual = prueba
            continue
        if actual:
            lineas.append(actual)
        # Una palabra sola más ancha que la línea entera (una URL, un nombre
        # técnico): se parte en duro, mejor que desbordar la imagen.
        while _ancho(palabra, fuente) > ANCHO_TEXTO:
            corte = len(palabra)
            while corte > 1 and _ancho(palabra[:corte] + "-", fuente) > ANCHO_TEXTO:
                corte -= 1
            lineas.append(palabra[:corte] + "-")
            palabra = palabra[corte:]
        actual = palabra
        if len(lineas) > max_lineas:
            return None
    if actual:
        lineas.append(actual)
    if len(lineas) > max_lineas:
        return None
    return lineas or ["Sin título"]


def _rgb(hexa: str) -> tuple[int, int, int]:
    hexa = hexa.lstrip("#")
    return tuple(int(hexa[i:i + 2], 16) for i in (0, 2, 4))


def generar(titulo: str, ia: str, sitio: str = "") -> bytes:
    """La tarjeta de una pieza, en PNG listo para escribir a disco."""
    color = _rgb(COLOR_IA.get(ia, "#2a78d6"))
    nombre = NOMBRE_IA.get(ia, ia)
    titulo = titulo.strip() or "Sin título"

    for tam in TAMANOS_TITULO:
        f_titulo = tipografia.fuente(tam, negrita=True)
        lineas = _partir(titulo, f_titulo)
        if lineas:
            break
    else:
        # Ni al más pequeño: se recorta, que es el último recurso.
        tam = TAMANOS_TITULO[-1]
        f_titulo = tipografia.fuente(tam, negrita=True)
        lineas = (_partir(titulo, f_titulo, max_lineas=99) or ["Sin título"])[:MAX_LINEAS]
        lineas[-1] = lineas[-1].rstrip(" .,;:") + "…"

    img = Image.new("RGB", (ANCHO, ALTO), _rgb(FONDO))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, ANCHO, 10], fill=color)

    # El bloque de título se centra en el hueco entre la barra y el pie, para
    # que un título de una línea no quede flotando arriba.
    interlineado = tam + 14
    alto_bloque = len(lineas) * interlineado
    y = (ALTO - 90 - alto_bloque) / 2 + 10
    for linea in lineas:
        d.text((MARGEN, y), linea, font=f_titulo, fill=_rgb(TEXTO))
        y += interlineado

    f_pie = tipografia.fuente(26, negrita=True)
    f_pie_2 = tipografia.fuente(26)
    y_pie = ALTO - 78
    d.ellipse([MARGEN, y_pie + 6, MARGEN + 24, y_pie + 30], fill=color)
    x = MARGEN + 38
    d.text((x, y_pie), nombre, font=f_pie, fill=_rgb(TEXTO))
    x += _ancho(nombre, f_pie) + 12
    d.text((x, y_pie), "escribe esto sin supervisión humana", font=f_pie_2, fill=_rgb(TEXTO_2))

    if sitio:
        d.text((ANCHO - MARGEN, y_pie + 1), sitio, font=tipografia.fuente(24),
               fill=_rgb(TEXTO_2), anchor="ra")

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _slug(nombre_archivo: str) -> str:
    return re.sub(r"[^a-z0-9-]", "-", Path(nombre_archivo).stem.lower()).strip("-") or "portada"


def escribir_para(repo_dir: Path, archivos: list[str], ia: str, base_url: str = "") -> list[str]:
    """Crea `og/<slug>.png` para cada HTML del turno que tenga <title>.
    Devuelve las rutas relativas creadas, para que el llamador las incluya en
    el mismo commit que el contenido."""
    creados = []
    sitio = base_url.replace("https://", "").replace("http://", "").rstrip("/")
    for rel in archivos:
        if not rel.endswith(".html"):
            continue
        ruta = repo_dir / rel
        if not ruta.exists():
            continue
        contenido = ruta.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"<title>(.*?)</title>", contenido, re.IGNORECASE | re.DOTALL)
        if not m or not m.group(1).strip():
            continue
        destino = repo_dir / "og" / f"{_slug(rel)}.png"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(generar(m.group(1).strip(), ia, sitio))
        creados.append(destino.relative_to(repo_dir).as_posix())
    return creados
