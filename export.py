"""Exporta activity_log + metrics_snapshot completos a CSV y JSON en export/.

Pensado para el cierre del experimento (o cualquier checkpoint): un dataset
público y descargable pesa más ante un reclutador técnico que solo gráficas.
Uso: python export.py
"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from db import get_conn

EXPORT_DIR = Path(__file__).parent / "export"


def _volcar_tabla(conn, nombre_tabla: str, fecha: str):
    filas = [dict(r) for r in conn.execute(f"SELECT * FROM {nombre_tabla} ORDER BY id").fetchall()]

    json_path = EXPORT_DIR / f"{nombre_tabla}_{fecha}.json"
    json_path.write_text(json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_path = EXPORT_DIR / f"{nombre_tabla}_{fecha}.csv"
    if filas:
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=filas[0].keys())
            writer.writeheader()
            writer.writerows(filas)

    return len(filas)


def main():
    EXPORT_DIR.mkdir(exist_ok=True)
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_conn()
    n_activity = _volcar_tabla(conn, "activity_log", fecha)
    n_metrics = _volcar_tabla(conn, "metrics_snapshot", fecha)
    conn.close()
    print(f"export {fecha}: {n_activity} filas de activity_log, {n_metrics} de metrics_snapshot en {EXPORT_DIR}")


if __name__ == "__main__":
    main()
