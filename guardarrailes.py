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

# --- Checks de contenido -----------------------------------------------------
# Los patrones buscan la ESTRUCTURA DE PROMESA, no el tema. Un artículo de
# fitness puede hablar de dolor o de kilos sin prometer nada; lo que no puede
# es garantizar un resultado individual. Afinar por promesa y no por palabra
# es lo que mantiene los falsos positivos bajos — y un falso positivo aquí
# bloquea el turno entero del agente, así que importa.
PATRONES_SALUD = [
    (r"\bcura(?:n|r)?\s+(?:el|la|los|las|tu|su)\b", "promete curar algo"),
    (r"\belimina\s+(?:el|la|los|las|tu|su)\s+(?:dolor|ansiedad|estrés|depresión)", "promete eliminar un síntoma"),
    (r"\bsin\s+efectos\s+secundarios\b", "afirma ausencia de efectos secundarios"),
    (r"\b(?:pierde|adelgaza|baja)\s+\d+\s*(?:kilos?|kg)\b", "promete pérdida de peso cuantificada"),
    (r"\b(?:previene|evita)\s+(?:el\s+)?(?:cáncer|alzheimer|diabetes)\b", "promete prevenir una enfermedad grave"),
    (r"\bremedio\s+(?:infalible|definitivo|milagroso)\b", "presenta un remedio como infalible"),
]
PATRONES_DINERO = [
    (r"\b(?:rentabilidad|beneficios?|ganancias?|retornos?)\s+(?:garantizad|asegurad)", "garantiza rendimientos"),
    (r"\bte\s+(?:harás?|hará)\s+rico\b", "promete enriquecimiento"),
    (r"\b(?:duplica|triplica)\s+tu\s+(?:dinero|inversión|capital)\b", "promete multiplicar el dinero"),
    (r"\bgana\s+\d+\s*(?:€|euros|\$|dólares)\s+(?:al\s+|a\s+la\s+|por\s+)?(?:día|semana|mes)", "promete ingresos cuantificados"),
    (r"\bsin\s+riesgo\b", "afirma ausencia de riesgo"),
]

# Escribir *contra* estas promesas es contenido responsable, y es justo lo que
# se quiere de un agente serio: "ningún fondo garantiza rentabilidad" no puede
# bloquearse igual que "rentabilidad garantizada". Un regex no entiende de
# negación, así que se mira si hay un negador en la frase justo antes.
# Sigue siendo una heurística: se prefiere dejar pasar algún caso raro (que la
# revisión semanal humana ve) a frenar en seco a un agente por escribir bien.
NEGADORES = re.compile(
    r"\b(?:no|ni|ningún|ninguna|ningun|nadie|nunca|jamás|jamas|falso|mito|"
    r"desconfía|desconfia|cuidado|evita|imposible|dudoso)\b"
)
VENTANA_NEGACION = 90  # caracteres antes del match donde se busca el negador


def _hay_negacion_cerca(texto: str, inicio: int) -> bool:
    # Se corta en el punto anterior para no arrastrar la negación de otra frase.
    tramo = texto[max(0, inicio - VENTANA_NEGACION):inicio]
    tramo = tramo.rsplit(".", 1)[-1]
    return bool(NEGADORES.search(tramo))
# Guardarraíl 4 (integridad de la métrica): inflar altas con incentivos en vez
# de con contenido que convenza. Va aparte porque no es un riesgo de salud ni
# legal, es hacer trampa al propio experimento.
PATRONES_INCENTIVO = [
    (r"\bsorte(?:o|amos|aremos)\b", "sortea algo entre suscriptores"),
    (r"\bsuscríbete\s+y\s+(?:gana|participa|llévate|consigue)\b", "condiciona un premio a la suscripción"),
    (r"\b(?:premio|regalo)\s+por\s+suscribirte\b", "ofrece premio por suscribirse"),
]


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


# Ficheros que genera el sistema DESPUÉS de que el agente escriba, en el mismo
# turno: pedirle que además los mantenga a mano costaría tokens y un feed mal
# formado no se detecta hasta que Search Console se queja semanas después. El
# agente enlaza a ellos con razón, así que no son enlaces rotos.
GENERADOS_POR_EL_SISTEMA = {"rss.xml", "sitemap.xml"}


def _resuelve(repo_dir: Path, destino: str, archivos_nuevos: dict[str, str]) -> bool:
    """¿Existe este destino, resolviendo como resuelve Caddy en producción?

    El esqueleto enlaza a /privacidad y /log sin extensión, y Caddy los sirve
    con `try_files {path} {path}.html {path}/index.html`. Comprobar solo la
    ruta literal marcaba como rotos justo los enlaces que el propio esqueleto
    obliga a poner — habría bloqueado el primer turno de las cuatro.
    """
    if destino in GENERADOS_POR_EL_SISTEMA:
        return True
    for candidato in (destino, f"{destino}.html", f"{destino}/index.html"):
        if candidato in archivos_nuevos or (repo_dir / candidato).exists():
            return True
    return False


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
            if destino_rel.startswith("/"):
                # Raíz-relativo: cuelga de la raíz del repo, no del directorio
                # de la página. Sin este caso, `repo_dir / "/log"` devolvía
                # "/log" —pathlib descarta la izquierda ante una ruta
                # absoluta— y se comprobaba la raíz del servidor.
                destino = os.path.normpath(destino_rel.lstrip("/"))
            else:
                destino = os.path.normpath((Path(ruta).parent / destino_rel).as_posix())
            if _resuelve(repo_dir, destino, archivos_nuevos):
                continue
            errores.append(f"enlace interno roto en {ruta}: {url!r} no existe")
    return sorted(set(errores))


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


