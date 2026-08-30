"""Lector de feeds RSS/Atom por URL arbitraria, simétrico para las 4.

Pedido real en la auditoría de herramientas del 2026-08-30: Claude quería
un lector de los feeds de release de su nicho (OrcaSlicer, PrusaSlicer,
firmware Bambu) para no publicar sobre un material o un slicer sin saber
si la versión por defecto cambió; DeepSeek pidió específicamente la API de
GitHub Releases para sus paquetes (Home Assistant, Zigbee2MQTT, ESPHome,
Matter). Un lector de feeds genérico cubre las dos peticiones con una sola
herramienta: GitHub ya publica `.../releases.atom` para cualquier repo, así
que "lee este feed" es el superconjunto de "lee este release de GitHub".

Simétrico por construcción: cada IA elige sus propias URLs (hasta
MAX_FEEDS por turno), nadie tiene una fuente que las otras no puedan pedir
igual. Sin API key, sin coste — son feeds públicos.

Uso: python feeds.py <url> [otra_url ...]
"""
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from lxml import etree

TIMEOUT = 15
MAX_FEEDS = 3
MAX_ENTRADAS_POR_FEED = 5

# Espacios de nombres de Atom — RSS 2.0 no usa namespace, así que las rutas
# sin prefijo cubren ambos formatos con el mismo XPath.
_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _texto(el) -> str:
    return (el.text or "").strip() if el is not None else ""


def _parsear_atom(root) -> list[dict]:
    entradas = []
    for entry in root.findall("atom:entry", _NS)[:MAX_ENTRADAS_POR_FEED]:
        link_el = entry.find("atom:link", _NS)
        entradas.append({
            "titulo": _texto(entry.find("atom:title", _NS)),
            "url": (link_el.get("href") if link_el is not None else "") or "",
            "fecha": _texto(entry.find("atom:updated", _NS)) or _texto(entry.find("atom:published", _NS)),
            "resumen": (_texto(entry.find("atom:summary", _NS)) or _texto(entry.find("atom:content", _NS)))[:1500],
        })
    return entradas


def _parsear_rss(root) -> list[dict]:
    canal = root.find("channel")
    if canal is None:
        return []
    entradas = []
    for item in canal.findall("item")[:MAX_ENTRADAS_POR_FEED]:
        entradas.append({
            "titulo": _texto(item.find("title")),
            "url": _texto(item.find("link")),
            "fecha": _texto(item.find("pubDate")),
            "resumen": _texto(item.find("description"))[:1500],
        })
    return entradas


def leer_feed(url: str) -> dict:
    """Devuelve {'url', 'entradas': [...]}, o {'url', 'error'} si falla —
    un feed caído no debe tumbar el turno, igual que busqueda.py/imagenes.py."""
    host = urlparse(url).hostname or ""
    if not host or urlparse(url).scheme not in {"http", "https"}:
        return {"url": url, "error": "URL inválida"}
    try:
        resp = httpx.get(
            url, timeout=TIMEOUT, follow_redirects=True,
            headers={"User-Agent": "AI-SEO-Battle-feed-reader/1.0"},
        )
        resp.raise_for_status()
        root = etree.fromstring(resp.content)
    except Exception as e:
        return {"url": url, "error": str(e)}

    tag = etree.QName(root).localname if root.tag.startswith("{") else root.tag
    if tag == "feed":
        entradas = _parsear_atom(root)
    elif tag == "rss":
        entradas = _parsear_rss(root)
    else:
        return {"url": url, "error": f"formato no reconocido (raíz: {tag})"}

    return {"url": url, "entradas": entradas}


def leer_varios(urls: list[str]) -> dict:
    return {u: leer_feed(u) for u in urls[:MAX_FEEDS]}


if __name__ == "__main__":
    import json
    urls = sys.argv[1:] or ["https://github.com/bambulab/BambuStudio/releases.atom"]
    print(f"# consultado el {datetime.now(timezone.utc).isoformat()}", file=sys.stderr)
    print(json.dumps(leer_varios(urls), indent=2, ensure_ascii=False))
