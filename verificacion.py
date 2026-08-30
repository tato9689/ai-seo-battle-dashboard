#!/usr/bin/env python3
"""Mete la etiqueta de verificación de Search Console en el index.html ya
publicado de un agente.

Va aquí y no en el prompt del agente a propósito. La verificación es
infraestructura del dueño del dominio, no contenido: si dependiera de que la
IA reescriba bien la etiqueta en cada turno, bastaría un carácter cambiado
para que Google desverifique la propiedad semanas después, en silencio y sin
que nadie mire. Determinista y gratis es mejor que confiable y caro.

Uso: verificacion.py <ia> [raiz_web]
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent
RE_ETIQUETA = re.compile(
    r'\s*<meta\s+name=["\']google-site-verification["\'][^>]*>', re.IGNORECASE)


def aplicar(ia: str, raiz: Path) -> bool:
    tokens = json.loads((BASE / "verificacion_gsc.json").read_text(encoding="utf-8"))
    token = tokens.get(ia)
    if not token:
        return False
    index = raiz / "index.html"
    if not index.exists():
        return False
    html = index.read_text(encoding="utf-8")
    etiqueta = f'<meta name="google-site-verification" content="{token}">'
    # Se quita cualquier etiqueta previa antes de poner la buena: si el agente
    # copió una vieja o la escribió a medias, quedarían dos y Google usa la
    # primera que encuentra.
    limpio = RE_ETIQUETA.sub("", html)
    if "<head>" not in limpio:
        return False
    index.write_text(limpio.replace("<head>", f"<head>\n  {etiqueta}", 1), encoding="utf-8")
    return True


if __name__ == "__main__":
    ia = sys.argv[1]
    dominio = (BASE / ".dominio").read_text(encoding="utf-8").strip()
    raiz = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(f"/var/www/{ia}.{dominio}")
    print(f"[{ia}] verificación {'puesta' if aplicar(ia, raiz) else 'NO aplicada'} en {raiz}")
