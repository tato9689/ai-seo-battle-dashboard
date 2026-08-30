"""Envío de la newsletter semanal por Listmonk.

Hueco que tapa este módulo (2026-08-30): el contrato de salida pide un campo
`newsletter` con `{asunto, cuerpo_html}` cuando la acción es
`enviar-newsletter`, pero nadie lo leía nunca y en todo el repo no había una
sola llamada que creara una campaña — `poller_metrics.py` toca `/campaigns`,
pero solo para LEER la tasa de apertura. El turno del domingo gastaba el
modelo flagship, publicaba la pieza y el correo no salía de aquí.

Dos decisiones de diseño:

  - **Con 0 suscriptores confirmados el turno semanal ni se hace.** No es
    contenido de más: es el único turno que usa el modelo caro de cada casa y
    el presupuesto tiene que llegar a 10 meses. La pieza pública de esa
    semana ya la ha escrito el turno diario del mismo domingo, así que no se
    pierde nada indexable. Lo aplica `cron_agente.py` ANTES de llamar a la
    API, con `hay_a_quien_enviar()`.
  - **Solo cuentan los confirmados.** Las 4 listas son de doble opt-in: el
    `subscriber_count` que devuelve Listmonk incluye a quien se apuntó y
    nunca confirmó, y a ese Listmonk no le envía. Contar el total daría
    turnos caros que acaban en un envío a cero personas.
"""

import os

import httpx

TIMEOUT = 15


def _credenciales(cfg: dict) -> tuple[str, dict]:
    # Mismo convenio que poller_metrics.py: "env:NOMBRE" saca el valor del
    # entorno porque config.json está versionado en git.
    base = cfg.get("listmonk_base_url", "")
    token = cfg.get("listmonk_api_token", "")
    if isinstance(token, str) and token.startswith("env:"):
        token = os.environ.get(token[4:], "PENDIENTE")
    if not base or "PENDIENTE" in base or "PENDIENTE" in str(token):
        raise RuntimeError("Listmonk aún no configurado")
    return base, {"Authorization": f"token {token}"}


def confirmados(cfg: dict, list_id) -> int:
    """Suscriptores de esa lista que pueden recibir un envío de verdad."""
    if not list_id:
        raise RuntimeError("el agente no tiene listmonk_list_id en config.json")
    base, cabeceras = _credenciales(cfg)
    resp = httpx.get(
        f"{base}/subscribers",
        params={"list_id": list_id, "subscription_status": "confirmed", "per_page": 1},
        headers=cabeceras,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return int(resp.json()["data"]["total"])


def hay_a_quien_enviar(cfg: dict, list_id) -> tuple[bool, str]:
    """(seguir_con_el_turno, motivo).

    Si Listmonk no contesta se sigue adelante a propósito: quedarse sin la
    pieza semanal por una caída del sistema de envío sería peor que gastar un
    turno de más, y el motivo queda escrito en el log para que se vea.
    """
    try:
        n = confirmados(cfg, list_id)
    except Exception as e:
        return True, f"no se pudo consultar Listmonk ({e}) — se hace el turno igualmente"
    if n == 0:
        return False, "0 suscriptores confirmados"
    return True, f"{n} suscriptores confirmados"


def enviar(cfg: dict, ia: str, list_id, asunto: str, cuerpo_html: str) -> dict:
    """Crea la campaña y la pone a enviar. Devuelve lo que se registra en el
    log público del agente."""
    if not asunto or not cuerpo_html:
        return {"enviado": False, "motivo": "el modelo no devolvió asunto o cuerpo"}

    base, cabeceras = _credenciales(cfg)
    n = confirmados(cfg, list_id)
    if n == 0:
        # Puede pasar aunque el turno arrancara con lista no vacía (bajas
        # entre medias). Barato de comprobar, evita una campaña fantasma.
        return {"enviado": False, "motivo": "0 suscriptores confirmados", "suscriptores": 0}

    # Sin `template_id` a propósito: Listmonk aplica su plantilla por defecto,
    # que es la que trae el enlace de baja. Un envío sin enlace de baja no es
    # un detalle de formato, es un incumplimiento de RGPD — y aquí hay 4
    # responsables de tratamiento distintos, uno por newsletter.
    creada = httpx.post(
        f"{base}/campaigns",
        headers=cabeceras,
        timeout=TIMEOUT,
        json={
            "name": f"{ia} — {asunto}"[:200],
            "subject": asunto,
            "lists": [int(list_id)],
            "type": "regular",
            "content_type": "richtext",
            "body": cuerpo_html,
        },
    )
    creada.raise_for_status()
    campana = creada.json()["data"]

    arrancada = httpx.put(
        f"{base}/campaigns/{campana['id']}/status",
        headers=cabeceras,
        timeout=TIMEOUT,
        json={"status": "running"},
    )
    arrancada.raise_for_status()

    return {
        "enviado": True,
        "campana_id": campana["id"],
        "asunto": asunto,
        "suscriptores": n,
    }
