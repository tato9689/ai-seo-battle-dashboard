"""Tarea diaria (o semanal con --newsletter) de un agente del experimento.

Uso:
  python cron_agente.py <claude|gpt|gemini|deepseek> [--newsletter] [--dry-run]

Qué hace ya, de verdad, sin esperar al dominio:
  1. Lee las métricas propias más recientes guardadas en metrics_snapshot
     (las mete ahí poller_metrics.py) y las compara con las de hace ~7 días
     — esto es lo que responde a "que accedan a sus datos y analíticas".
  2. Arma el prompt: base_comun + personalidad + ese contexto + el
     contenido actual de sus archivos en /root/aisb-<ia>/.
  3. Llama a su API (variante barata en diario, flagship con --newsletter,
     ver tiering en prompts-sistema/README.md).
  4. Parsea el bloque JSON de salida.
  5. Escribe los archivos y commitea en su repo.
  6. Añade el evento a su log.json local con datos REALES de la llamada
     (tokens, coste, duración) — no inventados.

Antes de escribir nada pasa por guardarrailes.validar() (enlaces rotos,
duplicación, canibalización de keywords, metadatos, JSON-LD) — un solo
bloqueante descarta el turno completo sin commitear ni tocar disco.

Qué NO hace todavía porque no existe: publicar el commit en un servidor
real (no hay subdominio), ni enviar la newsletter (no hay Listmonk).
Con --dry-run no escribe ni commitea nada, solo imprime lo que haría.
"""
import json
import re
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timezone, date, timedelta
from pathlib import Path

DASHBOARD_DIR = Path(__file__).parent
sys.path.insert(0, str(DASHBOARD_DIR))
sys.path.insert(0, str(DASHBOARD_DIR / "consulta_ias"))

from clientes import llamar_con_metadata, precio_de, coste_estimado  # noqa: E402
from db import get_conn, init_db  # noqa: E402
import guardarrailes  # noqa: E402
import generar_feeds  # noqa: E402
import portada  # noqa: E402
import presupuesto  # noqa: E402
import busqueda  # noqa: E402
import imagenes  # noqa: E402
import feeds  # noqa: E402
import dataforseo  # noqa: E402
import tendencias  # noqa: E402
import poller  # noqa: E402
import envio_newsletter  # noqa: E402
# Con nombre propio: dentro de ejecutar() hay una variable local `avisos`
# (los del filtro de guardarraíles) que taparía el módulo.
from avisos import enviar as avisar_telegram  # noqa: E402

PROMPTS_DIR = DASHBOARD_DIR / "prompts-sistema"

# La tabla de precios y el cálculo de coste viven en clientes.py (precio_de,
# coste_estimado) desde 2026-08-30: consulta_ias/debate.py (el consejo de
# sabios) también necesita saber cuánto cuesta cada llamada, y ese módulo no
# puede importar de aquí sin crear un ciclo (aquí ya se importa de clientes).


def cargar_prompt_sistema(ia: str, diseno: bool = False) -> str:
    """base + personalidad, y en el turno semanal de diseño un tercer bloque.

    `diseno_<ia>.md` lo escribió cada agente para sí misma en el consejo del
    2026-09-01, con los diagramas y las convenciones reales de su nicho — por
    eso hay uno por IA y no uno común: un brief compartido tendría que hablar
    en genérico para no revelar los nichos entre ellas, y en genérico se
    pierde justo lo que hace que un sitio parezca hecho por alguien de dentro.
    Va DESPUÉS de la personalidad: es la tarea, no la identidad."""
    base = (PROMPTS_DIR / "base_comun.md").read_text(encoding="utf-8")
    personalidad = (PROMPTS_DIR / f"personalidad_{ia}.md").read_text(encoding="utf-8")
    bloques = [base, personalidad]
    if diseno:
        ruta = PROMPTS_DIR / f"diseno_{ia}.md"
        if not ruta.exists():
            raise SystemExit(f"falta {ruta}: el turno de diseño de {ia} no tiene prompt")
        bloques.append(ruta.read_text(encoding="utf-8"))
    return "\n\n".join(bloques)


def contexto_metricas(ia: str) -> dict:
    """Sus propias métricas + evolución vs hace ~7 días. Fuente:
    metrics_snapshot, la misma tabla que rellena poller_metrics.py — así el
    agente ve exactamente lo mismo que ya se muestra en el dashboard.

    Tolera que la base no exista: el primer día del experimento el cron del
    agente puede correr antes que el del poller, y quedarse sin publicar por
    no tener aún una tabla de métricas vacía sería absurdo."""
    try:
        conn = get_conn()
        conn.execute("SELECT 1 FROM metrics_snapshot LIMIT 1")
    except sqlite3.Error:
        return {"aviso": "sin snapshot de métricas todavía, decide con prudencia"}
    hoy = conn.execute(
        "SELECT * FROM metrics_snapshot WHERE ia = ? ORDER BY fecha DESC LIMIT 1", (ia,)
    ).fetchone()
    hace_semana = conn.execute(
        "SELECT * FROM metrics_snapshot WHERE ia = ? AND fecha <= ? ORDER BY fecha DESC LIMIT 1",
        (ia, (date.today() - timedelta(days=6)).isoformat()),
    ).fetchone()
    conn.close()

    if hoy is None:
        return {"aviso": "sin snapshot de métricas todavía, decide con prudencia"}

    ctx = {
        "fecha_snapshot": hoy["fecha"],
        "vistas": hoy["vistas_ga4"],
        "clics_gsc": hoy["clics_gsc"],
        "posicion_media_gsc": hoy["posicion_media_gsc"],
        "suscriptores_totales": hoy["suscriptores_totales"],
    }
    if hace_semana:
        ctx["evolucion_7d"] = {
            "vistas": (hoy["vistas_ga4"] or 0) - (hace_semana["vistas_ga4"] or 0),
            "suscriptores": (hoy["suscriptores_totales"] or 0) - (hace_semana["suscriptores_totales"] or 0),
        }
    return ctx


def contenido_actual_archivos(repo_dir: Path) -> str:
    partes = []
    for nombre in ("index.html", "log.html"):
        ruta = repo_dir / nombre
        if ruta.exists():
            partes.append(f"--- {nombre} actual ---\n{ruta.read_text(encoding='utf-8')}")
    return "\n\n".join(partes)


_ESCAPES_JSON_VALIDOS = set('"\\/bfnrtu')


def _reparar_barras_invertidas(bruto: str) -> str:
    """Escapa cada `\\` que NO forme parte de un escape JSON válido,
    escaneando de izquierda a derecha (no con regex): una versión con
    regex sin estado se equivoca en cuanto hay dos barras seguidas — la
    segunda barra de un `\\\\` ya válido se malinterpreta como el inicio
    de OTRO escape a medias y se duplica otra vez, dejando triple barra.
    Probado contra el caso real: LaTeX con `\\Delta`, `\\mu`, `\\cdot`
    mezclado con `\\n`/`\\"` ya bien escapados en la misma cadena.
    """
    salida = []
    i, n = 0, len(bruto)
    while i < n:
        c = bruto[i]
        if c == "\\" and i + 1 < n:
            if bruto[i + 1] in _ESCAPES_JSON_VALIDOS:
                salida.append(bruto[i:i + 2])  # escape válido, se deja tal cual
                i += 2
                continue
            salida.append("\\\\")  # barra suelta: se escapa como barra literal
            i += 1
            continue
        salida.append(c)
        i += 1
    return "".join(salida)


