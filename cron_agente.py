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

from clientes import llamar_con_metadata  # noqa: E402
from db import get_conn, init_db  # noqa: E402
import guardarrailes  # noqa: E402
import generar_feeds  # noqa: E402
import portada  # noqa: E402
import presupuesto  # noqa: E402

PROMPTS_DIR = DASHBOARD_DIR / "prompts-sistema"

# Precios (entrada, salida) en USD por millón de tokens, CONTRASTADOS con la
# documentación oficial de los 4 proveedores el 2026-08-29. La tabla anterior
# era una extrapolación y estaba muy desviada — Haiku se estimaba 4x por
# debajo de su precio real, lo que habría hecho que el freno de presupuesto
# dejara gastar cuatro veces más de lo previsto antes de saltar.
#
# De estos números depende cuándo se degrada y cuándo se corta, así que
# conviene repasarlos si algún proveedor cambia tarifas a mitad de
# experimento. La cifra que manda para facturar sigue siendo la de la consola.
PRECIOS_APROX_POR_M_TOKENS = {
    # Anthropic — precios de la referencia oficial de la API.
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-opus-5": (5.0, 25.0),
    # OpenAI — developers.openai.com/api/docs/pricing.
    "gpt-5.4-mini": (0.75, 4.5),
    "gpt-5.4": (2.5, 15.0),
    "gpt-5.5-pro-2026-04-23": (30.0, 180.0),
    # Google — ai.google.dev/gemini-api/docs/pricing. Flash tiene precio
    # promocional hasta el 31/12/2026 (después dobla): el experimento acaba
    # mucho antes, pero conviene saberlo si se alarga.
    "gemini-3.1-flash-lite": (0.25, 1.5),
    "gemini-3.7-flash": (0.75, 3.75),
    "gemini-3.1-pro-preview": (2.0, 12.0),
    # DeepSeek — api-docs.deepseek.com. Tiene tarifa punta y valle (la valle
    # es la mitad); se apuntan los precios de PUNTA a propósito, porque
    # sobreestimar el gasto es el error barato en un freno de presupuesto.
    # Horas punta: 01:00-04:00 y 06:00-10:00 UTC de lunes a viernes.
    "deepseek-v4-flash": (0.44, 1.32),
    "deepseek-v4-pro": (1.32, 3.96),
}


def precio_de(modelo: str) -> tuple[float, float] | None:
    """Precio del modelo, tolerando los snapshots con fecha.

    Las APIs devuelven el snapshot exacto que sirvieron (`gpt-5.4-mini` llega
    como `gpt-5.4-mini-2026-03-17`), y buscarlo tal cual en la tabla no
    encontraba nada: el coste salía `None` y el freno de presupuesto se
    quedaba ciego para ese agente sin que nada lo avisara. Se busca primero
    la coincidencia exacta y luego el nombre base más largo que encaje.
    """
    if not modelo:
        return None
    if modelo in PRECIOS_APROX_POR_M_TOKENS:
        return PRECIOS_APROX_POR_M_TOKENS[modelo]
    candidatos = [k for k in PRECIOS_APROX_POR_M_TOKENS if modelo.startswith(k)]
    if not candidatos:
        return None
    # El más largo evita que "gpt-5.4" se lleve lo que es de "gpt-5.4-mini".
    return PRECIOS_APROX_POR_M_TOKENS[max(candidatos, key=len)]


def coste_estimado(modelo: str, tokens_in: int | None, tokens_out: int | None) -> float | None:
    precio = precio_de(modelo)
    if precio is None:
        # Avisar en voz alta: un modelo sin precio no suma al gasto, y el
        # freno de presupuesto lo daría por gratis indefinidamente.
        print(f"AVISO: sin precio para {modelo!r}, esta llamada no cuenta para el presupuesto", file=sys.stderr)
        return None
    if tokens_in is None or tokens_out is None:
        return None
    precio_in, precio_out = precio
    return round(tokens_in / 1_000_000 * precio_in + tokens_out / 1_000_000 * precio_out, 6)


def cargar_prompt_sistema(ia: str) -> str:
    base = (PROMPTS_DIR / "base_comun.md").read_text(encoding="utf-8")
    personalidad = (PROMPTS_DIR / f"personalidad_{ia}.md").read_text(encoding="utf-8")
    return base + "\n\n" + personalidad


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


