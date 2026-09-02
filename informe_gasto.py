#!/usr/bin/env python3
"""En qué se va el presupuesto de cada agente, y si va a llegar a fin de mes.

El dato estaba desde el principio en `activity_log` —tipo de tarea, tokens,
coste y duración por turno— pero no había forma de verlo sin escribir SQL a
mano, así que en la práctica no lo miraba nadie. Un dato que existe y no se
consulta no informa ninguna decisión.

Proyecta a fin de mes con el ritmo del mes en curso, no con el de los últimos
días: el gasto de un agente varía mucho entre un turno que solo cambia un
título y uno que escribe una pieza entera, y una proyección sobre 3 días de
muestra dice más del azar que del ritmo.

Uso: informe_gasto.py [YYYY-MM]
"""
import sqlite3
import sys
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

from db import get_conn  # noqa: E402
import presupuesto as P  # noqa: E402

IAS = ["claude", "gpt", "gemini", "deepseek"]


def _dias_del_mes(mes: str) -> tuple[int, int]:
    """(días transcurridos, días del mes). Si el mes ya pasó, transcurridos =
    todos: proyectar un mes cerrado no tiene sentido."""
    anio, m = int(mes[:4]), int(mes[5:7])
    siguiente = date(anio + (m == 12), (m % 12) + 1, 1)
    total = (siguiente - date(anio, m, 1)).days
    hoy = date.today()
    if (hoy.year, hoy.month) != (anio, m):
        return total, total
    return hoy.day, total


def informe(mes: str | None = None):
    mes = mes or date.today().strftime("%Y-%m")
    transcurridos, total_dias = _dias_del_mes(mes)
    cfg = P.cargar_config()
    conn = get_conn()
    conn.row_factory = sqlite3.Row

    print(f"\nGasto de {mes} · día {transcurridos} de {total_dias}\n")
    print(f"{'ia':10}{'bote':11}{'gastado':>10}{'tope':>8}{'uso':>7}"
          f"{'proyec.':>10}{'fin de mes':>13}")
    print("─" * 69)

    for ia in IAS:
        for tipo, etiqueta in (("normal", "contenido"), (P.TIPO_DISENO, "diseño")):
            e = P.estado(ia, cfg, tipo=tipo)
            proy = e["gastado"] / transcurridos * total_dias if transcurridos else 0.0
            if e["tope"] <= 0:
                veredicto = "sin tope"
            elif proy > e["tope"]:
                # El día en que la proyección cruza el tope. Es el número
                # accionable: "se pasa" no dice si hay que actuar hoy o en
                # tres semanas.
                dia = int(e["tope"] / (e["gastado"] / transcurridos)) if e["gastado"] else total_dias
                veredicto = f"⛔ tope el día {min(dia, total_dias)}"
            elif proy > e["tope"] * P.UMBRAL_DEGRADAR:
                veredicto = "⚠ degradará"
            else:
                veredicto = "✓ holgado"
            print(f"{ia if tipo == 'normal' else '':10}{etiqueta:11}"
                  f"{e['gastado']:9.3f}€{e['tope']:7.2f}€{e['fraccion'] * 100:6.1f}%"
                  f"{proy:9.2f}€  {veredicto}")
        print()

    filas = conn.execute(
        "SELECT ia, COALESCE(tipo_tarea, '(sin declarar)') tarea, COUNT(*) n,"
        " ROUND(SUM(coste_estimado), 4) usd, ROUND(AVG(duracion_seg), 1) seg,"
        " SUM(tokens_out) salida"
        " FROM activity_log WHERE substr(timestamp, 1, 7) = ?"
        " GROUP BY ia, tarea ORDER BY usd DESC NULLS LAST", (mes,)).fetchall()
    if filas:
        print("Por tipo de trabajo\n")
        print(f"{'ia':10}{'tarea':24}{'n':>4}{'$':>10}{'seg/turno':>11}{'tokens out':>12}")
        print("─" * 71)
        for f in filas:
            print(f"{f['ia']:10}{f['tarea']:24}{f['n']:>4}{f['usd'] or 0:>10}"
                  f"{f['seg'] or 0:>11}{f['salida'] or 0:>12}")

    matriz = conn.execute(
        "SELECT COUNT(*) n, ROUND(SUM(COALESCE(coste_prompt_usd,0)"
        " + COALESCE(coste_imagen_usd,0)), 4) usd FROM imagenes_matriz"
        " WHERE substr(creado_el, 1, 7) = ?", (mes,)).fetchone()
    if matriz and matriz["n"]:
        print(f"\nMatriz de imágenes: {matriz['n']} imágenes, ${matriz['usd']} "
              f"(claves aparte, no toca los botes de los agentes)")
    conn.close()
    print()


if __name__ == "__main__":
    informe(sys.argv[1] if len(sys.argv) > 1 else None)
