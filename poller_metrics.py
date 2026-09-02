"""Snapshot diario de métricas de RESULTADO por IA (no acciones, eso es poller.py).

Responde a "cómo sabe que le va bien a una IA": tráfico (GA4 + Search
Console del subdominio) y leads reales (suscriptores netos + tasa de
apertura vía Listmonk). Mismo mecanismo de acceso que ya usa
/root/tato9689-panel/metricas.py: service account de Google con
analytics.readonly + webmasters.readonly.

Pensado para cron diario (una fila por ia+fecha, upsert). Cada fuente falla
de forma independiente y aislada: si Listmonk aún no existe o una property
GA4 no está creada, esa fuente queda a None pero las demás se guardan igual.
"""
import json
import os
import sys
from datetime import datetime, timezone, date, timedelta
from pathlib import Path

import httpx

from entorno import cargar_env

cargar_env()
from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric
from googleapiclient.discovery import build

from avisos import enviar as avisar_telegram
from db import get_conn, init_db


def _avisar(texto: str):
    try:
        avisar_telegram(texto)
    except Exception as e:
        print(f"aviso Telegram fallido (no bloqueante): {e}", file=sys.stderr)

BASE = Path(__file__).parent
CONFIG_PATH = BASE / "config.json"

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
]


def cargar_config():
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def credenciales(cred_path: str):
    return service_account.Credentials.from_service_account_file(cred_path, scopes=SCOPES)


def datos_ga4(creds, property_id: str) -> dict:
    client = BetaAnalyticsDataClient(credentials=creds)
    resp = client.run_report(RunReportRequest(
        property=property_id,
        date_ranges=[DateRange(start_date="yesterday", end_date="yesterday")],
        metrics=[Metric(name="sessions"), Metric(name="activeUsers"), Metric(name="screenPageViews")],
    ))
    fila = resp.rows[0] if resp.rows else None
    return {
        "sesiones": int(fila.metric_values[0].value) if fila else 0,
        "usuarios": int(fila.metric_values[1].value) if fila else 0,
        "vistas": int(fila.metric_values[2].value) if fila else 0,
    }


def consultas_gsc(creds, site_url: str, dias: int = 28, tope: int = 25) -> list[dict]:
    """Las búsquedas por las que ya te ven, una por fila.

    `datos_gsc` devuelve el agregado del sitio —tres números— y con eso no se
    puede decidir nada: dice CUÁNTO, nunca QUÉ. Esto devuelve la dimensión
    `query`, que es de donde salen los temas demostrados: una consulta con
    impresiones y posición 4-25 es algo que Google ya asocia con este sitio,
    que alguien busca de verdad, y para lo que todavía no hay una página que
    lo responda bien. Eso no se puede inventar desde el escritorio.

    Ventana de 28 días y no 2: en un sitio nuevo las búsquedas de un día son
    ruido, y la señal solo aparece acumulando. GSC consolida con 3 días de
    retraso, así que la ventana termina ahí.

    Nunca lanza: si GSC falla o el sitio aún no tiene datos, lista vacía. Es
    contexto, no una dependencia del turno."""
    try:
        service = build("searchconsole", "v1", credentials=creds)
        fin = date.today() - timedelta(days=3)
        inicio = fin - timedelta(days=dias)
        resp = service.searchanalytics().query(
            siteUrl=site_url,
            body={
                "startDate": inicio.isoformat(),
                "endDate": fin.isoformat(),
                "dimensions": ["query"],
                "rowLimit": tope,
                "dataState": "final",
            },
        ).execute()
    except Exception as e:
        print(f"consultas GSC no disponibles para {site_url}: {e}", file=sys.stderr)
        return []
    filas = []
    for r in resp.get("rows", []):
        claves = r.get("keys") or [""]
        filas.append({
            "consulta": claves[0],
            "clics": int(r.get("clicks", 0)),
            "impresiones": int(r.get("impressions", 0)),
            "ctr": round(r.get("ctr", 0) * 100, 2),
            "posicion": round(r.get("position", 0), 1),
        })
    filas.sort(key=lambda f: f["impresiones"], reverse=True)
    return filas


def datos_gsc(creds, site_url: str) -> dict:
    service = build("searchconsole", "v1", credentials=creds)
    fin = date.today() - timedelta(days=3)  # GSC tarda en consolidar
    inicio = fin - timedelta(days=1)
    resp = service.searchanalytics().query(
        siteUrl=site_url,
        body={"startDate": inicio.isoformat(), "endDate": fin.isoformat()},
    ).execute()
    filas = resp.get("rows", [])
    r = filas[0] if filas else {}
    return {
        "clics": int(r.get("clicks", 0)),
        "impresiones": int(r.get("impressions", 0)),
        "posicion_media": round(r.get("position", 0), 1),
    }


