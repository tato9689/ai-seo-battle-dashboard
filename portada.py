"""Genera la imagen de portada (Open Graph) de cada pieza, como SVG.

Por qué SVG en el servidor y no un proveedor de imagen de pago:
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
import html
import re
from pathlib import Path

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

TAM_TITULO = 58
# Ancho medio de un carácter a ese tamaño en una grotesca en negrita. No hay
# motor de texto aquí para medir de verdad, así que se estima — y se estima
# ALTO a propósito: pasarse de ancho saca el texto fuera de la imagen, mientras
# que quedarse corto solo deja algo más de margen. Con 0.52 el título se salía.
ANCHO_CAR = TAM_TITULO * 0.60
MAX_CAR = int((ANCHO - 160) / ANCHO_CAR)
MAX_LINEAS = 4


def _partir(titulo: str, max_car: int = MAX_CAR, max_lineas: int = MAX_LINEAS) -> list[str]:
    palabras = titulo.split()
    lineas, actual = [], ""
    for palabra in palabras:
        prueba = f"{actual} {palabra}".strip()
        if len(prueba) <= max_car:
            actual = prueba
            continue
        if actual:
            lineas.append(actual)
        # Una palabra sola más larga que la línea entera (una URL, un nombre
        # técnico) se corta en duro: mejor eso que desbordar la imagen.
        while len(palabra) > max_car:
            lineas.append(palabra[:max_car - 1] + "-")
            palabra = palabra[max_car - 1:]
        actual = palabra
        if len(lineas) >= max_lineas:
            break
    if actual and len(lineas) < max_lineas:
        lineas.append(actual)
    lineas = lineas[:max_lineas]
    if lineas and len(" ".join(lineas)) < len(titulo):
        lineas[-1] = lineas[-1].rstrip(" .,;:") + "…"
    return lineas or ["Sin título"]


def generar(titulo: str, ia: str, sitio: str = "") -> str:
    color = COLOR_IA.get(ia, "#2a78d6")
    nombre = NOMBRE_IA.get(ia, ia)
    lineas = _partir(titulo.strip())

    # El bloque de título se centra verticalmente en el espacio libre entre la
    # barra superior y el pie, para que un título de una línea no quede
    # flotando arriba y uno de cuatro no se coma el pie.
    alto_bloque = len(lineas) * (TAM_TITULO + 14)
    y0 = (ALTO - alto_bloque) / 2 + TAM_TITULO - 10

    tspans = "".join(
        f'<tspan x="80" y="{y0 + i * (TAM_TITULO + 14):.0f}">{html.escape(l)}</tspan>'
        for i, l in enumerate(lineas)
    )
    pie = html.escape(sitio) if sitio else ""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{ANCHO}" height="{ALTO}" viewBox="0 0 {ANCHO} {ALTO}" role="img" aria-label="{html.escape(titulo)}">
  <rect width="{ANCHO}" height="{ALTO}" fill="{FONDO}"/>
  <rect x="0" y="0" width="{ANCHO}" height="10" fill="{color}"/>
  <text font-family="Inter, Helvetica, Arial, sans-serif" font-size="{TAM_TITULO}" font-weight="700" fill="{TEXTO}" letter-spacing="-1.2">{tspans}</text>
  <g font-family="Inter, Helvetica, Arial, sans-serif" font-size="26">
    <circle cx="92" cy="{ALTO - 68}" r="12" fill="{color}"/>
    <!-- Nombre y coletilla en un solo <text> con tspans: calcular la x del
         segundo a ojo hacía que "GPT" dejara un hueco y "DeepSeek" se comiera
         la palabra siguiente. Con dx lo espacia el propio renderizador. -->
    <text x="118" y="{ALTO - 59}" fill="{TEXTO}" font-weight="600">{html.escape(nombre)}<tspan dx="12" fill="{TEXTO_2}" font-weight="400">escribe esto sin supervisión humana</tspan></text>
  </g>
  <text x="{ANCHO - 80}" y="{ALTO - 59}" text-anchor="end" font-family="Inter, Helvetica, Arial, sans-serif" font-size="24" fill="{TEXTO_2}">{pie}</text>
</svg>
"""


def _slug(nombre_archivo: str) -> str:
    return re.sub(r"[^a-z0-9-]", "-", Path(nombre_archivo).stem.lower()).strip("-") or "portada"


def escribir_para(repo_dir: Path, archivos: list[str], ia: str, base_url: str = "") -> list[str]:
    """Crea `og/<slug>.svg` para cada HTML del turno que tenga <title>.
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
        destino = repo_dir / "og" / f"{_slug(rel)}.svg"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(generar(m.group(1).strip(), ia, sitio), encoding="utf-8")
        creados.append(destino.relative_to(repo_dir).as_posix())
    return creados
