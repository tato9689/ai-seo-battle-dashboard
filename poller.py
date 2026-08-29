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


def derivar_fase(timestamp_iso: str, checkpoint_iso: str) -> int:
    try:
        ts = datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00"))
        checkpoint = datetime.fromisoformat(checkpoint_iso.replace("Z", "+00:00"))
        return 2 if ts >= checkpoint else 1
    except ValueError:
        return 1


def _avisar(texto: str):
    try:
        avisar_telegram(texto)
    except Exception as e:
        print(f"aviso Telegram fallido (no bloqueante): {e}", file=sys.stderr)


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

    ahora = datetime.now(timezone.utc).isoformat()
    nuevos = 0
    for ev in eventos:
        fase = derivar_fase(ev["timestamp"], checkpoint_iso)
        cur = conn.execute(
            """
            INSERT INTO activity_log
                (ia, subdominio, evento_id, timestamp, modelo_exacto, tipo_tarea,
                 input_contexto, razonamiento, accion_tipo, output_resumen, output_url,
                 tokens_in, tokens_out, coste_estimado, duracion_seg, resultado, detalle_error, fase, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ia, evento_id) DO NOTHING
            """,
            (
                ia, log_url, ev["evento_id"], ev["timestamp"], ev.get("modelo_exacto"),
                ev.get("tipo_tarea"), json.dumps(ev.get("input_contexto"), ensure_ascii=False),
                ev.get("razonamiento"), ev.get("accion_tipo"), ev.get("output_resumen"),
                ev.get("output_url"), ev.get("tokens_in"), ev.get("tokens_out"),
                ev.get("coste_estimado"), ev.get("duracion_seg"), ev.get("resultado"), ev.get("detalle_error"),
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