def extraer_bloque_json(texto: str) -> dict | None:
    m = re.search(r"```json\s*(\{.*?\})\s*```", texto, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def razonamiento_sin_json(texto: str) -> str:
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


def tier_elegido(repo_dir: Path, por_defecto: str) -> str:
    """Qué modelo pidió el agente para este turno en su turno anterior.

    Se lee del log real y no de un fichero de estado aparte, para que la
    elección quede publicada junto al razonamiento que la justificó: forma
    parte de lo que se enseña, no de la fontanería."""
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
        elegido = ev.get("modelo_siguiente")
        if isinstance(elegido, str) and elegido.lower() in ALIAS_TIER:
            return ALIAS_TIER[elegido.lower()]
    return por_defecto


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


def _config_agente(ia: str) -> dict:
    with open(DASHBOARD_DIR / "config.json", encoding="utf-8") as fh:
        cfg = json.load(fh)
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


def ejecutar(ia: str, newsletter: bool, dry_run: bool):
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

    system = cargar_prompt_sistema(ia)
    ctx = contexto_metricas(ia)
    tarea = "la newsletter semanal" if newsletter else "tu tarea diaria habitual"
    from clientes import MODELOS  # noqa: E402  (import local: evita ciclo al arrancar)
    ctx_presu = presupuesto.contexto_para_agente(
        ia, MODELOS.get(ia, {}), PRECIOS_APROX_POR_M_TOKENS
    )
    user = (
        f"Hoy toca {tarea}. Este es tu contexto real de métricas:\n{json.dumps(ctx, ensure_ascii=False)}\n\n"
        f"Este es tu presupuesto:\n{json.dumps(ctx_presu, ensure_ascii=False)}\n\n"
        f"Este es el contenido actual de tus archivos:\n\n{contenido_actual_archivos(repo_dir)}"
    )

    # Freno de gasto ANTES de llamar. El límite de la consola del proveedor es
    # la red final, pero salta de golpe y deja al agente mudo sin explicación;
    # esto degrada primero y solo para del todo al llegar al tope.
    presu = presupuesto.estado(ia)
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
    tier = tier_elegido(repo_dir, por_defecto="semanal" if newsletter else "diaria")
    if presu["degradar"] and tier == "semanal":
        # Único caso en que el sistema le pisa la elección: cerca del tope,
        # una newsletter con el modelo pequeño es mejor que quedarse sin turnos.
        print(f"[{ia}] {presu['motivo']}")
        tier = "diaria"
    resultado = llamar_con_metadata(ia, system, user, tier=tier)
    texto = resultado["texto"]

    if texto.startswith("[sin ") and texto.endswith("configurada]"):
        print(f"[{ia}] {texto}")
        return

    datos = extraer_bloque_json(texto)
    if datos is None:
        print(f"[{ia}] no se pudo parsear el bloque JSON de la respuesta — no se aplica nada.", file=sys.stderr)
        print(texto)
        return

    razonamiento = razonamiento_sin_json(texto)
    print(f"[{ia}] {datos.get('accion_tipo')}: {datos.get('output_resumen')}")

    if dry_run:
        print("--dry-run: no se escribe ni commitea nada.")
        print(json.dumps(datos, ensure_ascii=False, indent=2))
        return

    archivos = datos.get("archivos", [])
    try:
        destinos = [(ruta_segura(repo_dir, a["ruta"]), a["contenido_completo"]) for a in archivos]
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
            "tipo_tarea": datos.get("tipo_tarea"),
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
        })
        git_commit(repo_dir, "log: registra intento bloqueado por guardarraíles")
        # Los bloqueos también se publican: enseñar dónde se equivoca cada IA
        # es parte de la transparencia, no algo que esconder.
        git_push(repo_dir)
        return

    for destino, contenido in destinos:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")

    base_url = base_url_agente(ia)
    # Portadas y feeds los genera el sistema, no la IA: es trabajo mecánico
    # que sale gratis, siempre correcto, y viaja en el mismo commit que el
    # contenido al que pertenece.
    portada.escribir_para(repo_dir, list(archivos_nuevos), ia, base_url)
    generar_feeds.escribir_feeds(repo_dir, base_url)

    commit_hash = git_commit(repo_dir, f"{datos.get('accion_tipo', 'cambio')}: {datos.get('output_resumen', '')}")
    cambios = resumen_cambios(repo_dir, commit_hash)

    evento = {
        "evento_id": f"{date.today().isoformat()}-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "modelo_exacto": resultado["modelo"],
        "tipo_tarea": datos.get("tipo_tarea"),
        "input_contexto": ctx,
        "razonamiento": razonamiento,
        "accion_tipo": datos.get("accion_tipo"),
        "output_resumen": datos.get("output_resumen"),
        "output_url": url_commit(repo_dir, commit_hash),
        "cambios": cambios,
        # Con qué modelo pidió trabajar el próximo turno, y con cuál se le
        # llamó en este. Publicarlo hace visible cómo administra su gasto.
        "modelo_siguiente": datos.get("modelo_siguiente"),
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


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in {"claude", "gpt", "gemini", "deepseek"}:
        print("Uso: python cron_agente.py <claude|gpt|gemini|deepseek> [--newsletter] [--dry-run]")
        sys.exit(1)
    ejecutar(sys.argv[1], "--newsletter" in sys.argv[2:], "--dry-run" in sys.argv[2:])
