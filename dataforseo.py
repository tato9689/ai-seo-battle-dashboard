"""Volumen de búsqueda y dificultad de keyword real, vía DataForSEO.

Pedido real de Gemini en la auditoría de herramientas del 2026-08-30:
autocompletado y Trends dan DIRECCIÓN (hacia dónde se mueve el interés),
no ESCALA (cuánta gente busca esto de verdad). Sin volumen absoluto, un
agente puede gastar una pieza entera en una keyword con 0 búsquedas reales
o en una con 50.000 dominada por gigantes.

Reutiliza la cuenta de DataForSEO que Tato ya tiene activa para su trabajo
real (agencia/SEO), en `/root/.config/dataforseo/credentials.json` — NO es
una cuenta nueva para el experimento. Por eso lleva un tope de llamadas
propio y conservador aparte del `tope_mensual_eur` de cada agente (que
solo cuenta gasto de modelo, no de esta API): un experimento autónomo sin
supervisión diaria no debe poder consumir sin límite una cuenta que Tato
usa para clientes de verdad.

Simétrico: las 4 IAs comparten el mismo tope total (no uno cada una) para
no cuadruplicar el consumo de una cuenta compartida — a diferencia de
`tope_mensual_eur`, que sí es por agente porque cada uno tiene su propia
cuenta de modelo.
"""
import json
import sys
from datetime import date
from pathlib import Path

import httpx

BASE = Path(__file__).parent
CREDENCIALES_PATH = Path("/root/.config/dataforseo/credentials.json")
USO_PATH = BASE / "cache" / "dataforseo_uso.json"
TIMEOUT = 20

# Tope compartido, conservador a propósito: ~60 consultas/mes de sobra para
# un turno diario por agente (30 días x 4 agentes = 120 turnos, ni todos
# piden esto ni cada turno lo necesita). A los precios reales de DataForSEO
# (documentados por Gemini, ~0.001-0.05 $/petición) el tope completo cuesta
# céntimos, pero el número de llamadas es el freno, no el gasto — es la
# cuenta de producción de Tato, el freno debe notarse antes de que la
# factura lo haga.
TOPE_LLAMADAS_MES = 200
# Subido de 60 a 200 el 2026-10-05: desde ese día consultar el volumen antes
# de escribir es OBLIGATORIO (base_comun, "OBJETIVO ÚNICO"), y 4 agentes al
# día pidiendo una vez son ~240 llamadas/mes (cada consulta = 2 llamadas).
# A ~0,05-0,09 $ por consulta completa, el tope entero ronda los 9 $/mes.
AVISO_SIN_SALDO_PATH = BASE / "cache" / "dataforseo_sin_saldo.txt"


def _credenciales() -> tuple[str, str] | None:
    if not CREDENCIALES_PATH.exists():
        return None
    try:
        d = json.loads(CREDENCIALES_PATH.read_text(encoding="utf-8"))
        return d["login"], d["password"]
    except (json.JSONDecodeError, OSError, KeyError):
        return None


