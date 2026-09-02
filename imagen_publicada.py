#!/usr/bin/env python3
"""Decide qué imagen sirve cada página y deja lista su miniatura.

El cable que faltaba. Hasta el 2026-09-02 había cuatro subsistemas de imagen
que no se hablaban: `portada.py` dibujaba una tarjeta de texto, la matriz
generaba imágenes de verdad con OpenAI y Gemini, `og_image.py` repartía la
`og:image`... y repartía siempre la tarjeta de texto. Las imágenes generadas
se pagaban, se guardaban en `og/matriz/` y no las enlazaba ninguna página, así
que las columnas de CTR de la matriz no podían llenarse con nada que
significara algo: 2 filas generadas, 0 medidas.

Este módulo pone la jerarquía y produce dos derivados de la MISMA imagen,
cada uno dimensionado para su trabajo:

  og/<slug>.jpg           1200x630 — la tarjeta social, cuando gana una imagen
                          generada. Si no hay, sirve la og/<slug>.png de
                          portada.py y este fichero no existe.
  og/miniatura/<slug>.jpg  640x336 — la miniatura de portada. SIEMPRE existe
                          para toda página con contenido, salga de una imagen
                          generada o de la tarjeta de texto.

Por qué dos ficheros y no uno: la og:image no está dentro de la página, así
que puede pesar; la miniatura sí, y se pinta a ~400px de ancho. Servir un
1200x630 como miniatura es cargar cuatro veces los píxeles que se ven, en la
única imagen que sí toca el LCP. Es la misma imagen, cortada para cada sitio.

Qué generador se publica: se elige por hash del slug, así que **no cambia
nunca para un mismo artículo**. Eso es lo que hace medible la matriz — si la
imagen servida cambiara a mitad de camino, las impresiones acumuladas no se
podrían atribuir a ninguna de las dos. Y como el hash reparte, ambos
generadores acaban acumulando datos sobre nichos distintos.

Uso: imagen_publicada.py <ia> [raiz_web]
"""
import hashlib
import sys
from pathlib import Path

from PIL import Image

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
from db import get_conn  # noqa: E402

SOCIAL = (1200, 630)
MINIATURA = (640, 336)
# 82 para la social y 78 para la miniatura: por encima de eso el JPEG crece
# rápido sin que se note, y la miniatura tiene que competir con el LCP.
CALIDAD_SOCIAL = 82
CALIDAD_MINIATURA = 78

# Páginas que no son contenido: no llevan miniatura porque nadie las lista.
NO_SON_PIEZAS = {"index", "log", "privacidad"}


def _recortar(origen: Path, destino: Path, tam: tuple[int, int], calidad: int) -> bool:
    """Redimensiona cubriendo el marco y recortando el sobrante, centrado.

    `cover` y no `contain` a propósito: una miniatura con franjas de relleno
    en una rejilla de portada rompe la alineación de todas las demás. Se
    prefiere perder un poco de los bordes a que la retícula baile.
    """
    try:
        with Image.open(origen) as img:
            img = img.convert("RGB")
            objetivo = tam[0] / tam[1]
            actual = img.width / img.height
            if actual > objetivo:
                nuevo = int(img.height * objetivo)
                izq = (img.width - nuevo) // 2
                img = img.crop((izq, 0, izq + nuevo, img.height))
            elif actual < objetivo:
                nuevo = int(img.width / objetivo)
                arriba = (img.height - nuevo) // 2
                img = img.crop((0, arriba, img.width, arriba + nuevo))
            img = img.resize(tam, Image.LANCZOS)
            destino.parent.mkdir(parents=True, exist_ok=True)
            img.save(destino, format="JPEG", quality=calidad, optimize=True, progressive=True)
        return True
    except (OSError, ValueError) as e:
        print(f"    no se pudo procesar {origen.name}: {e}", file=sys.stderr)
        return False


def _generada_de(ia: str, slug: str) -> tuple[Path | None, int | None, str]:
    """La imagen generada que debe servir este artículo, si hay alguna.

    Devuelve (ruta, id de la fila, generador). El generador se elige por hash
    del slug para que sea estable en el tiempo y esté repartido entre
    artículos.
    """
    conn = get_conn()
    filas = conn.execute(
        "SELECT id, generador, ruta_local FROM imagenes_matriz"
        " WHERE ia=? AND slug=? AND resultado='exito' AND ruta_local IS NOT NULL"
        " ORDER BY generador", (ia, slug)).fetchall()
    disponibles = [f for f in filas if Path(f["ruta_local"]).exists()]
    if not disponibles:
        conn.close()
        return None, None, ""
    i = int(hashlib.sha256(slug.encode("utf-8")).hexdigest(), 16) % len(disponibles)
    elegida = disponibles[i]
    # La fila publicada se marca aquí y no al generar: hasta que esta función
    # no elige, no hay ninguna publicada. medir() solo mira las marcadas.
    conn.execute("UPDATE imagenes_matriz SET publicada=0 WHERE ia=? AND slug=?", (ia, slug))
    conn.execute("UPDATE imagenes_matriz SET publicada=1 WHERE id=?", (elegida["id"],))
    conn.commit()
    conn.close()
    return Path(elegida["ruta_local"]), elegida["id"], elegida["generador"]


def aplicar(ia: str, raiz: Path) -> dict:
    """Recorre las páginas publicadas y deja cada imagen en su sitio."""
    og = raiz / "og"
    resumen = {"generadas": 0, "de_tarjeta": 0, "sin_fuente": 0}
    for pagina in sorted(raiz.rglob("*.html")):
        slug = pagina.stem
        if slug in NO_SON_PIEZAS:
            continue
        generada, _, generador = _generada_de(ia, slug)
        if generada:
            # Gana la imagen de verdad: se escribe la social en JPEG y
            # og_image.py la prefiere sobre la tarjeta de texto.
            if _recortar(generada, og / f"{slug}.jpg", SOCIAL, CALIDAD_SOCIAL):
                _recortar(generada, og / "miniatura" / f"{slug}.jpg", MINIATURA, CALIDAD_MINIATURA)
                resumen["generadas"] += 1
                print(f"    {slug}: imagen de {generador}")
                continue
        tarjeta = og / f"{slug}.png"
        if tarjeta.exists():
            # Sin imagen generada, la miniatura sale de la tarjeta de texto:
            # menos vistosa, pero una portada con huecos es peor que una
            # portada con tarjetas.
            if _recortar(tarjeta, og / "miniatura" / f"{slug}.jpg", MINIATURA, CALIDAD_MINIATURA):
                resumen["de_tarjeta"] += 1
                continue
        resumen["sin_fuente"] += 1
    return resumen


if __name__ == "__main__":
    ia = sys.argv[1]
    if len(sys.argv) > 2:
        raiz = Path(sys.argv[2])
    else:
        dominio = (BASE / ".dominio").read_text(encoding="utf-8").strip()
        raiz = Path(f"/var/www/{ia}.{dominio}")
    r = aplicar(ia, raiz)
    print(f"[{ia}] miniaturas: {r['generadas']} de imagen generada, "
          f"{r['de_tarjeta']} de tarjeta de texto, {r['sin_fuente']} sin fuente")