def extraer_bloque_json(texto: str) -> dict | None:
    """Corregido 2026-08-30 (bug real encontrado probando esta misma
    función contra una respuesta de Gemini con un `<style>` grande): la
    versión anterior buscaba el cierre con `\\{.*?\\}` — no greedy — así
    que en cuanto el contenido del JSON llevaba HTML con CSS embebido (que
    tiene sus propias llaves `{`/`}` de sobra), el regex se paraba en la
    PRIMERA `}` que encontraba, muy por delante del cierre real, y
    `json.loads` fallaba con un fragmento truncado. La respuesta era
    válida y el turno se perdía igual — justo el escenario que se vuelve
    más probable con el prompt de "piel con intención" de hoy, que pide
    más `<style>` propio, no menos.

    Ahora se localizan los MARCADORES del cercado (```json ... ```) por
    posición, no por contenido, y se decodifica lo que hay entre medias
    con el parser de verdad (que sí entiende de llaves anidadas). La red
    de seguridad para cuando falta el cercado sigue igual, pero ahora
    tolera que sobren backticks de cierre después del JSON.
    """
    inicio = texto.find("```json")
    if inicio != -1:
        cierre = texto.find("```", inicio + len("```json"))
        bruto = texto[inicio + len("```json"):cierre if cierre != -1 else None].strip()
        try:
            obj = json.loads(bruto)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            # Reparación de última instancia: pasó de verdad con gemini el
            # 2026-08-30 en un artículo de física (Ley de Darcy) — escribió
            # notación LaTeX ("$\Delta P$", "$\mu$") dentro de un string sin
            # escapar la barra invertida, que JSON exige (`\\` para una
            # barra literal). No es un fallo de ESTE parser: el JSON que
            # envió el modelo es inválido de origen. Se repara la barra
            # invertida solo cuando NO forma parte de un escape JSON válido
            # (\" \\ \/ \b \f \n \r \t \uXXXX) — así no se toca un escape
            # que ya estaba bien.
            reparado = _reparar_barras_invertidas(bruto)
            try:
                obj = json.loads(reparado)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass
    # Red de seguridad: si el modelo se salta el cercado ```json``` pero el
    # JSON en sí es válido (pasó de verdad con gpt el 2026-08-30 — dos
    # párrafos de razonamiento y el bloque sin cercar detrás), tirar el turno
    # entero por un detalle cosmético desperdicia contenido bueno y gasto
    # real. El contrato exige que sea el bloque FINAL: se acepta el primer
    # objeto decodificable cuyo resto de texto, quitando espacios Y
    # backticks de cierre sueltos, quede vacío — así no se cuela un '{'
    # suelto de en medio del razonamiento, pero tampoco molesta un
    # cercado a medio poner.
    decoder = json.JSONDecoder()
    pos = texto.find("{")
    while pos != -1:
        try:
            obj, fin = decoder.raw_decode(texto, pos)
            if isinstance(obj, dict) and not texto[fin:].strip().strip("`").strip():
                return obj
        except json.JSONDecodeError:
            # Mismo arreglo que la ruta con cercado: se repara la cola desde
            # `pos` (nunca lo de antes, que es razonamiento libre y puede
            # llevar barras sueltas de sobra que no hace falta tocar).
            try:
                cola_reparada = _reparar_barras_invertidas(texto[pos:])
                obj, fin = decoder.raw_decode(cola_reparada)
                if isinstance(obj, dict) and not cola_reparada[fin:].strip().strip("`").strip():
                    return obj
            except json.JSONDecodeError:
                pass
        pos = texto.find("{", pos + 1)
    return None


BLOQUE_ARCHIVO = re.compile(r"```archivo:([^\n`]+)\n(.*?)\n```", re.DOTALL)
BLOQUE_NEWSLETTER_HTML = re.compile(r"```newsletter-html\n(.*?)\n```", re.DOTALL)


def extraer_bloques_archivo(texto: str) -> dict[str, str]:
    """El contenido de cada archivo vive en su propio bloque
    ```archivo:ruta```, fuera del bloque ```json``` final. Antes
    `contenido_completo` iba como string DENTRO del JSON, y una comilla o
    un backslash sin escapar en medio de una tabla HTML o una cita
    bastaba para reventar el bloque entero — pasó de verdad el
    2026-09-01: Claude perdió un turno completo por una comilla suelta en
    una cita de Prusa Forum, en un artículo que por lo demás estaba bien.
    Con el HTML fuera del JSON, en texto plano, una comilla o un
    backslash sueltos ya no rompen nada."""
    return {ruta.strip(): contenido for ruta, contenido in BLOQUE_ARCHIVO.findall(texto)}


def extraer_cuerpo_newsletter(texto: str) -> str | None:
    """Mismo motivo que `extraer_bloques_archivo`: el cuerpo del correo es
    HTML largo, así que vive en su propio bloque ```newsletter-html```,
    no como string dentro del JSON."""
    m = BLOQUE_NEWSLETTER_HTML.search(texto)
    return m.group(1) if m else None


def razonamiento_sin_json(texto: str) -> str:
    texto = BLOQUE_ARCHIVO.sub("", texto)
    texto = BLOQUE_NEWSLETTER_HTML.sub("", texto)
    return re.sub(r"```json.*?```", "", texto, flags=re.DOTALL).strip()


def ruta_segura(repo_dir: Path, ruta_relativa: str) -> Path:
    """La ruta de cada archivo viene del JSON que genera la propia IA — nunca
    confiar en ella sin comprobar que sigue dentro de repo_dir. Bloquea rutas
    absolutas y cualquier '../' que intente escapar del repo del agente."""
    destino = (repo_dir / ruta_relativa).resolve()
    if destino != repo_dir.resolve() and repo_dir.resolve() not in destino.parents:
        raise ValueError(f"ruta fuera del repo del agente, rechazada: {ruta_relativa!r}")
    return destino


def registrar_urls_publicadas(ia: str, base_url: str, archivos_nuevos: dict):
    """Apunta la fecha de publicación de cada página nueva, para poder medir
    después cuánto tarda Google en indexarla. Se hace aquí y no en el poller
    porque solo aquí se sabe el día exacto en que la página nació.

    `INSERT OR IGNORE`: reeditar una página no reinicia su reloj de
    indexación, que mide desde la primera publicación."""
    if not base_url or "PENDIENTE" in base_url:
        return
    try:
        conn = get_conn()
        hoy = date.today().isoformat()
        for rel in archivos_nuevos:
            if not rel.endswith(".html"):
                continue
            url = generar_feeds._url_publica(base_url, rel)
            conn.execute(
                "INSERT OR IGNORE INTO indexacion (ia, url, fecha_publicacion) VALUES (?, ?, ?)",
                (ia, url, hoy),
            )
        conn.commit()
        conn.close()
    except Exception as e:
        # El seguimiento de indexación es un extra: no puede costarle al
        # agente el turno que ya ha commiteado correctamente.
        print(f"no se pudo registrar la indexación: {e}", file=sys.stderr)


ALIAS_TIER = {"barato": "diaria", "potente": "semanal"}


def contexto_consultas_gsc(ia: str) -> dict:
    """Las búsquedas reales por las que ya aparece este sitio.

    Va aparte de `contexto_metricas` a propósito: aquello lee el snapshot
    diario de la base (tres números agregados) y esto pregunta a GSC en vivo
    por la dimensión `query`. Son cosas distintas — el snapshot dice cómo va,
    esto dice DE QUÉ va. Sin la segunda, el agente decide qué escribir por
    intuición teniendo delante la respuesta demostrada.

    Es contexto y no una dependencia: cualquier fallo devuelve {} y el turno
    sigue. La llamada a GSC no cuesta dinero."""
    try:
        cfg = _config_completa()
        ruta = cfg.get("google_service_account")
        site = (_config_agente(ia) or {}).get("gsc_site")
        if not ruta or not site or not Path(ruta).exists():
            return {}
        import poller_metrics
        creds = poller_metrics.credenciales(ruta)
        filas = poller_metrics.consultas_gsc(creds, site)
    except Exception as e:
        print(f"[{ia}] consultas GSC no disponibles: {e}", file=sys.stderr)
        return {}
    if not filas:
        return {}
    # 4-25 es la franja donde un cambio mueve la aguja: por encima de 4 ya
    # estás arriba y ganas poco; por debajo de 25 nadie te ve y el trabajo es
    # otro (crear autoridad, no retocar). Es el filtro que ya usa el pipeline
    # de contenido de GranVía y viene de resultados, no de teoría.
    oportunidades = [f for f in filas if 4.0 <= f["posicion"] <= 25.0 and f["impresiones"] >= 10]
    return {
        "que_es": ("busquedas reales por las que Google ya te muestra, ultimos 28 dias. "
                   "Una consulta con impresiones y posicion 4-25 es un tema DEMOSTRADO: "
                   "hay gente buscandolo, Google ya te asocia con ello y todavia no "
                   "tienes la pagina que lo responde bien."),
        "top_por_impresiones": filas[:15],
        "oportunidades_posicion_4_25": oportunidades[:10],
    }


