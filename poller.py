"""Lee /log.json de cada uno de los 4 agentes y lo consolida en SQLite.

Pensado para correr por cron (no como proceso persistente): un pase, upsert
de lo nuevo, sale. Idempotente por (ia, evento_id).
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

from avisos import enviar as avisar_telegram
from db import get_conn, init_db

BASE = Path(__file__).parent
CONFIG_PATH = BASE / "config.json"


def cargar_config():
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _aware(dt: datetime) -> datetime:
    """Una fecha sin zona horaria ('2026-10-05', el formato natural que se
    escribe a mano en config.json) no se puede comparar con un timestamp con
    zona: Python lanza TypeError. Se asume UTC, que es la zona en la que los
    agentes escriben sus timestamps."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def derivar_fase(timestamp_iso: str, checkpoint_iso: str) -> int:
    try:
        ts = _aware(datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00")))
        checkpoint = _aware(datetime.fromisoformat(checkpoint_iso.replace("Z", "+00:00")))
        return 2 if ts >= checkpoint else 1
    except (ValueError, TypeError):
        # Caer a fase 1 es lo seguro (nunca abre el acceso competitivo por
        # accidente), pero hacerlo en silencio significaría que un
        # checkpoint_fase2 sin poner deja el experimento entero en fase 1 para
        # siempre sin que nadie se entere. Se avisa una vez por proceso.
        global _AVISADO_CHECKPOINT
        if not _AVISADO_CHECKPOINT:
            _AVISADO_CHECKPOINT = True
            print(
                f"AVISO: checkpoint_fase2 = {checkpoint_iso!r} no es una fecha válida. "
                "Todo se registrará como fase 1 hasta que se ponga la fecha real en config.json.",
                file=sys.stderr,
            )
        return 1


_AVISADO_CHECKPOINT = False


def _avisar(texto: str):
    try:
        avisar_telegram(texto)
    except Exception as e:
        print(f"aviso Telegram fallido (no bloqueante): {e}", file=sys.stderr)


# Tope de eventos por poll: un agente con el log corrupto (o creciendo sin
# control) no debe poder inundar la base ni el canal de Telegram de un tirón.
MAX_EVENTOS_POR_POLL = 200
MAX_LARGO_TEXTO = 20000  # razonamiento/resumen: recorta, no rechaza


def evento_valido(ev) -> bool:
    """El /log.json lo escribe una IA sin supervisión diaria: es entrada no
    confiable, igual que las rutas de archivo en cron_agente.py. Sin esto, un
    evento sin 'timestamp' o sin 'evento_id' tumbaba el poll entero de ese
    agente con un KeyError y se perdían también los eventos correctos."""
    if not isinstance(ev, dict):
        return False
    for campo in ("evento_id", "timestamp"):
        valor = ev.get(campo)
        if not isinstance(valor, str) or not valor.strip():
            return False
    return True


def _texto(valor, limite: int = MAX_LARGO_TEXTO):
    """Normaliza a texto acotado. Un modelo puede devolver un número, una
    lista o un razonamiento de megabytes donde el contrato pide una cadena."""
    if valor is None:
        return None
    if not isinstance(valor, str):
        valor = json.dumps(valor, ensure_ascii=False)
    return valor[:limite]


def _numero(valor):
    """Los campos de tokens/coste/duración alimentan las gráficas y el KPI de
    coste por suscriptor — un string colado ahí rompe las agregaciones."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    return valor


def poll_agente(conn, ia: str, log_url: str, checkpoint_iso: str) -> int:
    try:
        resp = httpx.get(log_url, timeout=10)
        resp.raise_for_status()
        eventos = resp.json()
    except Exception as e:
        print(f"[{ia}] error consultando {log_url}: {e}", file=sys.stderr)
        return 0

    ya_fase2 = conn.execute(
        "SELECT 1 FROM activity_log WHERE ia = ? AND fase = 2 LIMIT 1", (ia,)
    ).fetchone() is not None

    if not isinstance(eventos, list):
        print(f"[{ia}] {log_url} no devolvió una lista de eventos — se ignora este poll.", file=sys.stderr)
        return 0

    ahora = datetime.now(timezone.utc).isoformat()
    nuevos = 0
    descartados = 0
    for ev in eventos[:MAX_EVENTOS_POR_POLL]:
        if not evento_valido(ev):
            descartados += 1
            continue
        fase = derivar_fase(ev["timestamp"], checkpoint_iso)
        cur = conn.execute(
            """
            INSERT INTO activity_log
                (ia, subdominio, evento_id, timestamp, modelo_exacto, tipo_tarea,
                 input_contexto, razonamiento, accion_tipo, output_resumen, output_url, cambios,
                 tokens_in, tokens_out, coste_estimado, duracion_seg, resultado, detalle_error, fase, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ia, evento_id) DO NOTHING
            """,
            (
                ia, log_url, _texto(ev["evento_id"], 200), _texto(ev["timestamp"], 40),
                _texto(ev.get("modelo_exacto"), 100),
                _texto(ev.get("tipo_tarea"), 100), json.dumps(ev.get("input_contexto"), ensure_ascii=False)[:MAX_LARGO_TEXTO],
                _texto(ev.get("razonamiento")), _texto(ev.get("accion_tipo"), 100), _texto(ev.get("output_resumen"), 2000),
                _texto(ev.get("output_url"), 500),
                json.dumps(ev.get("cambios"), ensure_ascii=False)[:4000] if ev.get("cambios") else None,
                _numero(ev.get("tokens_in")), _numero(ev.get("tokens_out")),
                _numero(ev.get("coste_estimado")), _numero(ev.get("duracion_seg")),
                _texto(ev.get("resultado"), 20), _texto(ev.get("detalle_error"), 2000),
                fase, ahora,
            ),
        )
        if cur.rowcount == 0:
            continue
        nuevos += 1

        if ev.get("resultado") == "error":
            _avisar(f"⚠️ AI SEO Battle: {ia} tuvo un error en '{ev.get('accion_tipo', '?')}'\n{ev.get('detalle_error', '')}")

        if fase == 2 and not ya_fase2:
            ya_fase2 = True
            _avisar(f"🔓 AI SEO Battle: {ia} entra en fase 2 (inteligencia competitiva)")

    if descartados:
        print(f"[{ia}] {descartados} eventos descartados por no cumplir el contrato de /log.json", file=sys.stderr)
    if len(eventos) > MAX_EVENTOS_POR_POLL:
        print(f"[{ia}] /log.json traía {len(eventos)} eventos, solo se leyeron los {MAX_EVENTOS_POR_POLL} primeros", file=sys.stderr)

    conn.commit()
    return nuevos


def main():
    init_db()
    cfg = cargar_config()
    conn = get_conn()
    total = 0
    for agente in cfg["agentes"]:
        total += poll_agente(conn, agente["ia"], agente["log_url"], cfg["checkpoint_fase2"])
    conn.close()
    print(f"poll completo: {total} eventos nuevos")


if __name__ == "__main__":
    main()
