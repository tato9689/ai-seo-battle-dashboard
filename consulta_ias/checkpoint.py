"""Arma automáticamente el post-mortem de un checkpoint (mes 5, cierre)
con los datos reales de cada IA (activity_log + metrics_snapshot) y lanza
debate.py en modo checkpoint para que cada una analice su propia estrategia
y puntúe a las otras 3.

Uso: python checkpoint.py "mes 5"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import get_conn  # noqa: E402

from debate import debate, ORDEN_BASE


def resumen_datos_reales() -> str:
    conn = get_conn()
    bloques = []
    for ia in ORDEN_BASE:
        acciones = conn.execute(
            "SELECT COUNT(*) AS n, SUM(coste_estimado) AS coste FROM activity_log WHERE ia = ?", (ia,)
        ).fetchone()
        ultimo = conn.execute(
            "SELECT * FROM metrics_snapshot WHERE ia = ? ORDER BY fecha DESC LIMIT 1", (ia,)
        ).fetchone()
        bloques.append(
            f"- {ia}: {acciones['n'] or 0} acciones, {(acciones['coste'] or 0):.3f}$ gastados. "
            + (
                f"Último dato: {ultimo['suscriptores_totales'] or 0} suscriptores, "
                f"{ultimo['vistas_ga4'] or 0} vistas, posición media GSC {ultimo['posicion_media_gsc'] or '–'} "
                f"(snapshot {ultimo['fecha']})."
                if ultimo else "sin snapshot de métricas todavía."
            )
        )
    conn.close()
    return "\n".join(bloques)


def main():
    etiqueta = sys.argv[1] if len(sys.argv) > 1 else "checkpoint"
    datos = resumen_datos_reales()
    pregunta = (
        f"Checkpoint de {etiqueta} del experimento AI SEO Battle. Aquí están los "
        f"resultados reales de cada una hasta ahora:\n\n{datos}\n\n"
        "Analiza tu propia estrategia con estos datos: qué ha funcionado, qué "
        "cambiarías, y valora la de las otras tres."
    )
    path = debate(pregunta, rondas=1, modo="checkpoint")
    print(f"Acta de checkpoint guardada en {path}")


if __name__ == "__main__":
    main()
