"""Carga de fuentes para las imágenes que dibuja el sistema.

Vive suelto porque lo usan dos procesos que no se conocen: `portada.py` (las
og:image de los 4 sitios, dentro del turno de cada agente) y
`dashboard/tarjeta_og.py` (la tarjeta social del marcador). Tener la lista de
rutas en dos sitios significaba que el día que falte una fuente en el sistema,
una de las dos se arregla y la otra no.
"""
from pathlib import Path

from PIL import ImageFont

# En orden de preferencia. DejaVu viene en cualquier Debian/Ubuntu y cubre
# acentos y "ñ", que es el requisito real aquí: los 4 sitios escriben en
# español y un título con "ñ" partido en cuadraditos arruina la tarjeta.
FAMILIAS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans{}.ttf",
]


def fuente(tam: int, negrita: bool = False):
    for patron in FAMILIAS:
        ruta = Path(patron.format("-Bold" if negrita else ""))
        if ruta.exists():
            return ImageFont.truetype(str(ruta), tam)
    # Sin ninguna instalada, la de PIL: fea pero legible. Una tarjeta fea es
    # mejor que un turno que revienta por no encontrar un .ttf.
    return ImageFont.load_default(tam)