def urls_con_impresiones(creds, site_url: str, dias: int = 30) -> set[str]:
    """URLs del sitio que ya han aparecido alguna vez en resultados. Es la
    señal de indexación más fiable que da la API: 'aparece en búsquedas'
    implica indexada, mientras que la Inspection API tiene una cuota diaria
    muy baja y no serviría para vigilar 4 sitios a diario."""
    service = build("searchconsole", "v1", credentials=creds)
    fin = date.today() - timedelta(days=3)
    resp = service.searchanalytics().query(
        siteUrl=site_url,
        body={
            "startDate": (fin - timedelta(days=dias)).isoformat(),
            "endDate": fin.isoformat(),
            "dimensions": ["page"],
            "rowLimit": 500,
        },
    ).execute()
    return {r["keys"][0] for r in resp.get("rows", []) if r.get("keys")}


def registrar_indexacion(conn, ia: str, creds, site_url: str):
    """Marca la fecha en que cada URL publicada aparece por primera vez en
    Search Console. Solo escribe la primera vez: 'cuándo se indexó' es un
    hecho que no cambia, y sobrescribirlo perdería el dato."""
    pendientes = conn.execute(
        "SELECT url FROM indexacion WHERE ia = ? AND primera_impresion IS NULL", (ia,)
    ).fetchall()
    if not pendientes:
        return
    vistas = urls_con_impresiones(creds, site_url)
    hoy = date.today().isoformat()
    for fila in pendientes:
        if fila["url"] not in vistas:
            continue
        conn.execute(
            "UPDATE indexacion SET primera_impresion = ?,"
            " dias_hasta_indexar = CAST(julianday(?) - julianday(fecha_publicacion) AS INTEGER)"
            " WHERE ia = ? AND url = ? AND primera_impresion IS NULL",
            (hoy, hoy, ia, fila["url"]),
        )


