"""Filtro automático de guardarraíles: checks deterministas y baratos (sin
LLM de por medio) enganchados en cron_agente.py::ejecutar() justo antes de
escribir/commitear. Checklist cerrada en el diseño del proyecto: enlaces
rotos, duplicación de contenido entre páginas propias, canibalización de
keywords (title/meta-description repetidos), metadatos básicos, y validez
de JSON-LD si existe. Factualidad/alucinación quedan fuera a propósito —
requerirían un LLM-juez, que dobla coste y puede fallar también.

Uso: validar(repo_dir, archivos_nuevos) -> (bloqueantes, avisos). Un solo
bloqueante impide el commit del turno completo; los avisos se registran
pero no bloquean.
"""
import json
import os
import re
from difflib import SequenceMatcher
from pathlib import Path

_RE_TITLE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_RE_META_DESC = re.compile(
    r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', re.IGNORECASE | re.DOTALL
)
_RE_HREF_SRC = re.compile(r'(?:href|src)=["\']([^"\']+)["\']', re.IGNORECASE)
_RE_JSONLD = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.IGNORECASE | re.DOTALL
)
_RE_TAGS = re.compile(r"<[^>]+>")

UMBRAL_DUPLICADO = 0.85  # ratio difflib entre el texto visible de dos páginas distintas
LONGITUD_META_MIN = 50
LONGITUD_META_MAX = 160


def _texto_visible(html: str) -> str:
    return re.sub(r"\s+", " ", _RE_TAGS.sub(" ", html)).strip()


def _es_enlace_externo(url: str) -> bool:
    return url.startswith(("http://", "https://", "//", "mailto:", "tel:", "#", "javascript:"))


def _paginas_html(repo_dir: Path, archivos_nuevos: dict[str, str]) -> dict[str, str]:
    """Todas las páginas .html del repo tras aplicar este turno: las que
    cambian ya con su contenido nuevo, más las que no se tocan leídas de
    disco — hace falta ver el conjunto completo para detectar duplicación y
    canibalización entre una página nueva y una que no cambió hoy."""
    paginas = {}
    for ruta in repo_dir.rglob("*.html"):
        rel = ruta.relative_to(repo_dir).as_posix()
        if rel not in archivos_nuevos:
            paginas[rel] = ruta.read_text(encoding="utf-8", errors="ignore")
    paginas.update({k: v for k, v in archivos_nuevos.items() if k.endswith(".html")})
    return paginas


def _enlaces_rotos(repo_dir: Path, archivos_nuevos: dict[str, str]) -> list[str]:
    """Solo enlaces internos (relativos) — uno externo caído depende de un
    tercero, no es un fallo del agente y no debe bloquear su commit."""
    errores = []
    for ruta, contenido in archivos_nuevos.items():
        for url in _RE_HREF_SRC.findall(contenido):
            if _es_enlace_externo(url):
                continue
            destino_rel = url.split("#")[0].split("?")[0]
            if not destino_rel:
                continue
            destino = os.path.normpath((Path(ruta).parent / destino_rel).as_posix())
            if destino in archivos_nuevos or (repo_dir / destino).exists():
                continue
            errores.append(f"enlace interno roto en {ruta}: {url!r} no existe")
    return errores


def _duplicacion(paginas: dict[str, str]) -> list[str]:
    errores = []
    rutas = list(paginas.keys())
    textos = {r: _texto_visible(paginas[r]) for r in rutas}
    for i, a in enumerate(rutas):
        if len(textos[a]) < 200:  # páginas muy cortas dan ratios inestables, no vale la pena compararlas
            continue
        for b in rutas[i + 1:]:
            if len(textos[b]) < 200:
                continue
            # autojunk=False: por defecto difflib descarta como "ruido"
            # cualquier fragmento muy repetido en textos largos (>200
            # caracteres) — justo el patrón típico de contenido duplicado,
            # así que con autojunk activado el ratio sale artificialmente
            # bajo en el caso que este check existe para detectar.
            ratio = SequenceMatcher(None, textos[a], textos[b], autojunk=False).ratio()
            if ratio >= UMBRAL_DUPLICADO:
                errores.append(f"contenido casi duplicado entre {a} y {b} (similitud {ratio:.0%})")
    return errores


def _canibalizacion(paginas: dict[str, str]) -> list[str]:
    titulos, metas = {}, {}
    for ruta, html in paginas.items():
        m = _RE_TITLE.search(html)
        if m and m.group(1).strip():
            titulos.setdefault(m.group(1).strip().lower(), []).append(ruta)
        m = _RE_META_DESC.search(html)
        if m and m.group(1).strip():
            metas.setdefault(m.group(1).strip().lower(), []).append(ruta)

    errores = []
    for valor, rutas in titulos.items():
        if len(rutas) > 1:
            errores.append(f"mismo <title> en varias páginas ({', '.join(sorted(rutas))}): {valor!r}")
    for valor, rutas in metas.items():
        if len(rutas) > 1:
            errores.append(f"misma meta-description en varias páginas ({', '.join(sorted(rutas))}): {valor!r}")
    return errores


def _metadatos(archivos_nuevos: dict[str, str]) -> tuple[list[str], list[str]]:
    """Solo se valida lo que cambia hoy — una página vieja intocada con
    metadatos flojos no es responsabilidad de este turno."""
    bloqueantes, avisos = [], []
    for ruta, html in archivos_nuevos.items():
        if not ruta.endswith(".html") or "<html" not in html.lower():
            continue
        m = _RE_TITLE.search(html)
        if not m or not m.group(1).strip():
            bloqueantes.append(f"{ruta}: falta <title> o está vacío")
        m = _RE_META_DESC.search(html)
        if not m or not m.group(1).strip():
            bloqueantes.append(f"{ruta}: falta meta-description o está vacía")
        elif not (LONGITUD_META_MIN <= len(m.group(1).strip()) <= LONGITUD_META_MAX):
            avisos.append(
                f"{ruta}: meta-description de {len(m.group(1).strip())} caracteres, "
                f"fuera del rango recomendado {LONGITUD_META_MIN}-{LONGITUD_META_MAX}"
            )
    return bloqueantes, avisos


def _jsonld(archivos_nuevos: dict[str, str]) -> tuple[list[str], list[str]]:
    bloqueantes, avisos = [], []
    for ruta, html in archivos_nuevos.items():
        if not ruta.endswith(".html"):
            continue
        bloques = _RE_JSONLD.findall(html)
        if not bloques:
            continue
        for bloque in bloques:
            try:
                json.loads(bloque)
            except json.JSONDecodeError as e:
                bloqueantes.append(f"{ruta}: JSON-LD inválido ({e})")
    return bloqueantes, avisos


def validar(repo_dir: Path, archivos_nuevos: dict[str, str]) -> tuple[list[str], list[str]]:
    """archivos_nuevos: {ruta_relativa_posix: contenido_completo} — solo los
    ficheros que cambian este turno, ya con ruta_segura() verificada por el
    llamador. Devuelve (bloqueantes, avisos)."""
    bloqueantes: list[str] = []
    avisos: list[str] = []

    bloqueantes += _enlaces_rotos(repo_dir, archivos_nuevos)

    paginas = _paginas_html(repo_dir, archivos_nuevos)
    bloqueantes += _duplicacion(paginas)
    bloqueantes += _canibalizacion(paginas)

    b, a = _metadatos(archivos_nuevos)
    bloqueantes += b
    avisos += a

    b, a = _jsonld(archivos_nuevos)
    bloqueantes += b
    avisos += a

    return bloqueantes, avisos