def _contenido(archivos_nuevos: dict[str, str]) -> tuple[list[str], list[str]]:
    """Afirmaciones arriesgadas, incentivos que inflan la métrica y señales de
    spam. La página pública del proyecto promete que el filtro automático
    bloquea esto — hasta ahora solo estaba escrito en el prompt del sistema, y
    un prompt es una petición, no una garantía.

    Deliberadamente sin LLM-juez: doblaría el coste por turno y podría fallar
    también. Estos son patrones deterministas y auditables.
    """
    bloqueantes, avisos = [], []
    for ruta, html_doc in archivos_nuevos.items():
        if not ruta.endswith(".html"):
            continue
        texto = _texto_visible(html_doc)
        bajo = texto.lower()

        for patrones, categoria in (
            (PATRONES_SALUD, "afirmación de salud"),
            (PATRONES_DINERO, "afirmación financiera"),
            (PATRONES_INCENTIVO, "incentivo por suscripción"),
        ):
            for patron, explicacion in patrones:
                for m in re.finditer(patron, bajo):
                    if _hay_negacion_cerca(bajo, m.start()):
                        continue  # está desmintiendo la promesa, no haciéndola
                    fragmento = texto[max(0, m.start() - 40):m.end() + 40].strip()
                    bloqueantes.append(f"{ruta}: {categoria} — {explicacion} («…{fragmento}…»)")
                    break  # un aviso por patrón basta; no hace falta repetirlo

        # Señales de spam de forma, no de fondo: son de estilo, así que avisan
        # en vez de bloquear. Bloquear por escribir en mayúsculas sería
        # desproporcionado y frenaría a la personalidad "a saco" por diseño.
        letras = [c for c in texto if c.isalpha()]
        if len(letras) > 200:
            mayus = sum(1 for c in letras if c.isupper()) / len(letras)
            if mayus > 0.3:
                avisos.append(f"{ruta}: {mayus:.0%} del texto en mayúsculas, se lee como spam")
        if texto.count("!") > 15:
            avisos.append(f"{ruta}: {texto.count('!')} signos de exclamación, tono de spam")
    return bloqueantes, avisos


# Marcadores de plantilla que nunca deben llegar a producción. Salió de un
# dry-run real (2026-08-30): con el dominio todavía sin comprar, el agente
# escribió `https://[SUBDOMINIO]/` dentro de sus <link rel="canonical">, sus
# og:url y su RSS. Un canonical con un marcador dentro no es un fallo
# cosmético — le dice a Google que la URL buena es otra que no existe, y eso
# no se ve hasta semanas después en Search Console.
MARCADORES_PLANTILLA = ("[SUBDOMINIO]", "PENDIENTE-DOMINIO", "PENDIENTE-TOKEN", "[PENDIENTE")


def _marcadores(archivos_nuevos: dict[str, str]) -> list[str]:
    bloqueantes = []
    for ruta, contenido in sorted(archivos_nuevos.items()):
        encontrados = sorted({m for m in MARCADORES_PLANTILLA if m in contenido})
        if encontrados:
            bloqueantes.append(f"{ruta}: marcador de plantilla sin sustituir ({', '.join(encontrados)})")
    return bloqueantes


def _pie_obligatorio(archivos_nuevos: dict[str, str]) -> tuple[list[str], list[str]]:
    """El descargo de no-afiliación y el enlace al marcador.

    El descargo es bloqueante y el enlace solo un aviso, y la diferencia es
    deliberada: alojar contenido en `gpt.` o `gemini.` sin decir que no eres
    esa empresa es el único riesgo del proyecto que no se arregla pidiendo
    perdón después. Que falte el enlace al marcador cuesta visitas; que falte
    el descargo puede costar el dominio.
    """
    bloqueantes, avisos = [], []
    for ruta, contenido in sorted(archivos_nuevos.items()):
        if not ruta.endswith(".html"):
            continue
        if "sin afiliación" not in contenido.lower():
            bloqueantes.append(f"{ruta}: falta el descargo de no-afiliación en el pie")
        if "retoseo.com" not in contenido:
            avisos.append(f"{ruta}: no enlaza al marcador en vivo")
    return bloqueantes, avisos


def validar(repo_dir: Path, archivos_nuevos: dict[str, str]) -> tuple[list[str], list[str]]:
    """archivos_nuevos: {ruta_relativa_posix: contenido_completo} — solo los
    ficheros que cambian este turno, ya con ruta_segura() verificada por el
    llamador. Devuelve (bloqueantes, avisos)."""
    bloqueantes: list[str] = []
    avisos: list[str] = []

    bloqueantes += _marcadores(archivos_nuevos)

    b, a = _pie_obligatorio(archivos_nuevos)
    bloqueantes += b
    avisos += a

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

    b, a = _contenido(archivos_nuevos)
    bloqueantes += b
    avisos += a

    return bloqueantes, avisos


def validar_newsletter(cuerpo_html: str) -> tuple[list[str], list[str]]:
    """Guardarraíles del correo que sale a los suscriptores.

    Pasa por los checks de CONTENIDO (promesas de salud o dinero, incentivos
    por suscripción, tono de spam, marcadores de plantilla sin sustituir),
    que son exactamente los mismos riesgos que en una página. No pasa por los
    de página web: un correo no lleva canonical, ni og:, ni el pie del sitio,
    y exigírselo bloquearía todos los envíos por fallos que no existen.
    """
    como_pagina = {"newsletter.html": cuerpo_html}
    bloqueantes = _marcadores(como_pagina)
    b, avisos = _contenido(como_pagina)
    return bloqueantes + b, avisos
