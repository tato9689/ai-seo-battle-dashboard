"""La tarjeta social del marcador: 1200×630 PNG dibujado con los datos de hoy.

Por qué PNG y no SVG: los cuatro subdominios comparten su `og:image` como
SVG (`og/index.svg`) y ni LinkedIn, ni X, ni Facebook, ni WhatsApp renderizan
SVG en una tarjeta — el enlace sale sin imagen. Aquí se paga el coste de
rasterizar para que el enlace del marcador, que es el que se comparte cuando
alguien cuenta el experimento, salga con imagen en todas partes.

Y por qué generada y no fija: la tarjeta enseña quién va ganando en el
momento en que se comparte. Una portada estática diría "hay un experimento";
esta dice "van 12-9-4-2 y Claude lidera", que es lo que hace que alguien
pinche.
"""
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
FONDO = (18, 18, 17)
TEXTO = (255, 255, 255)
TEXTO_2 = (168, 167, 158)
BORDE = (52, 52, 47)
COLORES = {"claude": (57, 135, 229), "gpt": (217, 89, 38),
           "gemini": (25, 158, 112), "deepseek": (201, 133, 0)}

_FUENTES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans{}.ttf",
]
_cache: dict[str, bytes] = {}


def _fuente(tam: int, negrita: bool = False):
    for patron in _FUENTES:
        ruta = Path(patron.format("-Bold" if negrita else ""))
        if ruta.exists():
            return ImageFont.truetype(str(ruta), tam)
    return ImageFont.load_default(tam)


def generar(filas: list[dict], dias: int, firma: str) -> bytes:
    """`filas` es el leaderboard ya ordenado: ia, organicos, coste. `firma`
    identifica el estado de los datos — mientras no cambie, se reutiliza el
    PNG ya dibujado en vez de volver a rasterizar en cada compartido."""
    if firma in _cache:
        return _cache[firma]

    img = Image.new("RGB", (W, H), FONDO)
    d = ImageDraw.Draw(img)

    d.text((72, 68), "AI SEO BATTLE", font=_fuente(26, True), fill=TEXTO_2)
    d.text((72, 108), "Cuatro IAs compiten", font=_fuente(62, True), fill=TEXTO)
    d.text((72, 180), "por suscriptores reales", font=_fuente(62, True), fill=TEXTO)
    d.text((72, 262), "Cada una gestiona su propia web y decide sola. Sin nadie que revise.",
           font=_fuente(25), fill=TEXTO_2)

    y = 336
    fila_h = 58
    maximo = max([f.get("organicos") or 0 for f in filas] or [0]) or 1
    for i, f in enumerate(filas[:4]):
        c = COLORES.get(f["ia"], (120, 120, 120))
        d.rounded_rectangle([72, y + 8, 96, y + 32], radius=6, fill=c)
        d.text((112, y + 6), f.get("etiqueta", f["ia"]), font=_fuente(30, True), fill=TEXTO)
        # La barra empieza donde acaba el nombre más largo, no donde acaba
        # cada nombre: si cada barra arranca en un sitio, no se pueden comparar.
        x0, x1 = 320, 972
        org = f.get("organicos") or 0
        d.rounded_rectangle([x0, y + 12, x1, y + 28], radius=8, fill=(38, 38, 36))
        if org:
            ancho = x0 + max(16, int((x1 - x0) * org / maximo))
            d.rounded_rectangle([x0, y + 12, ancho, y + 28], radius=8, fill=c)
        # Cifra anclada por la derecha: con 0 y con 128 la columna sigue
        # cuadrada y "subs" nunca se come el número.
        d.text((1062, y + 6), str(org), font=_fuente(30, True), fill=TEXTO, anchor="ra")
        d.text((1074, y + 14), "subs", font=_fuente(19), fill=TEXTO_2)
        if i < 3:
            d.line([72, y + fila_h - 4, 1128, y + fila_h - 4], fill=BORDE, width=1)
        y += fila_h

    d.line([72, 578, 1128, 578], fill=BORDE, width=1)
    pie = f"retoseo.com · marcador en vivo · día {dias}" if dias else "retoseo.com · marcador en vivo"
    d.text((72, 592), pie, font=_fuente(22), fill=TEXTO_2)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    datos = buf.getvalue()
    # Una entrada por estado de los datos; el estado cambia como mucho una vez
    # cada poll, así que el diccionario no crece sin control dentro del día.
    if len(_cache) > 24:
        _cache.clear()
    _cache[firma] = datos
    return datos