def _uso_actual() -> dict:
    mes = date.today().strftime("%Y-%m")
    if USO_PATH.exists():
        try:
            d = json.loads(USO_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            d = {}
    else:
        d = {}
    if d.get("mes") != mes:
        d = {"mes": mes, "llamadas": 0}
    return d


def _registrar_llamada():
    d = _uso_actual()
    d["llamadas"] = d.get("llamadas", 0) + 1
    USO_PATH.parent.mkdir(exist_ok=True)
    USO_PATH.write_text(json.dumps(d), encoding="utf-8")


class SinSaldo(Exception):
    """402 de DataForSEO: la cuenta (la de trabajo de Tato) está a cero."""


MENSAJE_SIN_SALDO = (
    "la cuenta de DataForSEO se ha quedado sin saldo (HTTP 402). No es el tope "
    "compartido ni un fallo tuyo: Tato tiene que recargarla. Mientras tanto no "
    "tienes volumen real; decide con autocompletado, Trends y tus datos de "
    "Search Console, y vuelve a pedir el volumen en el turno siguiente."
)


def _avisar_sin_saldo():
    """Telegram a Tato, una vez al día como mucho. Durante semanas este 402
    se tragó en silencio: las IAs recibían un error que leían como "se acabó
    el tope" y nadie se enteró de que la cuenta estaba a cero."""
    hoy = date.today().isoformat()
    try:
        if AVISO_SIN_SALDO_PATH.exists() and AVISO_SIN_SALDO_PATH.read_text().strip() == hoy:
            return
        import avisos
        avisos.enviar("🔴 DataForSEO sin saldo (402): las IAs de retoseo.com se quedan sin "
                      "volumen de búsqueda, y tu MCP de DataForSEO tampoco funcionará. Recarga la cuenta.")
        AVISO_SIN_SALDO_PATH.parent.mkdir(exist_ok=True)
        AVISO_SIN_SALDO_PATH.write_text(hoy)
    except Exception as e:
        print(f"No se pudo avisar por Telegram del 402 de DataForSEO: {e}", file=sys.stderr)


def _post(endpoint: str, keywords: list[str], creds: tuple[str, str]) -> dict:
    resp = httpx.post(
        f"https://api.dataforseo.com/v3/{endpoint}",
        auth=creds,
        json=[{"keywords": keywords, "location_code": 2724, "language_code": "es"}],
        timeout=TIMEOUT,
    )
    if resp.status_code == 402:
        raise SinSaldo()
    resp.raise_for_status()
    _registrar_llamada()
    return resp.json()


def volumen_y_dificultad(keywords: list[str]) -> dict:
    """Hasta 5 keywords por llamada. Devuelve {keyword: {volumen_mensual,
    competencia, dificultad}} o {'error': ...} si no hay tope de llamadas,
    no hay credenciales, o falla la API — nunca tumba el turno, igual que
    busqueda.py/imagenes.py.

    Dos llamadas reales a DataForSEO por invocación (volumen + dificultad,
    endpoints distintos) — cuentan las dos contra `TOPE_LLAMADAS_MES`.
    """
    keywords = [k.strip() for k in keywords if k and k.strip()][:5]
    if not keywords:
        return {}

    uso = _uso_actual()
    if uso.get("llamadas", 0) + 2 > TOPE_LLAMADAS_MES:
        return {"error": f"tope compartido de {TOPE_LLAMADAS_MES} llamadas/mes a DataForSEO alcanzado"}

    creds = _credenciales()
    if creds is None:
        return {"error": "sin credenciales de DataForSEO configuradas"}

    resultado = {kw: {"volumen_mensual": None, "competencia": None, "dificultad": None} for kw in keywords}

    try:
        cuerpo = _post("keywords_data/google_ads/search_volume/live", keywords, creds)
        for tarea in cuerpo.get("tasks", []):
            for item in (tarea.get("result") or []):
                kw = item.get("keyword")
                if kw in resultado:
                    resultado[kw]["volumen_mensual"] = item.get("search_volume")
                    # LOW/MEDIUM/HIGH de pujas de Google Ads, no es "dificultad SEO" real.
                    resultado[kw]["competencia"] = item.get("competition")
    except SinSaldo:
        print("DataForSEO (volumen) no disponible: sin saldo (402)", file=sys.stderr)
        _avisar_sin_saldo()
        return {"error": MENSAJE_SIN_SALDO}
    except Exception as e:
        print(f"DataForSEO (volumen) no disponible: {e}", file=sys.stderr)
        return {"error": str(e)}

    try:
        cuerpo = _post("dataforseo_labs/google/bulk_keyword_difficulty/live", keywords, creds)
        for tarea in cuerpo.get("tasks", []):
            for bloque in (tarea.get("result") or []):
                for item in (bloque.get("items") or []):
                    kw = item.get("keyword")
                    if kw in resultado:
                        resultado[kw]["dificultad"] = item.get("keyword_difficulty")
    except SinSaldo:
        print("DataForSEO (dificultad) no disponible: sin saldo (402)", file=sys.stderr)
        _avisar_sin_saldo()
    except Exception as e:
        # El volumen ya se cobró y ya sirve por sí solo; no tirar el resultado
        # entero por un segundo endpoint que falla.
        print(f"DataForSEO (dificultad) no disponible: {e}", file=sys.stderr)

    return resultado


if __name__ == "__main__":
    print(json.dumps(volumen_y_dificultad(sys.argv[1:] or ["warping petg"]), indent=2, ensure_ascii=False))
