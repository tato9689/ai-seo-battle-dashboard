#!/usr/bin/env python3
"""Pone el `og:image` correcto en TODAS las páginas publicadas de un sitio.

Dos fallos que arregla, encontrados el 2026-08-30 y el 2026-09-02:

1. El esqueleto propone `og.png` como marcador de "aquí va tu imagen
   1200x630" y ningún agente genera ese fichero: el enlace se compartía con
   la imagen a 404.
2. Peor: **los artículos no declaraban `og:image` en absoluto**, solo la
   portada. Y los artículos son justo lo que se comparte y donde aterriza el
   tráfico de buscador. Ahora se recorre el sitio entero.

La imagen es la PNG que dibuja `portada.py` para esa misma página
(`og/<slug>.png`), con la portada del sitio como recambio si esa pieza no
tiene la suya. PNG y no SVG desde el 2026-09-02: ninguna red social
renderiza SVG en una tarjeta (ver el docstring de `portada.py`).

Se aplica al $DESTINO ya publicado y no al repo, mismo motivo que
`verificacion.py`: el agente reescribe sus HTML enteros cada turno y se
llevaría el arreglo por delante si viviera solo en el commit.

Uso: og_image.py <ia> [raiz_web]
"""
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent
RE_OG_IMAGE = re.compile(
    r'\s*<meta\s+(?:property|name)=["\'](?:og:image(?::(?:width|height|alt))?|twitter:image)["\'][^>]*>',
    re.IGNORECASE)


def _slug(nombre_archivo: str) -> str:
    """Mismo slug que portada.py, o la página buscaría una imagen que no
    existe con otro nombre."""
    return re.sub(r"[^a-z0-9-]", "-", Path(nombre_archivo).stem.lower()).strip("-") or "portada"


def etiquetas(url: str) -> str:
    # width/height le ahorran a la red social tener que descargar la imagen
    # para saber cómo maquetar la tarjeta, y twitter:image es lo que mira X
    # cuando no encuentra og:image (algunos clientes solo miran esa).
    return (f'<meta property="og:image" content="{url}">\n'
            f'  <meta property="og:image:width" content="1200">\n'
            f'  <meta property="og:image:height" content="630">\n'
            f'  <meta name="twitter:image" content="{url}">')


def aplicar(ia: str, raiz: Path, base_url: str) -> tuple[int, int]:
    """Devuelve (páginas corregidas, páginas sin imagen que ofrecer)."""
    og_dir = raiz / "og"
    portada_sitio = "index.png" if (og_dir / "index.png").exists() else None
    corregidas = sin_imagen = 0

    for pagina in sorted(raiz.rglob("*.html")):
        propia = f"{_slug(pagina.name)}.png"
        elegida = propia if (og_dir / propia).exists() else portada_sitio
        if not elegida:
            sin_imagen += 1
            continue
        html = pagina.read_text(encoding="utf-8", errors="ignore")
        if "<head>" not in html:
            continue
        # Se quita cualquier og:image previa (rota o no) antes de poner la
        # buena: si se acumulan dos, gana la primera y puede ser la mala.
        limpio = RE_OG_IMAGE.sub("", html)
        url = f"{base_url}/og/{elegida}"
        nuevo = limpio.replace("<head>", f"<head>\n  {etiquetas(url)}", 1)
        if nuevo != html:
            pagina.write_text(nuevo, encoding="utf-8")
            corregidas += 1
    return corregidas, sin_imagen


if __name__ == "__main__":
    ia = sys.argv[1]
    dominio = (BASE / ".dominio").read_text(encoding="utf-8").strip()
    raiz = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(f"/var/www/{ia}.{dominio}")
    base_url = f"https://{ia}.{dominio}"
    corregidas, sin_imagen = aplicar(ia, raiz, base_url)
    aviso = f", {sin_imagen} sin imagen que ofrecer" if sin_imagen else ""
    print(f"[{ia}] og:image puesta en {corregidas} páginas de {raiz}{aviso}")
