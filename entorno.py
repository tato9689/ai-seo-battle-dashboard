"""Carga el .env del proyecto si las variables no vienen ya del entorno.

Por qué existe: `run_agente.sh` hace `set -a; . ~/.config/ai-seo-battle/.env`
antes de llamar a Python, así que los turnos de los agentes siempre tienen sus
claves. Pero los crons de `poller.py` y `poller_metrics.py` llaman al binario
del venv directamente, sin pasar por ese envoltorio — y ahí no hay ni una
variable.

Eso no fallaba con un error: `datos_listmonk` leía el token, encontraba el
valor por defecto "PENDIENTE" y concluía "Listmonk aún no configurado". El
log llevaba días diciendo eso y parecía una tarea pendiente de montar, cuando
Listmonk estaba levantado y con las 4 listas creadas desde el día 0
(detectado el 2026-09-01). Un fallo que se presenta como una tarea pendiente
es peor que uno que se presenta como error, porque nadie lo investiga.

Se arregla aquí y no en el crontab a propósito: en el crontab habría que
acordarse en cada línea nueva, y este es el tipo de cosa que solo se recuerda
después de que vuelva a morder.
"""
import os
from pathlib import Path

RUTA_ENV = Path("/root/.config/ai-seo-battle/.env")


def cargar_env(ruta: Path = RUTA_ENV) -> int:
    """Mete en os.environ lo que falte. No pisa lo que ya está definido: si
    alguien exportó una variable a mano o vino de `run_agente.sh`, esa manda.
    Devuelve cuántas ha añadido. Nunca lanza: sin fichero, no hace nada."""
    if not ruta.exists():
        return 0
    puestas = 0
    try:
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            clave = clave.strip()
            valor = valor.strip().strip('"').strip("'")
            if clave and clave not in os.environ:
                os.environ[clave] = valor
                puestas += 1
    except OSError:
        return puestas
    return puestas
