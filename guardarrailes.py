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


_RE_STYLE_BLOCK = re.compile(r"<style[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)


_RE_H2 = re.compile(r"<h2[^>]*>(.*?)</h2>", re.IGNORECASE | re.DOTALL)


_RE_H1 = re.compile(r"<h1[\s>]", re.IGNORECASE)
_RE_HEADER = re.compile(r"<header\b[^>]*>.*?</header>", re.IGNORECASE | re.DOTALL)

# Reconocer que lo escribe una IA, dicho como a cada una le dé la gana. La
# versión estricta de este check exigía las palabras exactas "una IA" y
# habría tumbado un turno entero por escribir "contenido generado por IA" o
# "una inteligencia artificial", que dicen exactamente lo mismo. Un turno de
# diseño perdido cuesta una semana (corre los miércoles) y parte del bote:
# el listón es "¿lo dice?", no "¿lo dice con mis palabras?".
# `IA` va en mayúsculas y con frontera de palabra a propósito: así "GUÍA" o
# "vía" no cuelan como transparencia, pero "IA", "IAs" o "la IA" sí.
_RE_DIVULGA_IA = re.compile(r"\bIAs?\b")
_RE_DIVULGA_LARGO = re.compile(r"inteligencia\s+artificial", re.IGNORECASE)


def _dice_que_es_una_ia(html: str) -> bool:
    visible = _texto_visible(html)
    return bool(_RE_DIVULGA_IA.search(visible) or _RE_DIVULGA_LARGO.search(visible))


def _enlaza_al_diario(html: str) -> bool:
    """Vale cualquier forma de enlazar al diario: `/log`, `/log.html`,
    relativa o absoluta con su propio dominio delante. Antes solo valía
    `/log` exacto — otra forma de suspender a quien lo hace bien."""
    for url in _RE_HREF_SRC.findall(html):
        ruta = url.split("#")[0].split("?")[0].rstrip("/")
        if ruta.rsplit("/", 1)[-1].lower() in ("log", "log.html"):
            return True
    return False


def _transparencia(archivos_nuevos: dict[str, str]) -> tuple[list[str], list[str]]:
    """Que cada página diga que la gestiona una IA y enlace a su diario.

    Bloqueante desde el 2026-09-02, y es el contrapeso exacto del cambio de
    ese día: hasta entonces la transparencia iba en una barra fina ARRIBA del
    todo, tan visible que nadie tenía que comprobar que estuviera. Al bajarla
    al pie —para que la web se lea como un sitio de su nicho y no como la
    demo de un experimento— deja de estar a la vista, y lo que no se ve hay
    que verificarlo: sin este check, "discreta" se convierte en "ausente" en
    tres turnos de rediseño y nadie se entera.

    Bloqueante pero ANCHO: no se exige ninguna frase concreta ni ninguna
    forma concreta de enlazar. Se exige que la página diga que hay una IA
    detrás (con esas siglas o con "inteligencia artificial") y que se pueda
    llegar al diario desde ella. Cómo se redacte y cómo se maquete es de
    cada agente, incluido el pie entero.
    """
    bloqueantes: list[str] = []
    for ruta, contenido in sorted(archivos_nuevos.items()):
        if not ruta.endswith(".html"):
            continue
        if not _dice_que_es_una_ia(contenido):
            bloqueantes.append(
                f"{ruta}: en ninguna parte se dice que detrás de esto hay una IA. "
                f"Va en el pie y lo redactas como quieras — vale 'una IA', "
                f"'inteligencia artificial' o cualquier frase que lo diga.")
        if not _enlaza_al_diario(contenido):
            bloqueantes.append(
                f"{ruta}: no se puede llegar al diario de guerra desde esta página. "
                f"Vale /log, /log.html o la URL absoluta, y el texto del enlace es tuyo.")
    return bloqueantes, []


def _diario_arriba(repo_dir: Path, archivos_nuevos: dict[str, str]) -> list[str]:
    """Aviso: el experimento asomando por encima del `<h1>`.

    Es el mismo check que antes pedía lo contrario. Hasta el 2026-09-02 se
    avisaba a quien NO tuviera la barra de transparencia arriba; desde el
    2026-09-02 se avisa a quien la siga teniendo. El motivo del cambio es de
    conversión: quien llega desde Google buscando algo de tu nicho no vino a
    ver competir a cuatro IAs, y encontrarse la meta-explicación antes que el
    contenido le da un sitio del que irse. La transparencia no desaparece,
    baja al pie — y que esté allí lo garantiza `_transparencia()`, que sí
    bloquea.

    Se mira en dos sitios, y hacen falta los dos: todo lo que va por encima
    del primer `<h1>` (ahí vivía la barra de transparencia) y el `<header>`
    entero (ahí vive el menú). Con solo el corte del `<h1>` se escapaba el
    caso real de Gemini, que tiene el menú DEBAJO de su `<h1>` pero dentro
    de la cabecera: sigue siendo lo primero que ve el visitante. El `<h1>`
    hace de corte y no `<main>` porque las cuatro estructuraron su web
    distinto y no todas usan `<main>`.
    """
    if "index.html" in archivos_nuevos:
        index = archivos_nuevos["index.html"]
    elif (repo_dir / "index.html").exists():
        index = (repo_dir / "index.html").read_text(encoding="utf-8", errors="ignore")
    else:
        return []
    m = _RE_H1.search(index)
    cabecera = (index[: m.start()] if m else "") + "".join(_RE_HEADER.findall(index))
    if not cabecera:
        return []
    if _RE_ENLACE_LOG.search(cabecera) or _RE_UNA_IA.search(_texto_visible(cabecera)):
        return [
            "tu portada todavía enseña el experimento por encima del <h1> "
            "(barra de transparencia o enlace al diario en el menú). Eso ya "
            "no va ahí: bájalo al pie, que es donde lo pide 'Jerarquía de "
            "portada y transparencia'. No bloquea el turno, pero se te "
            "repite hasta que la portada empiece por tu contenido."
        ]
    return []


def _piel_visual(repo_dir: Path, archivos_nuevos: dict[str, str]) -> list[str]:
    """Aviso, no bloqueo: que el sitio entero siga sin una sola línea de CSS
    propia no es spam ni un riesgo legal, así que no encaja como bloqueante.
    Pero hasta ahora nada lo comprobaba en ningún sitio, solo se pedía en el
    prompt ("Tu piel visual") — y el 2026-08-30 eso bastó para que GPT
    publicara 4 turnos reales seguidos sirviendo solo `reset.css` sin que
    nadie, ni el propio agente, se enterara. Mira el sitio completo (páginas
    tocadas hoy + el resto del repo), no solo lo que cambia este turno: si
    CUALQUIER página ya tiene una hoja de estilos propia o un `<style>`, se
    da por vestido y deja de avisar para siempre en ese repo.

    Endurecido 2026-08-30 (hallazgo real de la auditoría de código): la
    versión original se daba por satisfecha con un `<style></style>` vacío
    o con un `<link>` a un fichero .css que no existe en el repo — un match
    trivial o accidental apagaba el aviso PARA SIEMPRE, justo el escenario
    que el check existe para pillar. Ahora exige contenido real dentro del
    `<style>` y que el fichero enlazado exista de verdad.
    """
    paginas = _paginas_html(repo_dir, archivos_nuevos)
    if not paginas:
        return []
    for html in paginas.values():
        m = _RE_STYLE_BLOCK.search(html)
        if m and m.group(1).strip():
            return []
        for href in _RE_HREF_SRC.findall(html):
            nombre = href.rsplit("/", 1)[-1].split("?", 1)[0].lower()
            if nombre.endswith(".css") and nombre != "reset.css" and (
                nombre in archivos_nuevos or (repo_dir / nombre).exists()
            ):
                return []
    return [
        "todo el sitio sigue sirviendo solo reset.css: nunca has vestido el "
        "esqueleto con tu propio CSS ni un <style> propio (sección 'Tu piel "
        "visual' del prompt base). No bloquea el turno, pero se te repite "
        "cada vez hasta que lo hagas."
    ]


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


_RE_FORM = re.compile(r"<form\b.*?</form>", re.IGNORECASE | re.DOTALL)
_RE_CAMPO_EMAIL = re.compile(r"""type=['"]email['"]""", re.IGNORECASE)
_RE_METHOD_POST = re.compile(r"""method=['"]post['"]""", re.IGNORECASE)
_RE_CAMPO_LISTA = re.compile(r"""name=['"]l['"]""", re.IGNORECASE)
_RE_ONSUBMIT = re.compile(r"\bonsubmit=", re.IGNORECASE)
ACTION_ALTA = "panel.retoseo.com/subscription/form"


def _formulario_alta(archivos_nuevos: dict[str, str]) -> tuple[list[str], list[str]]:
    """El formulario de suscripción, entero y conectado de verdad.

    Hasta el 2026-09-02 esto solo estaba pedido en el prompt ("la IA no
    cambia la acción/method, solo el texto y estilo visual") y no lo
    comprobaba nada. Y el prompt solo no bastó, igual que no bastó con la
    piel visual ni con la og:image: al revisar los cuatro sitios ese día,
    **el formulario de Gemini era decorativo desde el día 0** —
    `action="#"` con un `onsubmit` que hacía `preventDefault()` y enseñaba
    un `alert` diciendo "Suscripción registrada en fase de prueba". Nunca
    llegó un solo email a Listmonk, a nadie le llegó su doble opt-in, y
    Gemini competía por una métrica que le era imposible marcar.

    La línea entre bloquear y avisar es una sola pregunta: **¿se pierde
    algo que no se pueda recuperar?**

    Bloquea (el alta se pierde, o falta el consentimiento):
      el `action` a Listmonk, `method="post"`, el campo `l`, un `onsubmit`
      que cancele el envío, la casilla de consentimiento y el enlace a
      privacidad. Aquí la persona ya se fue creyendo que estaba suscrita, o
      se le guardó el correo sin permiso. No hay marcha atrás.

    Solo avisa (se pierde medida, no el alta):
      que falte `attribs_origen` o su script — el alta entra igual, solo se
      apunta como "directo" en vez de "orgánico"; y que la portada se quede
      sin formulario, que puede ser una decisión de diseño legítima (moverlo
      a su propia página) y no un descuido. El aviso vuelve cada turno hasta
      que se arregle, así que no se pierde de vista.

    Todo lo visible del formulario —dónde va, qué tamaño tiene, qué dice el
    botón, cómo se maqueta— es decisión del agente y no se toca aquí.
    """
    bloqueantes, avisos = [], []
    for ruta, contenido in sorted(archivos_nuevos.items()):
        if not ruta.endswith(".html"):
            continue
        formularios = [f for f in _RE_FORM.findall(contenido) if _RE_CAMPO_EMAIL.search(f)]
        if ruta == "index.html" and not formularios:
            avisos.append(
                "index.html: la portada se ha quedado sin formulario de suscripción. Si "
                "lo has movido a otra página a propósito, ignora esto; si no, los "
                "suscriptores son la métrica que decide el experimento")
            continue
        for f in formularios:
            rotura = []
            if ACTION_ALTA not in f:
                rotura.append(f"el action a Listmonk (.../{ACTION_ALTA})")
            if not _RE_METHOD_POST.search(f):
                rotura.append('method="post"')
            if not _RE_CAMPO_LISTA.search(f):
                rotura.append('el campo oculto name="l" con tu id de lista')
            if _RE_ONSUBMIT.search(f):
                rotura.append("quitar el onsubmit: cancela el envío y deja el "
                              "formulario de adorno")
            if "consentimiento" not in f:
                rotura.append("la casilla de consentimiento obligatoria")
            if "/privacidad" not in f:
                rotura.append("el enlace a la política de privacidad")
            if rotura:
                bloqueantes.append(
                    f"{ruta}: el formulario de alta no llegaría a nadie o no tendría "
                    f"consentimiento, le falta " + "; ".join(rotura)
                    + ". El diseño del formulario es tuyo entero; su fontanería no.")
            if "attribs_origen" not in f:
                avisos.append(
                    f"{ruta}: el formulario funciona pero le falta el campo oculto "
                    f"attribs_origen, así que sus altas se apuntarán como 'directo' y "
                    f"no contarán como orgánicas — que son las únicas que puntúan")
        if formularios and "attribs_origen" in contenido and "getElementById" not in contenido:
            avisos.append(
                f"{ruta}: está el campo attribs_origen pero no el script que lo "
                f"rellena, así que toda alta se apuntará como 'directo'")
    return bloqueantes, avisos


# 300 KB por imagen, tope duro pedido por Tato el 2026-09-01. Aplica a todo lo
# que sirve el sitio, no solo a lo que genera la matriz: una foto pesada en una
# pieza hunde el LCP en móvil, y el LCP es de los pocos factores de ranking
# que Google admite en voz alta. Los SVG que dibujan las 4 andan por 1,3 KB, así
# que esto no las estorba — está para el día que alguna pegue un PNG a pelo.
MAX_BYTES_IMAGEN = 300 * 1024
EXTENSIONES_IMAGEN = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".svg")


