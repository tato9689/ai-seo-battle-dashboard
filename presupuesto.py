"""Presupuesto por agente: cada IA administra el suyo, con una red debajo.

**Quién elige el modelo es el propio agente**, no este módulo: gastar el
modelo caro en la pieza semanal o repartirlo en varios días es una decisión
estratégica con consecuencias reales, y administrar bien los recursos es
parte de lo que el experimento mide. Aquí se le da la información para
decidir (`contexto_para_agente`) y se ponen los límites que no puede cruzar.

El límite duro de la consola del proveedor es la red final, pero es un freno
brusco: cuando salta, la API empieza a fallar a mitad de experimento y el
agente se queda mudo sin explicación. Esta es la capa de antes:

  - hasta el 80% del tope: manda la elección del agente, sin tocarla.
  - del 80% al 100%: se le fuerza el modelo barato aunque hubiera pedido el
    potente. Una newsletter escrita con el modelo pequeño es mejor que
    quedarse sin turnos a mitad de mes.
  - a partir del 100%: no se llama. El turno queda registrado como bloqueado
    por presupuesto, para que en el log público se vea que fue el tope y no
    que el agente dejó de trabajar por su cuenta.

El gasto sale de `coste_estimado` de `activity_log`, que es una estimación
con la tabla de precios de cron_agente. Sirve para decidir, no para
facturar: la cifra que manda siempre es la de la consola del proveedor.
"""
import calendar
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
from db import get_conn  # noqa: E402

CONFIG_PATH = BASE / "config.json"

UMBRAL_DEGRADAR = 0.80
TOPE_POR_DEFECTO = 5.0  # €/mes por API, el acordado para el experimento
# Los costes se estiman en dólares (así los publican los 4 proveedores) y el
# tope se fija en euros. Se aplica una conversión aproximada y conservadora:
# no hace falta precisión de contabilidad para decidir si degradar, y errar
# por el lado de gastar menos es el error barato.
USD_POR_EUR = 1.08


def cargar_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


# Dos botes por agente y no uno solo. Con un único tope, el turno semanal de
# diseño —que usa el modelo capaz y produce ficheros grandes— se come el
# presupuesto de los turnos diarios de contenido, que son 7 veces más
# frecuentes y son los que sostienen el corpus. Separarlos hace que un mes caro
# de diseño no pueda dejar al agente sin escribir, ni al revés. El reparto es
# 10 € contenido + 5 € diseño (2026-09-01).
TOPE_DISENO_POR_DEFECTO = 5.0
TIPO_DISENO = "diseno"


def tope_mensual(cfg: dict, ia: str, tipo: str = "normal") -> float:
    """Tope en euros del bote que toca. Se puede fijar por agente en
    config.json; si no, el global; si tampoco, el acordado por defecto."""
    clave = "tope_diseno_eur" if tipo == TIPO_DISENO else "tope_mensual_eur"
    defecto = TOPE_DISENO_POR_DEFECTO if tipo == TIPO_DISENO else TOPE_POR_DEFECTO
    for agente in cfg.get("agentes", []):
        if agente.get("ia") == ia and agente.get(clave) is not None:
            return float(agente[clave])
    return float(cfg.get(clave, defecto))


def gasto_del_mes(ia: str, hoy: date | None = None, tipo: str = "normal") -> float:
    """Gasto estimado del mes en curso, en euros, del bote que toca.

    El reparto se hace por `tipo_tarea` del propio log: los turnos de diseño se
    registran como "diseno" y todo lo demás cae en el bote de contenido. Las
    filas sin `tipo_tarea` (turnos saltados, errores tempranos) cuentan como
    contenido, que es donde estaban antes de existir esta separación."""
    hoy = hoy or date.today()
    prefijo = hoy.strftime("%Y-%m")
    filtro = ("AND tipo_tarea = ?" if tipo == TIPO_DISENO
              else "AND (tipo_tarea IS NULL OR tipo_tarea != ?)")
    try:
        conn = get_conn()
        fila = conn.execute(
            "SELECT SUM(coste_estimado) total FROM activity_log"
            f" WHERE ia = ? AND substr(timestamp, 1, 7) = ? {filtro}",
            (ia, prefijo, TIPO_DISENO),
        ).fetchone()
        conn.close()
    except sqlite3.Error as e:
        # Base todavía sin crear (instalación nueva) o ilegible. Sin registro
        # de gasto, el gasto conocido es cero: no puede ser motivo para dejar
        # a un agente sin trabajar, y el límite de la consola sigue detrás.
        print(f"no se pudo leer el gasto de {ia}, se asume 0: {e}", file=sys.stderr)
        return 0.0
    return (fila["total"] or 0.0) / USD_POR_EUR