def datos_listmonk(base_url: str, token: str, list_id) -> dict:
    # "env:NOMBRE" saca el valor del entorno: el token no puede vivir en
    # config.json, que está versionado en git.
    if isinstance(token, str) and token.startswith("env:"):
        token = os.environ.get(token[4:], "PENDIENTE")
    if not list_id or "PENDIENTE" in base_url or "PENDIENTE" in token:
        raise RuntimeError("Listmonk aún no configurado")
    resp = httpx.get(
        f"{base_url}/lists/{list_id}",
        headers={"Authorization": f"token {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()["data"]

    confirmados = _confirmados(base_url, token, list_id)
    salida = {
        # Se cuenta explícitamente con `subscription_status=confirmed` y no con
        # el `subscriber_count` de la lista: ese valor lo cachea Listmonk y su
        # criterio con el doble opt-in no está garantizado entre versiones. La
        # métrica que decide el experimento no puede depender de una caché
        # ajena, y un suscriptor sin confirmar NO cuenta: no ha dado su
        # consentimiento todavía.
        "suscriptores_totales": confirmados,
        # netos_dia lo calcula poll_ia contra el snapshot del día anterior:
        # Listmonk da el total vivo, no la variación.
        "suscriptores_netos_dia": None,
        "tasa_apertura_ultimo_envio": _tasa_apertura(base_url, token, list_id),
        # Todo suscriptor confirmado es orgánico POR REGLA del experimento: el
        # tráfico de pago está prohibido y el filtro bloquea los incentivos por
        # registro. Antes esto se leía de `attribs.origen`, que el formulario
        # público de Listmonk IGNORA a propósito —probado el 2026-09-01 con
        # tres nombres de campo distintos, los tres devuelven attribs vacío—
        # así que esa columna habría dado 0 para siempre, y es la que decide
        # quién gana. Un cero que parece «todavía no ha entrado nadie» es el
        # peor sitio donde tener un fallo.
        "suscriptores_organicos": confirmados,
        # `None` y no `0`: no se distingue el origen, y eso no es lo mismo que
        # haber medido cero. Si algún día hace falta el desglose de verdad,
        # hay que poner un endpoint propio delante del formulario que fije
        # `origen` desde el servidor y llame a la API — el formulario público
        # nunca va a poder hacerlo.
        "suscriptores_meta": None,
        "suscriptores_directos": None,
    }
    return salida


def _confirmados(base_url: str, token: str, list_id) -> int:
    """Suscriptores confirmados y activos de una lista. 0 si algo falla: es un
    contador, y devolver None aquí haría que el dashboard pintara un hueco
    donde debería haber un número."""
    try:
        resp = httpx.get(
            f"{base_url}/subscribers",
            params={"list_id": list_id, "subscription_status": "confirmed",
                    "query": "subscribers.status='enabled'", "per_page": 1},
            headers={"Authorization": f"token {token}"},
            timeout=10,
        )
        resp.raise_for_status()
        return int(resp.json()["data"]["total"])
    except Exception as e:
        print(f"no se pudo contar confirmados de la lista {list_id}: {e}", file=sys.stderr)
        return 0


def _tasa_apertura(base_url: str, token: str, list_id) -> float | None:
    """% de apertura del último envío terminado de esa lista. Es la métrica
    secundaria de calidad del experimento (un suscriptor que nunca abre no
    vale lo mismo que uno que lee), así que no puede quedarse en None."""
    try:
        resp = httpx.get(
            f"{base_url}/campaigns",
            params={"list_id": list_id, "status": "finished", "per_page": 1, "order_by": "created_at", "order": "DESC"},
            headers={"Authorization": f"token {token}"},
            timeout=10,
        )
        resp.raise_for_status()
        resultados = resp.json()["data"].get("results") or []
        if not resultados:
            return None
        campana = resultados[0]
        enviados = campana.get("sent") or 0
        if not enviados:
            return None
        # Listmonk cuenta vistas totales, no únicas: dos aperturas del mismo
        # lector inflarían la tasa por encima de 100%, así que se acota.
        return round(min(campana.get("views", 0) / enviados, 1.0) * 100, 2)
    except Exception as e:
        print(f"tasa de apertura no disponible: {e}", file=sys.stderr)
        return None


# `_desglose_origen` se retiró el 2026-09-01. Consultaba
# `subscribers.attribs->>'origen'`, un atributo que el formulario público de
# Listmonk nunca llega a guardar: ignora cualquier campo de atributos que le
# mandes (probado con attribs_origen, attribs y attribs[origen]). La función
# devolvía siempre ceros y alimentaba la métrica que decide el experimento.
# Si vuelve a hacer falta el desglose, no se resucita esto: hace falta un
# endpoint propio delante del formulario que fije el origen desde el servidor.

def poll_ia(conn, cfg, agente: dict) -> bool:
    ia = agente["ia"]
    fecha = (date.today() - timedelta(days=1)).isoformat()
    fila = {
        "sesiones_ga4": None, "usuarios_ga4": None, "vistas_ga4": None,
        "clics_gsc": None, "impresiones_gsc": None, "posicion_media_gsc": None,
        "suscriptores_totales": None, "suscriptores_netos_dia": None,
        "suscriptores_organicos": None, "suscriptores_meta": None,
        "suscriptores_directos": None,
        "tasa_apertura_ultimo_envio": None,
    }
    fuentes_ok = []

    try:
        # GA4 sin propiedad no es un fallo, es una decisión pendiente: hoy
        # ningún subdominio lleva la etiqueta y `ga4_property` está a null en
        # los 4. Sin este corte, cada ejecución escupía 4 trazas de error 400
        # idénticas y el log de un proceso sano parecía el de uno roto.
        if not agente.get("ga4_property"):
            raise RuntimeError("sin ga4_property en config.json (GA4 no montado todavía)")
        creds = credenciales(cfg["google_service_account"])
        ga4 = datos_ga4(creds, agente["ga4_property"])
        fila.update(sesiones_ga4=ga4["sesiones"], usuarios_ga4=ga4["usuarios"], vistas_ga4=ga4["vistas"])
        fuentes_ok.append("ga4")
    except Exception as e:
        print(f"[{ia}] GA4 no disponible: {e}", file=sys.stderr)

    try:
        creds = credenciales(cfg["google_service_account"])
        gsc = datos_gsc(creds, agente["gsc_site"])
        fila.update(clics_gsc=gsc["clics"], impresiones_gsc=gsc["impresiones"], posicion_media_gsc=gsc["posicion_media"])
        fuentes_ok.append("gsc")
        try:
            registrar_indexacion(conn, ia, creds, agente["gsc_site"])
        except Exception as e:
            # Va en su propio try: que falle el seguimiento de indexación no
            # debe costarle al agente su snapshot de métricas del día.
            print(f"[{ia}] seguimiento de indexación no disponible: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[{ia}] GSC no disponible: {e}", file=sys.stderr)

    try:
        lm = datos_listmonk(cfg["listmonk_base_url"], cfg["listmonk_api_token"], agente["listmonk_list_id"])
        fila.update(lm)
        fuentes_ok.append("listmonk")
    except Exception as e:
        print(f"[{ia}] Listmonk no disponible: {e}", file=sys.stderr)

    if not fuentes_ok:
        return False

    # Netos del día = variación real frente al último snapshot, no un contador
    # de altas: así las bajas restan, que es justo lo que pide el criterio de
    # victoria ("altas menos bajas", no volumen bruto).
    if fila["suscriptores_totales"] is not None:
        previo = conn.execute(
            "SELECT suscriptores_totales FROM metrics_snapshot "
            "WHERE ia = ? AND fecha < ? AND suscriptores_totales IS NOT NULL "
            "ORDER BY fecha DESC LIMIT 1",
            (ia, fecha),
        ).fetchone()
        if previo is not None:
            fila["suscriptores_netos_dia"] = fila["suscriptores_totales"] - previo["suscriptores_totales"]

    ya_tenia_subs = conn.execute(
        "SELECT 1 FROM metrics_snapshot WHERE ia = ? AND suscriptores_totales > 0 LIMIT 1", (ia,)
    ).fetchone() is not None
    if not ya_tenia_subs and (fila["suscriptores_totales"] or 0) > 0:
        _avisar(f"🎉 AI SEO Battle: {ia} consiguió su primer suscriptor ({fila['suscriptores_totales']} total)")

    conn.execute(
        """
        INSERT INTO metrics_snapshot
            (ia, fecha, sesiones_ga4, usuarios_ga4, vistas_ga4, clics_gsc, impresiones_gsc,
             posicion_media_gsc, suscriptores_totales, suscriptores_netos_dia,
             suscriptores_organicos, suscriptores_meta, suscriptores_directos,
             tasa_apertura_ultimo_envio, fuente, ingested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ia, fecha) DO UPDATE SET
            sesiones_ga4=excluded.sesiones_ga4, usuarios_ga4=excluded.usuarios_ga4,
            vistas_ga4=excluded.vistas_ga4, clics_gsc=excluded.clics_gsc,
            impresiones_gsc=excluded.impresiones_gsc, posicion_media_gsc=excluded.posicion_media_gsc,
            suscriptores_totales=excluded.suscriptores_totales,
            suscriptores_netos_dia=excluded.suscriptores_netos_dia,
            suscriptores_organicos=excluded.suscriptores_organicos,
            suscriptores_meta=excluded.suscriptores_meta,
            suscriptores_directos=excluded.suscriptores_directos,
            tasa_apertura_ultimo_envio=excluded.tasa_apertura_ultimo_envio,
            fuente=excluded.fuente, ingested_at=excluded.ingested_at
        """,
        (
            ia, fecha, fila["sesiones_ga4"], fila["usuarios_ga4"], fila["vistas_ga4"],
            fila["clics_gsc"], fila["impresiones_gsc"], fila["posicion_media_gsc"],
            fila["suscriptores_totales"], fila["suscriptores_netos_dia"],
            fila["suscriptores_organicos"], fila["suscriptores_meta"], fila["suscriptores_directos"],
            fila["tasa_apertura_ultimo_envio"], "+".join(fuentes_ok),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    return True


def main():
    # Este proceso avisaba dos veces por ejecución —"arranca" y "terminado"—
    # y eso son ~730 mensajes al año de un trabajo que casi siempre sale bien.
    # Un canal donde la mayoría de los mensajes no piden nada es un canal que
    # se deja de leer, y entonces el que sí importa (una fuente caída, el
    # primer suscriptor) se pierde entre los que no. Ahora habla solo cuando
    # hay algo que decir: fallo, o alguna IA sin ninguna fuente. Todo bien es
    # silencio, y el resumen sigue en el log y en stdout.
    silencioso = "--silencioso" in sys.argv
    def avisar(texto):
        if not silencioso:
            _avisar(texto)
    try:
        init_db()
        cfg = cargar_config()
        conn = get_conn()
        ok = sum(poll_ia(conn, cfg, agente) for agente in cfg["agentes"])
        conn.commit()
        conn.close()
    except Exception as e:
        avisar(f"🔴 AI SEO Battle: poller de métricas FALLÓ — {e}")
        raise
    total = len(cfg["agentes"])
    resumen = f"metrics snapshot: {ok}/{total} IAs con al menos una fuente"
    print(resumen)
    if ok < total:
        avisar(f"⚠️ AI SEO Battle: {total - ok} de {total} IAs se han quedado hoy "
               f"sin ninguna fuente de métricas — {resumen}")


if __name__ == "__main__":
    main()
