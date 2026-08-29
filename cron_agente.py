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
import subprocess
import sys
import uuid
from datetime import datetime, timezone, date, timedelta
from pathlib import Path

DASHBOARD_DIR = Path(__file__).parent
sys.path.insert(0, str(DASHBOARD_DIR))
sys.path.insert(0, str(DASHBOARD_DIR / "consulta_ias"))

from clientes import llamar_con_metadata  # noqa: E402
from db import get_conn  # noqa: E402
import guardarrailes  # noqa: E402
import generar_feeds  # noqa: E402

PROMPTS_DIR = DASHBOARD_DIR / "prompts-sistema"

# Estimación aproximada a fecha de diseño (2026-08-28), tomada de las cifras
# ya calculadas en la memoria del proyecto para las variantes flagship. Las
# variantes baratas son una extrapolación, no un dato confirmado — verificar
# precios reales de las 4 consolas al darlas de alta este finde.
PRECIOS_APROX_POR_M_TOKENS = {
    "claude-sonnet-5": (2.0, 12.0),
    "claude-haiku-4-5-20251001": (0.25, 1.5),  # TODO: verificar al alta
    "gpt-5.2": (1.75, 14.0),
    "gpt-5.2-mini": (0.3, 2.5),  # TODO: verificar al alta
    "gemini-3.7-flash": (0.5, 3.0),
    "deepseek-chat": (0.15, 0.3),  # TODO: verificar al alta
    "deepseek-reasoner": (0.6, 2.2),  # TODO: verificar al alta
}


def coste_estimado(modelo: str, tokens_in: int | None, tokens_out: int | None) -> float | None:
    if tokens_in is None or tokens_out is None or modelo not in PRECIOS_APROX_POR_M_TOKENS:
        return None
    precio_in, precio_out = PRECIOS_APROX_POR_M_TOKENS[modelo]
    return round(tokens_in / 1_000_000 * precio_in + tokens_out / 1_000_000 * precio_out, 6)


def cargar_prompt_sistema(ia: str) -> str:
    base = (PROMPTS_DIR / "base_comun.md").read_text(encoding="utf-8")
    personalidad = (PROMPTS_DIR / f"personalidad_{ia}.md").read_text(encoding="utf-8")
    return base + "\n\n" + personalidad


def contexto_metricas(ia: str) -> dict:
    """Sus propias métricas + evolución vs hace ~7 días. Fuente:
    metrics_snapshot, la misma tabla que rellena poller_metrics.py — así el
    agente ve exactamente lo mismo que ya se muestra en el dashboard."""
    conn = get_conn()
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
    user = (
        f"Hoy toca {tarea}. Este es tu contexto real de métricas:\n{json.dumps(ctx, ensure_ascii=False)}\n\n"
        f"Este es el contenido actual de tus archivos:\n\n{contenido_actual_archivos(repo_dir)}"
    )

    tier = "semanal" if newsletter else "diaria"
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

    # Feeds regenerados aquí y no por la IA: es XML mecánico, sale gratis y
    # siempre correcto, y viaja en el mismo commit que el contenido.
    generar_feeds.escribir_feeds(repo_dir, base_url_agente(ia))

    commit_hash = git_commit(repo_dir, f"{datos.get('accion_tipo', 'cambio')}: {datos.get('output_resumen', '')}")

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
        "tokens_in": resultado["tokens_in"],
        "tokens_out": resultado["tokens_out"],
        "coste_estimado": coste_estimado(resultado["modelo"], resultado["tokens_in"], resultado["tokens_out"]),
        "duracion_seg": resultado["duracion_seg"],
        "resultado": "exito",
        "detalle_error": None,
    }
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
