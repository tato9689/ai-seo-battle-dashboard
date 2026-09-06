"""Genera sitemap.xml y rss.xml de un agente leyendo su propio repo.

Determinista y gratis: ni una llamada a la API. La alternativa era pedirle a
cada IA que mantuviera el XML a mano en cada turno — más tokens, y un feed
mal formado es de los errores que no se ven hasta que Search Console se
queja semanas después.

Se llama desde cron_agente.py tras aplicar los cambios del turno, antes de
commitear, para que el feed viaje en el mismo commit que el contenido.
"""
import html
import re
from datetime import datetime, timezone
from pathlib import Path

RE_TITLE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
RE_META_DESC = re.compile(
    r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', re.IGNORECASE | re.DOTALL
)

# Páginas que no son contenido: no van al RSS (sí al sitemap, salvo las
# legales, que no aportan nada en resultados de búsqueda).
NO_SON_ARTICULOS = {"index.html", "log.html", "privacidad.html", "404.html"}
FUERA_DEL_SITEMAP = {"privacidad.html", "404.html"}

# Carpetas de infraestructura (plantillas/componentes del sistema de diseño,
# no piezas editoriales) que alguna IA puede decidir meter dentro del árbol
# servido. Detectado 2026-09-06: deepseek publicó `/componentes/` y
# `/plantillas/` ahí, y como este generador no las excluía, un sitemap
# recorriendo TODO el .html del repo (línea de abajo) las mandó a Google como
# si fueran contenido — una de ellas encima marcada noindex en su propio
# <head>, contradicción que Search Console reporta como ruido de cobertura.
CARPETAS_SIN_CONTENIDO = ("componentes/", "plantillas/")
RE_ROBOTS_NOINDEX = re.compile(r'<meta\s+name=["\']robots["\'][^>]*noindex', re.IGNORECASE)


def _url_publica(base_url: str, rel: str) -> str:
    """index.html -> /  ·  guia-x.html -> /guia-x  (URLs limpias, sin .html)"""
    base = base_url.rstrip("/")
    if rel == "index.html":
        return base + "/"
    return f"{base}/{rel[:-5]}" if rel.endswith(".html") else f"{base}/{rel}"


def _paginas(repo_dir: Path) -> list[tuple[str, str, str, datetime]]:
    """(ruta_relativa, título, descripción, fecha de última modificación)."""
    encontradas = []
    for ruta in sorted(repo_dir.rglob("*.html")):
        rel = ruta.relative_to(repo_dir).as_posix()
        if rel.startswith(".") or "/." in rel:
            continue
        if rel.startswith(CARPETAS_SIN_CONTENIDO):
            continue
        contenido = ruta.read_text(encoding="utf-8", errors="ignore")
        if RE_ROBOTS_NOINDEX.search(contenido):
            continue
        m = RE_TITLE.search(contenido)
        titulo = m.group(1).strip() if m else rel
        m = RE_META_DESC.search(contenido)
        descripcion = m.group(1).strip() if m else ""
        modificado = datetime.fromtimestamp(ruta.stat().st_mtime, tz=timezone.utc)
        encontradas.append((rel, titulo, descripcion, modificado))
    return encontradas


def generar_sitemap(repo_dir: Path, base_url: str) -> str:
    entradas = []
    for rel, _titulo, _desc, modificado in _paginas(repo_dir):
        if rel in FUERA_DEL_SITEMAP:
            continue
        entradas.append(
            "  <url>\n"
            f"    <loc>{html.escape(_url_publica(base_url, rel))}</loc>\n"
            f"    <lastmod>{modificado.date().isoformat()}</lastmod>\n"
            "  </url>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entradas)
        + "\n</urlset>\n"
    )


def generar_rss(repo_dir: Path, base_url: str, nombre_sitio: str, descripcion_sitio: str) -> str:
    articulos = [
        (rel, titulo, desc, mod)
        for rel, titulo, desc, mod in _paginas(repo_dir)
        if rel not in NO_SON_ARTICULOS
    ]
    # Más recientes primero, y con tope: un feed enorme es lento de leer para
    # los agregadores y no aporta nada.
    articulos.sort(key=lambda x: x[3], reverse=True)
    articulos = articulos[:50]

    items = []
    for rel, titulo, desc, modificado in articulos:
        url = _url_publica(base_url, rel)
        items.append(
            "    <item>\n"
            f"      <title>{html.escape(titulo)}</title>\n"
            f"      <link>{html.escape(url)}</link>\n"
            f"      <guid isPermaLink=\"true\">{html.escape(url)}</guid>\n"
            f"      <description>{html.escape(desc)}</description>\n"
            f"      <pubDate>{modificado.strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>\n"
            "    </item>"
        )

    base = base_url.rstrip("/")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        f"    <title>{html.escape(nombre_sitio)}</title>\n"
        f"    <link>{html.escape(base)}/</link>\n"
        f"    <description>{html.escape(descripcion_sitio)}</description>\n"
        "    <language>es</language>\n"
        f'    <atom:link href="{html.escape(base)}/rss.xml" rel="self" type="application/rss+xml"/>\n'
        f"    <lastBuildDate>{datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>\n"
        + "\n".join(items)
        + "\n  </channel>\n</rss>\n"
    )


def escribir_feeds(repo_dir: Path, base_url: str) -> list[str]:
    """Escribe/actualiza sitemap.xml y rss.xml. Devuelve qué archivos tocó.
    Si el subdominio aún no existe (base_url con placeholder), no hace nada:
    un feed lleno de URLs 'PENDIENTE-DOMINIO' es peor que no tener feed."""
    if not base_url or "PENDIENTE" in base_url:
        return []

    index = repo_dir / "index.html"
    contenido_index = index.read_text(encoding="utf-8", errors="ignore") if index.exists() else ""
    m = RE_TITLE.search(contenido_index)
    nombre = m.group(1).strip() if m else "AI SEO Battle"
    m = RE_META_DESC.search(contenido_index)
    descripcion = m.group(1).strip() if m else ""

    (repo_dir / "sitemap.xml").write_text(generar_sitemap(repo_dir, base_url), encoding="utf-8")
    (repo_dir / "rss.xml").write_text(
        generar_rss(repo_dir, base_url, nombre, descripcion), encoding="utf-8"
    )
    return ["sitemap.xml", "rss.xml"]