def _peso_imagenes(repo_dir: Path) -> list[str]:
    """Imágenes servidas por encima del tope. Se mira el disco y no
    `archivos_nuevos` porque las imágenes son binarias y no viajan como texto
    en el turno: llegan al repo por otra vía y hay que pesarlas donde están."""
    errores = []
    for ruta in repo_dir.rglob("*"):
        if not ruta.is_file() or ".git" in ruta.parts:
            continue
        if ruta.suffix.lower() not in EXTENSIONES_IMAGEN:
            continue
        try:
            tam = ruta.stat().st_size
        except OSError:
            continue
        if tam > MAX_BYTES_IMAGEN:
            rel = ruta.relative_to(repo_dir).as_posix()
            errores.append(
                f"{rel}: {tam // 1024} KB, por encima del tope de "
                f"{MAX_BYTES_IMAGEN // 1024} KB por imagen — conviértela a WebP "
                f"y bájale la calidad, o redibújala en SVG si es un diagrama")
    return sorted(errores)


_RE_CANONICAL = re.compile(r'<link[^>]+rel=["\']canonical["\']', re.IGNORECASE)

# Aviso y no bloqueo, a propósito. En un sitio estático sin parámetros de
# consulta el riesgo real de duplicado por falta de canonical es casi nulo, y
# tumbarle el turno a las 4 por la página de privacidad sería desproporcionado.
# Como aviso se les repite en el parte mecánico cada turno hasta que lo
# arreglen, que es exactamente como Gemini se arregló sola la meta-description
# que faltaba (2026-09-01).
def _canonical(paginas: dict[str, str]) -> list[str]:
    return sorted(f"{ruta}: sin <link rel=\"canonical\">"
                  for ruta, html in paginas.items()
                  if not _RE_CANONICAL.search(html))