def estado(ia: str, cfg: dict | None = None, hoy: date | None = None,
           tipo: str = "normal") -> dict:
    """{gastado, tope, fraccion, permitir, degradar, motivo} del bote que toca."""
    cfg = cfg or cargar_config()
    tope = tope_mensual(cfg, ia, tipo)
    gastado = gasto_del_mes(ia, hoy, tipo)
    fraccion = (gastado / tope) if tope > 0 else 0.0

    if fraccion >= 1.0:
        return {
            "gastado": gastado, "tope": tope, "fraccion": fraccion,
            "permitir": False, "degradar": True,
            "motivo": f"tope mensual alcanzado ({gastado:.2f}€ de {tope:.2f}€)",
        }
    if fraccion >= UMBRAL_DEGRADAR:
        return {
            "gastado": gastado, "tope": tope, "fraccion": fraccion,
            "permitir": True, "degradar": True,
            "motivo": f"{fraccion:.0%} del tope gastado, se usa el modelo barato",
        }
    return {
        "gastado": gastado, "tope": tope, "fraccion": fraccion,
        "permitir": True, "degradar": False, "motivo": "",
    }


def contexto_para_agente(ia: str, modelos: dict, precios: dict, cfg: dict | None = None) -> dict:
    """Lo que el agente necesita para administrar su propio presupuesto.

    Elegir modelo es una decisión estratégica suya, no del sistema: gastar el
    modelo caro en la newsletter semanal o repartirlo en varias piezas
    diarias es exactamente el tipo de criterio que el experimento quiere
    medir. Para poder decidir necesita saber qué le queda y qué cuesta cada
    opción — sin eso estaría eligiendo a ciegas.
    """
    e = estado(ia, cfg)
    hoy = date.today()
    dias_mes = calendar.monthrange(hoy.year, hoy.month)[1]
    dia = min(hoy.day, dias_mes)
    dias_hasta_reinicio = dias_mes - hoy.day
    # Ritmo: cuánto llevaría gastado si el gasto fuera parejo todo el mes.
    esperado = e["tope"] * dia / dias_mes
    return {
        "gastado_este_mes_eur": round(e["gastado"], 3),
        "tope_mensual_eur": e["tope"],
        "queda_eur": round(max(e["tope"] - e["gastado"], 0), 3),
        "vas_por_delante_del_ritmo": bool(e["gastado"] > esperado),
        "dias_hasta_reinicio_del_tope": dias_hasta_reinicio,
        "modelos_disponibles": {
            "barato": {
                "modelo": modelos.get("diaria"),
                "precio_por_millon_tokens_usd": precios.get(modelos.get("diaria")),
            },
            "potente": {
                "modelo": modelos.get("semanal"),
                "precio_por_millon_tokens_usd": precios.get(modelos.get("semanal")),
            },
        },
        "nota": ("Eliges tú con cuál trabajar en tu PRÓXIMO turno, con el campo "
                 "modelo_siguiente. Si agotas el tope, no se te llama en lo que "
                 "queda de mes y pierdes turnos. El tope es mensual y NO se "
                 "acumula: lo que no gastes en 'queda_eur' antes de "
                 "dias_hasta_reinicio_del_tope no pasa al mes siguiente, se "
                 "pierde sin más. Si quedan pocos días, ahorrar ya no tiene "
                 "premio — gasta acorde a lo que de verdad mejore tu turno."),
    }


def resumen() -> list[dict]:
    cfg = cargar_config()
    return [dict(estado(a["ia"], cfg), ia=a["ia"]) for a in cfg.get("agentes", [])]


if __name__ == "__main__":
    for e in resumen():
        barra = "█" * int(min(e["fraccion"], 1.0) * 20)
        print(f'{e["ia"]:10} {e["gastado"]:6.3f}€ / {e["tope"]:.2f}€  {barra:<20} '
              f'{e["fraccion"]:5.0%}  {e["motivo"]}')
