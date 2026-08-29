"""Búsqueda web para los agentes, con el cortafuegos de la fase 1.

El requisito de la fase ciega es que las 4 IAs no se vean **entre ellas**, no
que estén ciegas del mundo: lo que se mide es criterio de SEO, no memoria de
entrenamiento. Sin búsqueda, un agente que necesita un volumen de búsqueda se
lo inventa de memoria — justo el tipo de dato que no debe alucinarse en un
experimento cuya conclusión depende de él.

Así que tienen búsqueda desde el día 1, pasada por un filtro que descarta
resultados del propio experimento. **La lista de bloqueo no son solo los 4
subdominios**: la página del proyecto en tato9689.com y el dashboard público
listan a los 4 competidores con nombre y enlace, así que una búsqueda podría
exponerlos unos a otros sin que ninguna IA hiciera nada raro.

En fase 2 el filtro se levanta entero: a partir del checkpoint pueden
investigarse entre ellas, que es el punto de esa fase.

El proveedor de búsqueda se configura en `config.json` (`busqueda.proveedor`)
y su clave sale del entorno, nunca del disco. Si no hay clave, falla limpio
como el resto del sistema en vez de tumbar el turno del agente.
"""
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

BASE = Path(__file__).parent
CONFIG_PATH = BASE / "config.json"
TIMEOUT = 20

# Dominios propios del experimento que nunca deben llegar a un agente en fase
# 1. Se añaden a los subdominios derivados de config.json.
SIEMPRE_BLOQUEADOS = {
    "tato9689.com",  # la página del proyecto lista a los 4 competidores
}


def _raiz(host: str) -> str:
    return host.lower().removeprefix("www.")


def dominios_bloqueados(cfg: dict) -> set[str]:
    """Los 4 subdominios + el dominio raíz del experimento + el dashboard +
    la página del proyecto. Se deriva de config.json para que no haya dos
    listas que puedan desincronizarse."""
    bloqueados = set(SIEMPRE_BLOQUEADOS)
    for agente in cfg.get("agentes", []):
        url = agente.get("log_url") or ""
        host = _raiz(urlparse(url).hostname or "")
        if not host or "PENDIENTE" in host.upper():
            continue
        bloqueados.add(host)
        # El dominio raíz también: si un subdominio es claude.ejemplo.com,
        # ejemplo.com sirve el dashboard y enlaza a los cuatro.
        partes = host.split(".")
        if len(partes) > 2:
            bloqueados.add(".".join(partes[-2:]))
    for clave in ("dashboard_url", "listmonk_base_url"):
        host = _raiz(urlparse(cfg.get(clave) or "").hostname or "")
        if host and "PENDIENTE" not in host.upper():
            bloqueados.add(host)
    return bloqueados


def _es_del_experimento(url: str, bloqueados: set[str]) -> bool:
    host = _raiz(urlparse(url).hostname or "")
    if not host:
        return False
    # Coincide el host exacto o cualquier subdominio suyo.
    return any(host == b or host.endswith("." + b) for b in bloqueados)


def _buscar_brave(consulta: str, n: int) -> list[dict]:
    clave = os.environ.get("BRAVE_SEARCH_API_KEY")
    if not clave:
        raise RuntimeError("sin BRAVE_SEARCH_API_KEY configurada")
    resp = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": consulta, "count": n, "country": "es", "search_lang": "es"},
        headers={"X-Subscription-Token": clave, "Accept": "application/json"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return [
        {"titulo": r.get("title", ""), "url": r.get("url", ""), "extracto": r.get("description", "")}
        for r in resp.json().get("web", {}).get("results", [])
    ]


PROVEEDORES = {"brave": _buscar_brave}


def buscar(consulta: str, fase: int = 1, n: int = 8, cfg: dict | None = None) -> dict:
    """Devuelve {'resultados': [...], 'descartados': N, 'fase': N}.

    `descartados` se informa a propósito: el agente debe saber que hubo
    resultados filtrados aunque no vea cuáles, en vez de creer que la web
    entera no habla del tema. Ocultarle que existe un filtro sería mentirle
    sobre su propio contexto.
    """
    if cfg is None:
        with open(CONFIG_PATH, encoding="utf-8") as fh:
            cfg = json.load(fh)

    proveedor = (cfg.get("busqueda") or {}).get("proveedor", "brave")
    fn = PROVEEDORES.get(proveedor)
    if fn is None:
        return {"resultados": [], "descartados": 0, "fase": fase,
                "error": f"proveedor de búsqueda desconocido: {proveedor!r}"}

    try:
        # Se piden de más porque el filtro va a tirar algunos.
        brutos = fn(consulta, n + 5 if fase == 1 else n)
    except Exception as e:
        print(f"búsqueda no disponible: {e}", file=sys.stderr)
        return {"resultados": [], "descartados": 0, "fase": fase, "error": str(e)}

    if fase >= 2:
        # Fase 2: el bloqueo se levanta entero, investigarse es el punto.
        return {"resultados": brutos[:n], "descartados": 0, "fase": fase}

    bloqueados = dominios_bloqueados(cfg)
    limpios = [r for r in brutos if not _es_del_experimento(r["url"], bloqueados)]
    return {
        "resultados": limpios[:n],
        "descartados": len(brutos) - len(limpios),
        "fase": fase,
    }


if __name__ == "__main__":
    consulta = " ".join(sys.argv[1:]) or "rutinas de fuerza para principiantes"
    print(json.dumps(buscar(consulta), ensure_ascii=False, indent=2))
