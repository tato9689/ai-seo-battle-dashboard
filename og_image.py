#!/usr/bin/env python3
"""Apunta el og:image del index.html publicado al SVG real que genera
`portada.py`, en vez de al `/og.png` de ejemplo que trae el esqueleto.

Iba a existir sin uso real: el esqueleto propone `og.png` como marcador de
"aquí va tu imagen 1200x630", pero ningún agente genera ese fichero — lo que
sí existe siempre es `og/index.svg`, que `portada.py` escribe en cada turno
que toca el index. Sin este guardarraíl los 4 sitios compartían un enlace
"roto" en redes (og:image a 404, o sin la etiqueta directamente) — detectado
el 2026-08-30. Mismo patrón que `verificacion.py`: se aplica al $DESTINO ya
publicado, no al repo, porque el agente reescribe su index.html entero cada
turno y se llevaría el arreglo por delante si viviera solo en el commit.

Uso: og_image.py <ia> [raiz_web]
"""
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent
RE_OG_IMAGE = re.compile(r'\s*<meta\s+property=["\']og:image["\'][^>]*>', re.IGNORECASE)


def aplicar(ia: str, raiz: Path, base_url: str) -> bool:
    if not (raiz / "og" / "index.svg").exists():
        return False
    index = raiz / "index.html"
    if not index.exists():
        return False
    html = index.read_text(encoding="utf-8")
    etiqueta = f'<meta property="og:image" content="{base_url}/og/index.svg">'
    # Se quita cualquier og:image previo (roto o no) antes de poner el bueno,
    # mismo motivo que verificacion.py: si se acumulan dos, gana el primero.
    limpio = RE_OG_IMAGE.sub("", html)
    if "<head>" not in limpio:
        return False
    index.write_text(limpio.replace("<head>", f"<head>\n  {etiqueta}", 1), encoding="utf-8")
    return True


if __name__ == "__main__":
    ia = sys.argv[1]
    dominio = (BASE / ".dominio").read_text(encoding="utf-8").strip()
    raiz = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(f"/var/www/{ia}.{dominio}")
    base_url = f"https://{ia}.{dominio}"
    print(f"[{ia}] og:image {'corregido' if aplicar(ia, raiz, base_url) else 'NO aplicado'} en {raiz}")