def parte_mecanico(repo_dir: Path) -> dict:
    """El estado real del sitio tal y como lo ve el filtro, calculado sobre el
    repo entero ANTES de que el agente decida nada.

    En el consejo del 2026-09-01 las 4 pidieron partir el turno: un trabajo
    barato que lee y audita, y uno capaz que decide y redacta. La condición
    que pusieron para que el reparto compense era que el barato entregara
    "hechos mecánicos, cero juicio" y que a cambio el capaz no volviera a
    recorrer el repo.

    Resulta que para esos hechos no hace falta ningún modelo: son exactamente
    lo que `guardarrailes.validar` ya calcula, y calcularlos en Python cuesta
    cero y no alucina. Además es la MISMA función que decide si el turno se
    bloquea, así que el parte no es una aproximación de las reglas: son las
    reglas.

    Se pasa el repo entero como `archivos_nuevos` a propósito — así el
    validador audita lo que ya está publicado, no solo lo que cambia hoy."""
    actuales = {}
    for ruta in repo_dir.rglob("*"):
        if not ruta.is_file() or ".git" in ruta.parts:
            continue
        rel = ruta.relative_to(repo_dir).as_posix()
        if rel in guardarrailes.GENERADOS_POR_EL_SISTEMA:
            continue
        if ruta.suffix.lower() not in (".html", ".css", ".svg", ".xml", ".json", ".txt", ".md"):
            continue
        try:
            actuales[rel] = ruta.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
    try:
        bloqueantes, avisos = guardarrailes.validar(repo_dir, actuales)
    except Exception as e:  # nunca tumbar el turno por el parte
        print(f"[parte mecánico] no se pudo calcular: {e}", file=sys.stderr)
        return {}
    return {
        "que_es": ("estado del sitio publicado segun el mismo filtro que juzga tu turno, "
                   "calculado antes de que decidas. Son hechos, no opiniones: no hay "
                   "criterio de nadie aqui dentro."),
        "problemas_que_bloquearian": bloqueantes,
        "avisos_pendientes": avisos,
        "paginas_html": sum(1 for r in actuales if r.endswith(".html")),
    }


