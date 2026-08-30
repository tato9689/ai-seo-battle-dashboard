#!/usr/bin/env python3
"""Avisa a los buscadores de las URLs nuevas de un agente vía IndexNow.

Va del lado del sistema y no del agente: es simétrico por construcción (los
cuatro se anuncian igual, sin que ninguno pueda anunciarse más) y determinista.
En 10 meses la velocidad de indexación pesa más que una pieza extra, y una
web recién nacida sin enlaces entrantes puede tardar semanas en que la
rastreen sola.

Bing, Yandex, Seznam y Naver consumen IndexNow. Google no participa: para
Google el que cuenta es el sitemap, que ya genera generar_feeds.py.

Uso: indexnow.py <ia>
"""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

BASE = Path(__file__).parent
CLAVE_PATH = BASE / ".indexnow-key"


def clave() -> str:
    """Una sola clave para los cuatro: el fichero de verificación se sirve
    desde cada host, que es lo que IndexNow comprueba."""
    if not CLAVE_PATH.exists():
        import uuid
        CLAVE_PATH.write_text(uuid.uuid4().hex, encoding="utf-8")
    return CLAVE_PATH.read_text(encoding="utf-8").strip()


def urls_del_sitemap(raiz: Path) -> list[str]:
    sitemap = raiz / "sitemap.xml"
    if not sitemap.exists():
        return []
    try:
        arbol = ET.parse(sitemap).getroot()
    except ET.ParseError:
        return []
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [loc.text.strip() for loc in arbol.findall(".//s:loc", ns) if loc.text]


def avisar(ia: str, dominio: str, raiz: Path) -> str:
    host = f"{ia}.{dominio}"
    k = clave()
    # El fichero de verificación tiene que estar servido ANTES del aviso.
    (raiz / f"{k}.txt").write_text(k, encoding="utf-8")
    urls = urls_del_sitemap(raiz)[:100]
    if not urls:
        return "sin sitemap todavía, nada que anunciar"
    try:
        resp = httpx.post(
            "https://api.indexnow.org/indexnow",
            json={"host": host, "key": k, "keyLocation": f"https://{host}/{k}.txt", "urlList": urls},
            timeout=20,
        )
        return f"{len(urls)} urls anunciadas (HTTP {resp.status_code})"
    except Exception as e:
        return f"no se pudo anunciar: {e}"


if __name__ == "__main__":
    ia = sys.argv[1]
    dominio = (BASE / ".dominio").read_text(encoding="utf-8").strip()
    raiz = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(f"/var/www/{ia}.{dominio}")
    print(f"[{ia}] indexnow: {avisar(ia, dominio, raiz)}")
