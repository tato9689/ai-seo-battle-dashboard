"""Señales de demanda gratuitas para los agentes: autocompletado de Google y
Google Trends.

Van pegadas a las búsquedas que el agente ya pide (`consultas_siguiente_turno`)
en vez de estrenar un campo nuevo en su JSON de salida. Dos motivos: no hay que
tocar el contrato de salida que las cuatro ya conocen, y sobre todo el reparto
queda simétrico por construcción — nadie puede pedir más señal que otro, porque
nadie las pide: se entregan solas con cada consulta.

Ninguna de las dos fuentes cuesta dinero ni necesita clave, y las dos son
ajenas a las cuatro casas del experimento. Si fallan, fallan limpio: el turno
sigue con lo que haya. Quedarse sin una señal es mucho mejor que quedarse sin
turno.
"""
import sys

import httpx

TIMEOUT = 15


def sugerencias(consulta: str, n: int = 10) -> list[str]:
    """Lo que Google autocompleta para esa consulta.

    Es demanda real declarada por gente real, no una estimación: son las
    continuaciones que Google ha visto teclear de verdad. Para long-tail en
    español vale más que cualquier estimador de volumen.
    """
    try:
        resp = httpx.get(
            "https://suggestqueries.google.com/complete/search",
            params={"client": "firefox", "hl": "es", "gl": "es", "q": consulta},
            timeout=TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()
        return [s for s in resp.json()[1][:n] if isinstance(s, str)]
    except Exception as e:
        print(f"autocompletado no disponible: {e}", file=sys.stderr)
        return []


def tendencia(termino: str, periodo: str = "today 3-m") -> dict:
    """Interés relativo en Google Trends (España, 3 meses) y si sube o baja.

    Trends no da volumen absoluto, da un índice 0-100 relativo a su propio
    máximo. Se informa así, con su nombre, para que el agente no lo confunda
    con búsquedas mensuales y publique una cifra inventada.
    """
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="es-ES", tz=0)
        pt.build_payload([termino], timeframe=periodo, geo="ES")
        df = pt.interest_over_time()
        if df is None or df.empty or termino not in df:
            return {"disponible": False, "motivo": "sin datos para ese término en España"}
        serie = [int(v) for v in df[termino].tolist()]
        mitad = len(serie) // 2 or 1
        prim, seg = sum(serie[:mitad]) / mitad, sum(serie[mitad:]) / max(len(serie) - mitad, 1)
        if seg > prim * 1.15:
            direccion = "subiendo"
        elif seg < prim * 0.85:
            direccion = "bajando"
        else:
            direccion = "estable"
        return {
            "disponible": True,
            "indice_medio_0_100": round(sum(serie) / len(serie), 1),
            "maximo_0_100": max(serie),
            "direccion_ultimos_meses": direccion,
            "_nota": "índice relativo de Google Trends (0-100), NO búsquedas mensuales",
        }
    except Exception as e:
        print(f"trends no disponible: {e}", file=sys.stderr)
        return {"disponible": False, "motivo": str(e)[:120]}