def tier_elegido(repo_dir: Path, por_defecto: str, solo_tipo: str | None = None) -> str:
    """Qué modelo pidió el agente para este turno en su turno anterior.

    Se lee del log real y no de un fichero de estado aparte, para que la
    elección quede publicada junto al razonamiento que la justificó: forma
    parte de lo que se enseña, no de la fontanería.

    `solo_tipo` limita la búsqueda a turnos de ese `tipo_tarea`. Hace falta
    para el turno de diseño, y el 2026-09-02 se vio por qué: el turno de
    diseño de Claude se ejecutó con Haiku —el modelo barato— y falló al
    emitir los ficheros. No lo había elegido para diseñar: había pedido
    "barato" en su turno de CONTENIDO del día anterior, que es una decisión
    razonable para escribir un artículo y pésima para rehacer la piel de un
    sitio entero. El agente no estaba eligiendo mal; el sistema no le daba
    forma de elegir distinto según el tipo de turno, y se llevaba la última
    respuesta que encontrara.

    Es justo lo que separa los dos botes de presupuesto (10 € contenido,
    5 € diseño): si el bote es aparte porque el turno de diseño necesita un
    modelo capaz, heredar el "barato" de un turno de contenido vacía el
    motivo de haberlos separado. Esto no le quita la decisión al agente, se
    la devuelve por tipo de turno: si pide "barato" DENTRO de un turno de
    diseño, se respeta.
    """
    log_path = repo_dir / "log.json"
    if not log_path.exists():
        return por_defecto
    try:
        eventos = json.loads(log_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return por_defecto
    if not isinstance(eventos, list):
        return por_defecto
    for ev in eventos:  # el más reciente primero
        if not isinstance(ev, dict):
            continue
        if solo_tipo and ev.get("tipo_tarea") != solo_tipo:
            continue
        elegido = ev.get("modelo_siguiente")
        if isinstance(elegido, str) and elegido.lower() in ALIAS_TIER:
            return ALIAS_TIER[elegido.lower()]
    return por_defecto


MAX_CONSULTAS = 3


def bloqueo_anterior(repo_dir: Path) -> str:
    """Por qué se descartó su último turno, si se descartó.

    Sin esto, un guardarraíl bloquea pero no enseña: el agente repite el
    mismo fallo cada día sin enterarse nunca de que su trabajo no llegó a
    publicarse. Se lee del log público, que ya guarda el motivo exacto.
    """
    log_path = repo_dir / "log.json"
    if not log_path.exists():
        return ""
    try:
        eventos = json.loads(log_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ""
    if not isinstance(eventos, list) or not eventos:
        return ""
    ultimo = eventos[0]
    if not isinstance(ultimo, dict) or ultimo.get("resultado") != "error":
        return ""
    detalle = ultimo.get("detalle_error") or ""
    return str(detalle)[:1200]


def avisos_anteriores(repo_dir: Path) -> list[str]:
    """Avisos (no bloqueantes) de tu último turno REAL que pasó por
    guardarrailes.validar(), sea cual sea su resultado. Antes de esto,
    `validar()` ya devolvía avisos y se imprimían en el log del cron, pero
    nadie se los devolvía al agente — vivían y morían en un fichero de
    texto que solo lee una persona. Mismo patrón que `bloqueo_anterior()`:
    se leen del propio log público, no de un estado aparte, así que lo que
    se avisó y cuándo quedan juntos y a la vista.

    Corregido 2026-08-30 (hallazgo real de la auditoría de código): mirar
    solo `eventos[0]` perdía el aviso en silencio en cuanto el turno
    siguiente era de un tipo que nunca pasa por `validar()` (newsletter
    saltada por 0 suscriptores, bloqueo por presupuesto, JSON sin parsear)
    — justo el caso normal de los primeros meses. Ahora se busca hacia
    atrás el primer evento que de verdad tiene la clave `avisos` (aunque
    sea `null`), no el primero de la lista sea cual sea su tipo.
    """
    log_path = repo_dir / "log.json"
    if not log_path.exists():
        return []
    try:
        eventos = json.loads(log_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(eventos, list):
        return []
    for ev in eventos:
        if not isinstance(ev, dict) or "avisos" not in ev:
            continue
        avisos = ev.get("avisos")
        return avisos if isinstance(avisos, list) else []
    return []


def consultas_pedidas(repo_dir: Path) -> list[str]:
    """Las búsquedas que el agente pidió en su turno anterior.

    Mismo patrón que `tier_elegido`: la petición sale del log público, no de
    un fichero de estado aparte, así que lo que buscó y por qué quedan juntos
    y a la vista. Y sobre todo no cuesta una llamada extra: pedir las
    consultas dentro del JSON de salida del turno anterior deja el ciclo en
    una sola llamada al modelo por turno, igual que antes.
    """
    log_path = repo_dir / "log.json"
    if not log_path.exists():
        return []
    try:
        eventos = json.loads(log_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(eventos, list):
        return []
    for ev in eventos:  # el más reciente primero
        if not isinstance(ev, dict):
            continue
        pedidas = ev.get("consultas_siguiente_turno")
        if isinstance(pedidas, list) and pedidas:
            return [str(c)[:200] for c in pedidas if isinstance(c, str) and c.strip()][:MAX_CONSULTAS]
    return []


def contexto_busqueda(repo_dir: Path, cfg: dict) -> dict:
    """Ejecuta las búsquedas que pidió el agente y devuelve sus resultados.

    La fase la decide el sistema con la fecha del checkpoint, nunca el
    agente: en fase 1 el filtro de `busqueda.py` le esconde a los otros 3
    competidores. Si la búsqueda falla, el turno sigue — quedarse sin
    datos externos es peor que quedarse sin turno.
    """
    consultas = consultas_pedidas(repo_dir)
    if not consultas:
        return {}
    fase = poller.derivar_fase(datetime.now(timezone.utc).isoformat(), cfg.get("checkpoint_fase2"))
    salida = {}
    for consulta in consultas:
        try:
            bloque = busqueda.buscar(consulta, fase=fase, n=5, cfg=cfg)
        except Exception as e:
            bloque = {"resultados": [], "descartados": 0, "fase": fase, "error": str(e)}
        # Autocompletado y Trends viajan pegados a la consulta que el agente ya
        # pidió: así el reparto es simétrico por construcción —nadie puede
        # pedir más señal que otro— y el contrato de salida no cambia.
        bloque["autocompletado_google"] = tendencias.sugerencias(consulta)
        bloque["google_trends"] = tendencias.tendencia(consulta)
        salida[consulta] = bloque
    return salida


def imagenes_pedidas(repo_dir: Path) -> list[str]:
    """Mismo patrón que `consultas_pedidas`: lo que pidió el agente en su
    turno anterior, vía `imagenes_siguiente_turno` en el log público."""
    log_path = repo_dir / "log.json"
    if not log_path.exists():
        return []
    try:
        eventos = json.loads(log_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(eventos, list):
        return []
    for ev in eventos:  # el más reciente primero
        if not isinstance(ev, dict):
            continue
        pedidas = ev.get("imagenes_siguiente_turno")
        if isinstance(pedidas, list) and pedidas:
            return [str(c)[:200] for c in pedidas if isinstance(c, str) and c.strip()][:MAX_CONSULTAS]
    return []


def contexto_imagenes(repo_dir: Path) -> dict:
    """Busca en Pexels lo que el agente pidió. Sin clave configurada o con
    la API caída, el turno sigue sin imágenes — igual que `contexto_busqueda`,
    quedarse sin este dato no debe tumbar nada."""
    consultas = imagenes_pedidas(repo_dir)
    if not consultas:
        return {}
    salida = {}
    for consulta in consultas:
        try:
            salida[consulta] = imagenes.buscar(consulta)
        except Exception as e:
            salida[consulta] = {"error": str(e)}
    return salida


def feeds_pedidos(repo_dir: Path) -> list[str]:
    """Mismo patrón que `imagenes_pedidas`: URLs de feed (RSS/Atom, incluido
    `.../releases.atom` de GitHub) que el agente pidió seguir en su turno
    anterior, vía `feeds_siguiente_turno` en el log público. Añadido
    2026-08-30 tras la auditoría de herramientas (pedido real de Claude y
    DeepSeek: detectar releases/cambios de su nicho sin tener que buscarlo
    a mano cada turno)."""
    log_path = repo_dir / "log.json"
    if not log_path.exists():
        return []
    try:
        eventos = json.loads(log_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(eventos, list):
        return []
    for ev in eventos:
        if not isinstance(ev, dict):
            continue
        pedidas = ev.get("feeds_siguiente_turno")
        if isinstance(pedidas, list) and pedidas:
            return [str(u)[:500] for u in pedidas if isinstance(u, str) and u.strip()][:feeds.MAX_FEEDS]
    return []


def contexto_feeds(repo_dir: Path) -> dict:
    """Lee los feeds que el agente pidió. Un feed caído o con formato raro
    no tumba el turno — se devuelve el error de ESE feed, el resto sigue."""
    urls = feeds_pedidos(repo_dir)
    if not urls:
        return {}
    try:
        return feeds.leer_varios(urls)
    except Exception as e:
        return {"error": str(e)}


def keywords_pedidas(repo_dir: Path) -> list[str]:
    """Mismo patrón: keywords que el agente pidió consultar en DataForSEO
    (volumen real + dificultad), vía `keywords_siguiente_turno`. Añadido
    2026-08-30 tras la auditoría de herramientas (pedido real de Gemini:
    autocompletado/Trends dan dirección, no escala)."""
    log_path = repo_dir / "log.json"
    if not log_path.exists():
        return []
    try:
        eventos = json.loads(log_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(eventos, list):
        return []
    for ev in eventos:
        if not isinstance(ev, dict):
            continue
        pedidas = ev.get("keywords_siguiente_turno")
        if isinstance(pedidas, list) and pedidas:
            return [str(k)[:100] for k in pedidas if isinstance(k, str) and k.strip()][:5]
    return []


def contexto_dataforseo(repo_dir: Path) -> dict:
    """Consulta DataForSEO para las keywords pedidas. Comparte tope de
    llamadas entre las 4 (ver dataforseo.py) — si el tope compartido ya se
    agotó ese mes, el turno sigue con un aviso en el propio dato, no con un
    fallo."""
    keywords = keywords_pedidas(repo_dir)
    if not keywords:
        return {}
    try:
        return dataforseo.volumen_y_dificultad(keywords)
    except Exception as e:
        return {"error": str(e)}


MODELOS_VISTOS = DASHBOARD_DIR / "cache" / "modelos_vistos.json"


def avisar_si_cambia_modelo(ia: str, tier: str, servido: str | None):
    """Vigila que el modelo que sirve la API no cambie por debajo.

    Solo GPT tiene los tres tiers con snapshot fechado; Anthropic y Google no
    publican ids con fecha de sus familias actuales, así que sus alias pueden
    moverse solos. Si eso pasa a mitad de experimento, la comparación
    antes/después del checkpoint deja de medir lo mismo — y sin este aviso no
    habría forma de enterarse hasta revisar el log a mano meses después.

    Se guarda en cache/ (ignorado por git) porque es estado de ejecución, no
    parte del experimento: el dato bueno vive en `modelo_exacto` de cada
    evento del log público.
    """
    if not servido:
        return
    clave = f"{ia}/{tier}"
    try:
        MODELOS_VISTOS.parent.mkdir(parents=True, exist_ok=True)
        vistos = json.loads(MODELOS_VISTOS.read_text()) if MODELOS_VISTOS.exists() else {}
    except (OSError, json.JSONDecodeError):
        vistos = {}
    anterior = vistos.get(clave)
    if anterior and anterior != servido:
        avisar_telegram(
            f"🔄 AI SEO Battle: el modelo de {ia} ({tier}) cambió por debajo — "
            f"antes {anterior}, ahora {servido}. Afecta a la comparación del experimento."
        )
    if anterior != servido:
        vistos[clave] = servido
        try:
            MODELOS_VISTOS.write_text(json.dumps(vistos, ensure_ascii=False, indent=2))
        except OSError as e:
            print(f"no se pudo guardar {MODELOS_VISTOS}: {e}", file=sys.stderr)


def registrar_evento(repo_dir: Path, evento: dict):
    log_path = repo_dir / "log.json"
    eventos = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else []
    eventos.insert(0, evento)
    log_path.write_text(json.dumps(eventos, ensure_ascii=False, indent=2), encoding="utf-8")


def git_commit(repo_dir: Path, mensaje: str) -> str:
    subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", mensaje], cwd=repo_dir, check=True, capture_output=True)
    return subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True
    ).stdout.strip()


def git_push(repo_dir: Path) -> bool:
    """El commit ya está a salvo en local, así que un push fallido (sin red,
    token caducado) no debe tumbar el turno ni perder el trabajo: se avisa y
    el siguiente pase lo arrastra."""
    r = subprocess.run(["git", "push", "-q", "origin", "HEAD"], cwd=repo_dir, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"push fallido (no bloqueante, el commit está en local): {r.stderr.strip()}", file=sys.stderr)
        return False
    return True


def resumen_cambios(repo_dir: Path, sha: str) -> list[dict]:
    """[{archivo, añadidas, quitadas}] del commit. Poder ver *qué* cambió al
    lado del *por qué* es lo que convierte el log en algo que se explora; el
    enlace al commit da el diff completo, esto da el vistazo rápido sin salir
    del dashboard. Los archivos que genera el sistema (portadas, feeds) se
    excluyen: no son decisiones del agente y ensucian el resumen."""
    r = subprocess.run(
        ["git", "show", "--numstat", "--format=", sha], cwd=repo_dir, capture_output=True, text=True
    )
    if r.returncode != 0:
        return []
    cambios = []
    for linea in r.stdout.strip().splitlines():
        partes = linea.split("\t")
        if len(partes) != 3:
            continue
        añadidas, quitadas, archivo = partes
        if archivo.startswith("og/") or archivo in {"sitemap.xml", "rss.xml", "log.json"}:
            continue
        cambios.append({
            "archivo": archivo,
            # "-" en un binario; se guarda como None en vez de romper.
            "anadidas": int(añadidas) if añadidas.isdigit() else None,
            "quitadas": int(quitadas) if quitadas.isdigit() else None,
        })
    return cambios


def url_commit(repo_dir: Path, sha: str) -> str:
    """URL pública del commit, para que el /log enlace a la prueba real de lo
    que hizo el agente. Si no hay remoto configurado, se cae al identificador
    local en vez de inventar una URL que daría 404."""
    r = subprocess.run(
        ["git", "remote", "get-url", "origin"], cwd=repo_dir, capture_output=True, text=True
    )
    remoto = r.stdout.strip()
    if r.returncode != 0 or not remoto:
        return f"local-commit:{sha}"
    if remoto.startswith("git@github.com:"):
        remoto = "https://github.com/" + remoto[len("git@github.com:"):]
    return f"{remoto.removesuffix('.git')}/commit/{sha}"


def _config_completa() -> dict:
    with open(DASHBOARD_DIR / "config.json", encoding="utf-8") as fh:
        return json.load(fh)


def _config_agente(ia: str) -> dict:
    cfg = _config_completa()
    for agente in cfg.get("agentes", []):
        if agente.get("ia") == ia:
            return agente
    return {}


def agente_activo(ia: str) -> bool:
    """Kill switch humano: `"activo": false` en config.json para en seco a ese
    agente, antes de gastar una sola llamada a su API. Si el agente no aparece
    en config, se considera parado (fallar cerrado, no abierto)."""
    agente = _config_agente(ia)
    if not agente:
        return False
    return bool(agente.get("activo", True))


def base_url_agente(ia: str) -> str:
    """URL pública del subdominio, derivada del log_url ya configurado para no
    duplicar el dominio en dos sitios que se puedan desincronizar."""
    log_url = _config_agente(ia).get("log_url", "")
    return log_url[: -len("/log.json")] if log_url.endswith("/log.json") else ""


def ejecutar(ia: str, newsletter: bool, dry_run: bool, diseno: bool = False):
    # Crea las tablas si faltan (idempotente): el cron del agente puede correr
    # antes que el del poller el primer día, y todo lo que registra después
    # —indexación, presupuesto— necesita que el esquema exista.
    try:
        init_db()
    except sqlite3.Error as e:
        print(f"no se pudo inicializar la base: {e}", file=sys.stderr)

    if not agente_activo(ia):
        print(f"[{ia}] parado por kill switch (activo=false en config.json) — no se hace nada.")
        return

    repo_dir = Path(f"/root/aisb-{ia}")
    if not repo_dir.exists():
        print(f"No existe {repo_dir} — crea el repo del agente primero.", file=sys.stderr)
        sys.exit(1)

    system = cargar_prompt_sistema(ia, diseno=diseno)
    ctx = contexto_metricas(ia)
    if diseno:
        # Explícito y no solo "turno de diseño": la sección de cadencia de
        # contenido de `base_comun.md` sigue delante en el prompt y empuja a
        # publicar una pieza. En el primer ensayo en seco (gemini, 2026-09-01)
        # eso ganó a su propio prompt de diseño: montó su piel.css Y escribió
        # además un artículo, con accion_tipo "crear-articulo". La cuota no se
        # suspende, la cubren los turnos diarios; lo que no toca es hoy.
        tarea = (
            "tu turno semanal de DISEÑO. Hoy NO escribes ninguna pieza de "
            "contenido: la cadencia mínima de contenido no aplica a este turno "
            "y tu cuota la cubren tus turnos diarios. Si acabas antes de tiempo, "
            "resuelve mejor la pieza de diseño que has elegido en vez de añadir "
            "un artículo. El `accion_tipo` de hoy no puede ser crear-articulo "
            "ni actualizar-articulo"
        )
    elif newsletter:
        tarea = "la newsletter semanal"
    else:
        tarea = "tu tarea diaria habitual"

    # Turno semanal con la lista vacía: no se hace. Es el único turno que usa
    # el modelo flagship y el presupuesto tiene que llegar a 10 meses, así que
    # escribir un correo que no va a recibir nadie es gasto puro. La pieza
    # pública de ese domingo ya la ha escrito el turno diario del mismo día,
    # de modo que no se pierde nada indexable. Va aquí arriba, antes de las
    # búsquedas y de la llamada, para no gastar tampoco en el contexto.
    if newsletter and not dry_run:
        lista = _config_agente(ia).get("listmonk_list_id")
        seguir, motivo = envio_newsletter.hay_a_quien_enviar(_config_completa(), lista)
        if not seguir:
            print(f"[{ia}] newsletter no enviada: {motivo}")
            registrar_evento(repo_dir, {
                "evento_id": f"{date.today().isoformat()}-sin-suscriptores",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "modelo_exacto": None, "tipo_tarea": None, "input_contexto": ctx,
                "razonamiento": "", "accion_tipo": "sin-suscriptores",
                "output_resumen": f"turno de newsletter saltado: {motivo}",
                "output_url": None,
                "tokens_in": None, "tokens_out": None, "coste_estimado": None,
                # `exito` y no `error` a propósito: no se ha roto nada, es la
                # decisión correcta. Marcarlo como error dispararía el aviso
                # de Telegram del poller y ensuciaría la tasa de error del
                # marcador todas las semanas hasta el primer suscriptor.
                "duracion_seg": None, "resultado": "exito", "detalle_error": None,
            })
            # Sin esto el evento se queda escrito en disco pero sin commitear
            # — un vistazo real el 2026-08-30: como 0 suscriptores es la
            # situación normal en los primeros meses, esto pasaría CADA
            # domingo en las 4 IAs, dejando el repo sucio hasta que otro
            # commit posterior lo arrastrara sin querer con su `git add -A`.
            git_commit(repo_dir, "log: registra turno de newsletter saltado por 0 suscriptores")
            return
    from clientes import MODELOS, PRECIOS_APROX_POR_M_TOKENS  # noqa: E402  (import local: evita ciclo al arrancar)
    ctx_presu = presupuesto.contexto_para_agente(
        ia, MODELOS.get(ia, {}), PRECIOS_APROX_POR_M_TOKENS
    )
    base_url = base_url_agente(ia)
    motivo = bloqueo_anterior(repo_dir)
    aviso_bloqueo = (
        f"ATENCIÓN: tu turno anterior NO se publicó. El filtro lo descartó entero por esto:\n"
        f"{motivo}\n"
        f"Corrígelo hoy antes que nada; si vuelves a caer en lo mismo pierdes otro día.\n\n"
    ) if motivo else ""
    avisos_previos = avisos_anteriores(repo_dir)
    bloque_avisos_previos = (
        "Avisos de tu turno anterior (no bloquearon nada, pero se te repiten "
        "hasta que los resuelvas, no son ruido de una sola vez):\n"
        + "\n".join(f"- {a}" for a in avisos_previos) + "\n\n"
    ) if avisos_previos else ""
    cfg_completa = _config_completa()
    resultados_busqueda = contexto_busqueda(repo_dir, cfg_completa)
    bloque_busqueda = ""
    if resultados_busqueda:
        bloque_busqueda = (
            "Resultados de las búsquedas que pediste en tu turno anterior "
            f"(`descartados` son resultados del propio experimento que el filtro de fase te ocultó):\n"
            f"{json.dumps(resultados_busqueda, ensure_ascii=False)}\n\n"
        )
    resultados_imagenes = contexto_imagenes(repo_dir)
    bloque_imagenes = ""
    if resultados_imagenes:
        bloque_imagenes = (
            "Fotos de banco (Pexels) para las búsquedas de imagen que pediste "
            "en tu turno anterior. Usar cualquiera es opcional y decisión tuya "
            "— si usas una, `atribucion_html` va tal cual junto a la imagen, "
            "no lo resumas ni lo quites:\n"
            f"{json.dumps(resultados_imagenes, ensure_ascii=False)}\n\n"
        )
    resultados_feeds = contexto_feeds(repo_dir)
    bloque_feeds = ""
    if resultados_feeds:
        bloque_feeds = (
            "Feeds (RSS/Atom) que pediste seguir en tu turno anterior — "
            "incluye `.../releases.atom` de GitHub si seguiste un repo. Un "
            "feed nuevo o cambiado desde ayer puede ser tu disparador del "
            "turno de hoy:\n"
            f"{json.dumps(resultados_feeds, ensure_ascii=False)}\n\n"
        )
    resultados_dataforseo = contexto_dataforseo(repo_dir)
    bloque_dataforseo = ""
    if resultados_dataforseo:
        bloque_dataforseo = (
            "Volumen mensual real y dificultad de las keywords que pediste "
            "en tu turno anterior (DataForSEO — tope compartido entre las "
            "4, puede venir vacío si ya se agotó ese mes). `competencia` es "
            "de pujas de Google Ads, no es dificultad SEO real; usa "
            "`dificultad` para eso, y trátala como null si no hay dato "
            "para keywords muy long-tail:\n"
            f"{json.dumps(resultados_dataforseo, ensure_ascii=False)}\n\n"
        )

    # Freno de gasto ANTES de llamar. El límite de la consola del proveedor es
    # la red final, pero salta de golpe y deja al agente mudo sin explicación;
    # esto degrada primero y solo para del todo al llegar al tope.
    presu = presupuesto.estado(ia, tipo=presupuesto.TIPO_DISENO if diseno else "normal")
    if not presu["permitir"]:
        print(f"[{ia}] sin llamada: {presu['motivo']}")
        registrar_evento(repo_dir, {
            "evento_id": f"{date.today().isoformat()}-presupuesto",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "modelo_exacto": None, "tipo_tarea": None, "input_contexto": ctx,
            "razonamiento": "", "accion_tipo": "sin-presupuesto",
            "output_resumen": presu["motivo"], "output_url": None,
            "tokens_in": None, "tokens_out": None, "coste_estimado": None,
            "duracion_seg": None, "resultado": "error",
            "detalle_error": f"bloqueado por presupuesto: {presu['motivo']}",
        })
        return

    # El modelo lo elige el propio agente en su turno anterior: administrar su
    # presupuesto es parte de lo que se está midiendo, no una decisión del
    # sistema. El tiering por tarea queda solo como valor de partida el primer
    # día, cuando todavía no ha elegido nada.
    # El de diseño arranca en "semanal" igual que la newsletter: es un turno
    # que se da una vez por semana y produce componentes que reutilizan todos
    # los turnos diarios siguientes, así que es de los pocos sitios donde el
    # modelo capaz se amortiza. A partir del segundo, manda su propia elección.
    tier = tier_elegido(repo_dir, por_defecto="diaria" if not (newsletter or diseno) else "semanal",
                        solo_tipo="diseno" if diseno else None)
    if presu["degradar"] and tier == "semanal":
        # Único caso en que el sistema le pisa la elección: cerca del tope,
        # una newsletter con el modelo pequeño es mejor que quedarse sin turnos.
        print(f"[{ia}] {presu['motivo']}")
        tier = "diaria"

    # Se calcula el tier ANTES de construir el prompt para poder decírselo tal
    # cual: modelo_siguiente solo decide el PRÓXIMO turno, así que sin esta
    # línea el agente escribe sin saber con qué modelo está escribiendo ahora
    # mismo — pasó de verdad el 2026-08-30, un turno razonó "voy a usar el
    # modelo potente" y en realidad corrió con el barato, sin que nada se lo
    # dijera.
    consultas_reales = contexto_consultas_gsc(ia)
    bloque_consultas = (
        "Tus búsquedas reales en Search Console:\n"
        f"{json.dumps(consultas_reales, ensure_ascii=False, indent=2)}\n\n"
        if consultas_reales else ""
    )

    parte = parte_mecanico(repo_dir)
    bloque_parte = (
        "Parte mecánico del sitio, calculado por el mismo filtro que juzga tu "
        "turno (no lo ha escrito ningún modelo, no hay criterio de nadie "
        f"dentro):\n{json.dumps(parte, ensure_ascii=False, indent=2)}\n\n"
        if parte else ""
    )

    aviso_tier = (
        f"Este turno de HOY ya se está ejecutando con el modelo "
        f"'{MODELOS.get(ia, {}).get(tier)}' (tier '{tier}'). Eso no lo eliges "
        f"ahora: quedó fijado por tu elección de modelo_siguiente en el turno "
        f"anterior (o por defecto, si es tu primer turno). Lo que pongas en "
        f"modelo_siguiente esta vez decide tu PRÓXIMO turno, no este.\n\n"
    )
    user = (
        f"Tu sitio vive en {base_url} y ese es el dominio que va en tus canonical, "
        f"tus og:url y tus enlaces absolutos. Nunca escribas un marcador tipo "
        f"[SUBDOMINIO] ni inventes otro dominio: el filtro descarta el turno entero.\n\n"
        f"{aviso_bloqueo}"
        f"{bloque_avisos_previos}"
        f"{aviso_tier}"
        f"Hoy toca {tarea}. Este es tu contexto real de métricas:\n{json.dumps(ctx, ensure_ascii=False)}\n\n"
        f"Este es tu presupuesto:\n{json.dumps(ctx_presu, ensure_ascii=False)}\n\n"
        f"{bloque_busqueda}"
        f"{bloque_imagenes}"
        f"{bloque_feeds}"
        f"{bloque_dataforseo}"
        f"{bloque_consultas}"
        f"{bloque_parte}"
        f"Este es el contenido actual de tus archivos:\n\n{contenido_actual_archivos(repo_dir)}"
    )
    resultado = llamar_con_metadata(ia, system, user, tier=tier)
    texto = resultado["texto"]
    avisar_si_cambia_modelo(ia, tier, resultado.get("modelo"))

    if texto.startswith("[sin ") and texto.endswith("configurada]"):
        print(f"[{ia}] {texto}")
        return

    datos = extraer_bloque_json(texto)
    if datos is None:
        print(f"[{ia}] no se pudo parsear el bloque JSON de la respuesta — no se aplica nada.", file=sys.stderr)
        print(texto)
        if dry_run:
            # Hallazgo real de la auditoría de código (encontrado probando
            # este mismo turno en dry-run contra gemini): esta rama
            # escribía y commiteaba SIEMPRE, ignorando `dry_run` — al
            # revés que el resto de la función, que sí lo respeta. Dos
            # commits reales de prueba llegaron a /root/aisb-gemini antes
            # de pillarlo. `--dry-run` significa no tocar disco, sin
            # excepciones por el tipo de fallo.
            print("--dry-run: no se registra ni commitea nada (aquí también).")
            return
        # Se registra igual que un bloqueo de guardarraíles: antes esto
        # devolvía sin dejar rastro, así que el turno desaparecía del log
        # público sin explicación y el siguiente turno no se enteraba de por
        # qué no se publicó nada — rompía la transparencia del experimento.
        registrar_evento(repo_dir, {
            "evento_id": f"{date.today().isoformat()}-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "modelo_exacto": resultado["modelo"],
            "tipo_tarea": None,
            "input_contexto": ctx,
            "razonamiento": texto[:4000],
            "accion_tipo": None,
            "output_resumen": "el turno no se publicó: la respuesta no traía un bloque JSON válido",
            "output_url": None,
            "tokens_in": resultado["tokens_in"],
            "tokens_out": resultado["tokens_out"],
            "coste_estimado": coste_estimado(resultado["modelo"], resultado["tokens_in"], resultado["tokens_out"]),
            "duracion_seg": resultado["duracion_seg"],
            "resultado": "error",
            "detalle_error": "no se pudo parsear el bloque JSON de la respuesta",
        })
        git_commit(repo_dir, "log: registra intento sin JSON parseable")
        return

    razonamiento = razonamiento_sin_json(texto)
    print(f"[{ia}] {datos.get('accion_tipo')}: {datos.get('output_resumen')}")

    if dry_run:
        # Un dry-run que solo enseña el JSON no responde la única pregunta que
        # importa antes de un lanzamiento: ¿este turno se habría publicado?
        # Así que pasa por los mismos guardarraíles que el turno real.
        print("--dry-run: no se escribe ni commitea nada.")
        bloques_archivo = extraer_bloques_archivo(texto)
        try:
            prueba = {
                ruta_segura(repo_dir, r).relative_to(repo_dir).as_posix(): bloques_archivo[r]
                for r in datos.get("archivos", [])
            }
        except (ValueError, KeyError) as e:
            print(f"[{ia}] salida no aplicable: {e}", file=sys.stderr)
            return
        bloqueantes, avisos = guardarrailes.validar(repo_dir, prueba)
        for aviso in avisos:
            print(f"[{ia}] aviso: {aviso}")
        if bloqueantes:
            print(f"[{ia}] SE HABRÍA BLOQUEADO: " + "; ".join(bloqueantes), file=sys.stderr)
        else:
            print(f"[{ia}] pasa los guardarraíles ({len(prueba)} archivos)")
        return

    rutas = datos.get("archivos", [])
    bloques_archivo = extraer_bloques_archivo(texto)
    faltantes = [r for r in rutas if r not in bloques_archivo]
    if faltantes:
        # El JSON lista una ruta pero no hay bloque ```archivo:esa-ruta```
        # que le corresponda — mismo tratamiento que un JSON sin parsear:
        # se registra como error visible, no se aplica nada a medias.
        print(f"[{ia}] archivos listados sin bloque ```archivo:``` correspondiente: {faltantes} — no se aplica nada.", file=sys.stderr)
        registrar_evento(repo_dir, {
            "evento_id": f"{date.today().isoformat()}-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "modelo_exacto": resultado["modelo"],
            "tipo_tarea": tipo_tarea_de(datos, newsletter, diseno),
            "input_contexto": ctx,
            "razonamiento": razonamiento,
            "accion_tipo": datos.get("accion_tipo"),
            "output_resumen": "el turno no se publicó: faltan bloques ```archivo:``` para rutas listadas en el JSON",
            "output_url": None,
            "tokens_in": resultado["tokens_in"],
            "tokens_out": resultado["tokens_out"],
            "coste_estimado": coste_estimado(resultado["modelo"], resultado["tokens_in"], resultado["tokens_out"]),
            "duracion_seg": resultado["duracion_seg"],
            "resultado": "error",
            "detalle_error": f"rutas sin bloque archivo: correspondiente: {faltantes}",
        })
        git_commit(repo_dir, "log: registra intento con archivos sin bloque correspondiente")
        return
    try:
        destinos = [(ruta_segura(repo_dir, r), bloques_archivo[r]) for r in rutas]
    except ValueError as e:
        print(f"[{ia}] {e} — no se aplica ningún cambio de este turno.", file=sys.stderr)
        return

    archivos_nuevos = {destino.relative_to(repo_dir).as_posix(): contenido for destino, contenido in destinos}
    bloqueantes, avisos = guardarrailes.validar(repo_dir, archivos_nuevos)
    for aviso in avisos:
        print(f"[{ia}] aviso guardarraíl: {aviso}")

    if bloqueantes:
        detalle = "; ".join(bloqueantes)
        print(f"[{ia}] BLOQUEADO por guardarraíles, no se aplica ningún cambio de este turno:", file=sys.stderr)
        for b in bloqueantes:
            print(f"  - {b}", file=sys.stderr)
        registrar_evento(repo_dir, {
            "evento_id": f"{date.today().isoformat()}-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "modelo_exacto": resultado["modelo"],
            "tipo_tarea": tipo_tarea_de(datos, newsletter, diseno),
            "input_contexto": ctx,
            "razonamiento": razonamiento,
            "accion_tipo": datos.get("accion_tipo"),
            "output_resumen": datos.get("output_resumen"),
            "output_url": None,
            "tokens_in": resultado["tokens_in"],
            "tokens_out": resultado["tokens_out"],
            "coste_estimado": coste_estimado(resultado["modelo"], resultado["tokens_in"], resultado["tokens_out"]),
            "duracion_seg": resultado["duracion_seg"],
            "resultado": "error",
            "detalle_error": f"bloqueado por guardarraíles: {detalle}",
            "avisos": avisos or None,
        })
        git_commit(repo_dir, "log: registra intento bloqueado por guardarraíles")
        # Los bloqueos también se publican: enseñar dónde se equivoca cada IA
        # es parte de la transparencia, no algo que esconder.
        git_push(repo_dir)
        return

    for destino, contenido in destinos:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")

    # Portadas y feeds los genera el sistema, no la IA: es trabajo mecánico
    # que sale gratis, siempre correcto, y viaja en el mismo commit que el
    # contenido al que pertenece.
    portada.escribir_para(repo_dir, list(archivos_nuevos), ia, base_url)
    generar_feeds.escribir_feeds(repo_dir, base_url)

    commit_hash = git_commit(repo_dir, f"{datos.get('accion_tipo', 'cambio')}: {datos.get('output_resumen', '')}")
    cambios = resumen_cambios(repo_dir, commit_hash)

    # El correo, ya con la pieza publicada y commiteada: si el envío falla,
    # el contenido de esa semana no se pierde ni se queda sin justificar en
    # el log. El cuerpo pasa por los guardarraíles de contenido igual que una
    # página — es lo mismo que se publica, pero llegando a bandejas reales.
    envio = None
    avisos_nl: list[str] = []
    payload = datos.get("newsletter") or {}
    cuerpo_html = extraer_cuerpo_newsletter(texto)
    if isinstance(payload, dict) and cuerpo_html and not dry_run:
        bloq_nl, avisos_nl = guardarrailes.validar_newsletter(cuerpo_html)
        for aviso in avisos_nl:
            print(f"[{ia}] aviso newsletter: {aviso}")
        if bloq_nl:
            envio = {"enviado": False, "motivo": "bloqueado por guardarraíles: " + "; ".join(bloq_nl)}
            avisar_telegram(f"⛔ AI SEO Battle: newsletter de {ia} bloqueada — {'; '.join(bloq_nl)}")
        else:
            try:
                envio = envio_newsletter.enviar(
                    _config_completa(), ia, _config_agente(ia).get("listmonk_list_id"),
                    payload.get("asunto", ""), cuerpo_html,
                )
            except Exception as e:
                # Un fallo de envío no invalida el turno (la pieza ya está
                # publicada), pero tiene que verse: es la única vía por la
                # que el experimento capta suscriptores.
                envio = {"enviado": False, "motivo": f"error de Listmonk: {e}"}
            if envio.get("enviado"):
                avisar_telegram(
                    f"📬 AI SEO Battle: {ia} envió su newsletter «{envio['asunto']}» "
                    f"a {envio['suscriptores']} suscriptores"
                )
            else:
                avisar_telegram(f"⚠️ AI SEO Battle: {ia} no envió newsletter — {envio.get('motivo')}")
    elif newsletter and not dry_run:
        # Turno semanal que sí tenía a quien escribir y no devolvió correo.
        envio = {"enviado": False, "motivo": "el turno semanal no devolvió el campo newsletter"}
        avisar_telegram(f"⚠️ AI SEO Battle: turno semanal de {ia} sin campo newsletter — no salió ningún correo")

    evento = {
        "evento_id": f"{date.today().isoformat()}-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "modelo_exacto": resultado["modelo"],
        "tipo_tarea": tipo_tarea_de(datos, newsletter, diseno),
        "input_contexto": ctx,
        "razonamiento": razonamiento,
        "accion_tipo": datos.get("accion_tipo"),
        "output_resumen": datos.get("output_resumen"),
        "output_url": url_commit(repo_dir, commit_hash),
        "cambios": cambios,
        # Con qué modelo pidió trabajar el próximo turno, y con cuál se le
        # llamó en este. Publicarlo hace visible cómo administra su gasto.
        "modelo_siguiente": datos.get("modelo_siguiente"),
        # Qué quiere buscar en su próximo turno. Se ejecuta entonces, no
        # ahora: así el ciclo sigue siendo una sola llamada por turno.
        "consultas_siguiente_turno": datos.get("consultas_siguiente_turno"),
        "busquedas_recibidas": sorted(resultados_busqueda) or None,
        # Mismo patrón que las búsquedas: qué fotos quiere para su próximo
        # turno, y qué le llegó de las que pidió en el anterior.
        "imagenes_siguiente_turno": datos.get("imagenes_siguiente_turno"),
        "imagenes_recibidas": sorted(resultados_imagenes) or None,
        # Mismo patrón: feeds RSS/Atom para el próximo turno, y los que
        # llegaron de los que pidió en el anterior. Añadido 2026-08-30.
        "feeds_siguiente_turno": datos.get("feeds_siguiente_turno"),
        "feeds_recibidos": sorted(resultados_feeds) or None,
        # Igual con las keywords consultadas en DataForSEO. Añadido 2026-08-30.
        "keywords_siguiente_turno": datos.get("keywords_siguiente_turno"),
        "keywords_recibidas": sorted(resultados_dataforseo) or None,
        # Qué pasó con el correo: enviado y a cuántos, o por qué no. Va al log
        # público porque es la métrica que decide el experimento.
        "envio": envio,
        # Avisos de la página + del cuerpo de la newsletter (si esto era un
        # turno semanal) juntos: antes de esto, avisos_nl se imprimía en el
        # log del cron y se perdía, exactamente el bug que este mecanismo
        # existe para tapar — hallazgo real de la auditoría de código.
        "avisos": (avisos + avisos_nl) or None,
        "tier_usado": tier,
        "tokens_in": resultado["tokens_in"],
        "tokens_out": resultado["tokens_out"],
        "coste_estimado": coste_estimado(resultado["modelo"], resultado["tokens_in"], resultado["tokens_out"]),
        "duracion_seg": resultado["duracion_seg"],
        "resultado": "exito",
        "detalle_error": None,
    }
    registrar_urls_publicadas(ia, base_url, archivos_nuevos)
    registrar_evento(repo_dir, evento)
    git_commit(repo_dir, f"log: registra evento {evento['evento_id']}")
    # Un solo push al final: sube el cambio y su entrada de log juntos, para
    # que el repo público nunca muestre contenido sin su justificación.
    git_push(repo_dir)
    print(f"[{ia}] commit {commit_hash}, evento registrado en log.json")

    _lanzar_matriz_imagenes(ia, datos, archivos_nuevos, dry_run)


# De qué bote de presupuesto sale cada acción, cuando el modelo no declara el
# tipo. Sin esto, 8 de los primeros turnos quedaron con `tipo_tarea` a null y
# eran ingasto sin atribuir: no aparecían en el informe por tipo de trabajo y
# el reparto entre botes los metía todos en contenido por descarte, no por
# saberlo.
TIPO_POR_ACCION = {
    "crear-articulo": "redaccion-articulo",
    "actualizar-articulo": "redaccion-articulo",
    "podar-articulo": "redaccion-articulo",
    "cambiar-meta": "seo-onpage",
    "cambiar-titular": "seo-onpage",
    "modificar-enlazado-interno": "seo-onpage",
    "modificar-cta": "seo-onpage",
    "atacar-keyword": "cambio-estrategia",
    "abandonar-keyword": "cambio-estrategia",
    "cambiar-cluster-tematico": "cambio-estrategia",
    "enviar-newsletter": "contenido-newsletter",
}


def tipo_tarea_de(datos: dict, newsletter: bool, diseno: bool) -> str:
    """El tipo con el que se registra el turno, y por tanto de qué bote sale.

    En el turno de diseño se FUERZA a "diseno" aunque el modelo declare otra
    cosa: de ese valor depende que el gasto vaya al bote de 5 € en vez de
    comerse el de contenido, y eso no puede quedar a merced de lo que el
    modelo escriba en su JSON. Es contabilidad, no una opinión suya.

    En los demás se respeta lo que declare, y solo si no declara nada se
    deduce del `accion_tipo`, que sí suele venir."""
    if diseno:
        return "diseno"
    declarado = (datos.get("tipo_tarea") or "").strip()
    # "diseno" es una etiqueta reservada: de ella depende qué bote paga el
    # turno (5 € contra 10 €) y en qué diario del marcador aparece. Un turno
    # normal no puede autoclasificarse ahí solo porque le pareció "trabajo de
    # diseño" — pasó de verdad el 2026-09-02: un turno de RECUPERACIÓN de
    # Gemini (arreglar enlaces rotos, añadir logo y favicon) se declaró a sí
    # mismo tipo_tarea="diseno" corriendo fuera del turno de diseño, y su
    # coste salió del bote de contenido con la etiqueta del otro. Se acepta
    # cualquier texto libre menos justo ese, que solo puede venir de aquí
    # arriba.
    if declarado and declarado.lower() != "diseno":
        return declarado
    if newsletter:
        return "contenido-newsletter"
    return TIPO_POR_ACCION.get(datos.get("accion_tipo"), "otro")


def _lanzar_matriz_imagenes(ia: str, datos: dict, archivos_nuevos: dict, dry_run: bool):
    """Ronda de la matriz cruzada para el artículo que se acaba de publicar.

    Va DESPUÉS del push y con todo dentro de un try: la matriz es un
    experimento paralelo y no puede tener ninguna forma de estropear la
    publicación, que es el trabajo de verdad. Si falla, se anota y ya.

    Solo para artículos NUEVOS: una mejora reescribe una página que ya tiene su
    og:image y su historial de CTR en la matriz, y generarle otra rompería la
    comparación —dejaría de saberse a cuál de las dos corresponden las
    impresiones acumuladas.

    Usa sus propias claves de imagen, así que no toca ninguno de los dos botes
    de presupuesto del agente."""
    if dry_run or datos.get("accion_tipo") != "crear-articulo":
        return
    paginas = [r for r in archivos_nuevos
               if r.endswith(".html") and "/" not in r
               and r not in ("index.html", "log.html", "privacidad.html")]
    if len(paginas) != 1:
        # Ni una página nueva identificable, o varias: sin un slug claro no se
        # puede asociar la imagen a una URL, y una fila de la matriz que apunta
        # a la URL equivocada es peor que no tenerla.
        return
    slug = paginas[0][:-len(".html")]
    tema = (datos.get("output_resumen") or slug).strip()
    try:
        import matriz_imagenes
        matriz_imagenes.generar(ia, slug, tema)
    except Exception as e:
        print(f"[{ia}] matriz de imágenes no pudo correr para {slug}: {e}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in {"claude", "gpt", "gemini", "deepseek"}:
        print("Uso: python cron_agente.py <claude|gpt|gemini|deepseek> [--newsletter|--diseno] [--dry-run]")
        sys.exit(1)
    _flags = sys.argv[2:]
    if "--newsletter" in _flags and "--diseno" in _flags:
        raise SystemExit("--newsletter y --diseno son turnos distintos: elige uno")
    ejecutar(sys.argv[1], "--newsletter" in _flags, "--dry-run" in _flags,
             diseno="--diseno" in _flags)