# 500 KB de página completa: el HTML más el CSS, JS e imágenes propios que
# carga. Generoso a propósito — hoy sus páginas andan por decenas de KB y sus
# SVG por 1,3 KB, así que esto no estorba a nadie que se porte bien. Está para
# avisar el día que una pieza se llene de diagramas y nadie sume el total: cada
# imagen puede cumplir el tope de 300 KB y aun así la página pesar 2 MB.
MAX_BYTES_PAGINA = 500 * 1024


def _peso_paginas(repo_dir: Path, paginas: dict[str, str]) -> list[str]:
    avisos = []
    for ruta, html in paginas.items():
        total = len(html.encode("utf-8"))
        vistos = set()
        for url in _RE_HREF_SRC.findall(html):
            if _es_enlace_externo(url):
                continue
            rel = url.split("#")[0].split("?")[0].lstrip("/")
            if not rel or rel in vistos:
                continue
            vistos.add(rel)
            f = repo_dir / rel
            if f.is_file() and f.suffix.lower() in (
                    ".css", ".js", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif"):
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
        if total > MAX_BYTES_PAGINA:
            avisos.append(f"{ruta}: {total // 1024} KB con todo lo que carga, "
                          f"por encima de {MAX_BYTES_PAGINA // 1024} KB — mira el LCP en móvil")
    return sorted(avisos)


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

    bloqueantes += _peso_imagenes(repo_dir)

    avisos += _canonical(paginas)
    avisos += _peso_paginas(repo_dir, paginas)

    b, a = _transparencia(archivos_nuevos)
    bloqueantes += b
    avisos += a

    b, a = _formulario_alta(archivos_nuevos)
    bloqueantes += b
    avisos += a

    avisos += _piel_visual(repo_dir, archivos_nuevos)
    avisos += _diario_arriba(repo_dir, archivos_nuevos)

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
