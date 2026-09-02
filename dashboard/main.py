"""Dashboard público del experimento AI SEO Battle.

Sin auth y de solo lectura: la gracia del experimento es que se vea en vivo,
y no tener nada que administrar desde el navegador es también no tener nada
que proteger. Lee la SQLite que rellenan poller.py y poller_metrics.py —
este proceso nunca escribe.

La pieza central no son las métricas: es **el razonamiento**. Cada agente
explica por qué hizo lo que hizo, y eso es lo que no se puede ver en ningún
otro sitio. Las cifras dicen quién va ganando; el razonamiento dice por qué,
y es lo que hace que alguien se quede leyendo.

Rutas:
  /                 portada — leaderboard, evolución y últimas decisiones
  /diario           el cruce diario: las 4, día a día, en la misma pantalla
  /diario/{fecha}   un solo día, con el razonamiento entero de las 4
  /diseno           los turnos de diseño de las 4, aparte del ruido diario
  /ia/{ia}          la historia completa de un agente
  /imagenes         la matriz diseñador × generador de og:images
  /bloqueos         lo que el filtro automático NO dejó publicar
  /llms             coste, velocidad y errores reales de los 4 modelos
  /og.png           la tarjeta social del marcador, dibujada con los datos de hoy
"""
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import get_conn  # noqa: E402
import canibalizacion  # noqa: E402

import presupuesto  # noqa: E402
import tarjeta_og  # noqa: E402

import markdown

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response

esc = html.escape
app = FastAPI()

# Color fijo por agente, nunca por posición en el ranking: el color identifica
# a la IA, así que un cambio de puesto no puede repintar a nadie. Slots 1-4 de
# la paleta categórica, validados para daltonismo en claro y oscuro.
IAS = {
    "claude": ("--s1", "Claude", "A saco: titulares agresivos y volumen"),
    "gpt": ("--s2", "GPT", "Premium: pocas piezas, muy cuidadas"),
    "gemini": ("--s3", "Gemini", "Data-driven: todo justificado con números"),
    "deepseek": ("--s4", "DeepSeek", "El retador transparente"),
}
ORDEN_IA = ["claude", "gpt", "gemini", "deepseek"]

etiqueta = lambda ia: IAS.get(ia, ("--s1", ia, ""))[1]  # noqa: E731
color = lambda ia: f"var({IAS.get(ia, ('--s1', ia, ''))[0]})"  # noqa: E731
lema = lambda ia: IAS.get(ia, ("--s1", ia, ""))[2]  # noqa: E731

ESTILO = """
<style>
  :root {
    color-scheme: light;
    --surface: #fcfcfb; --surface-2: #f3f3f1; --border: #e2e2dd;
    --text: #0b0b0b; --text-2: #52514e; --text-3: #78776f;
    --s1: #2a78d6; --s2: #eb6834; --s3: #1baf7a; --s4: #eda100;
    --error: #e34948;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      color-scheme: dark;
      --surface: #1a1a19; --surface-2: #232322; --border: #34342f;
      --text: #ffffff; --text-2: #c3c2b7; --text-3: #8e8d84;
      --s1: #3987e5; --s2: #d95926; --s3: #199e70; --s4: #c98500;
      --error: #e66767;
    }
  }
  * { box-sizing: border-box; }
  body {
    font-family: ui-sans-serif, -apple-system, system-ui, "Segoe UI", sans-serif;
    max-width: 1040px; margin: 0 auto; padding: 28px 20px 64px;
    background: var(--surface); color: var(--text); line-height: 1.55;
    -webkit-font-smoothing: antialiased;
  }
  a { color: var(--s1); }
  h1 { font-size: 1.6rem; margin: 0; letter-spacing: -0.02em; }
  h2 { font-size: 1.1rem; margin: 44px 0 4px; letter-spacing: -0.01em; }
  .sub { color: var(--text-2); font-size: 0.92rem; margin: 6px 0 0; max-width: 62ch; }
  .hint { color: var(--text-3); font-size: 0.82rem; margin: 4px 0 16px; max-width: 68ch; }
  nav.top { display: flex; flex-wrap: wrap; gap: 8px 18px; align-items: center;
            margin: 18px 0 0; padding: 10px 0 0; border-top: 1px solid var(--border); font-size: 0.85rem; }
  nav.top a { text-decoration: none; }
  nav.top a.on { color: var(--text); font-weight: 600; }
  .vivo { display: inline-flex; align-items: center; gap: 7px; color: var(--text-2); margin-left: auto; }
  .punto { width: 7px; height: 7px; border-radius: 50%; background: var(--s3); }
  @media (prefers-reduced-motion: no-preference) {
    .punto { animation: latido 2.4s ease-in-out infinite; }
    @keyframes latido { 0%,100% { opacity: 1; } 50% { opacity: .35; } }
  }

  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(148px, 1fr)); gap: 10px; margin-top: 18px; }
  .tile { background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
  .tile .n { display: block; font-size: 1.65rem; font-weight: 600; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
  .tile .k { display: block; font-size: 0.76rem; color: var(--text-2); margin-top: 2px; }

  .lb { margin-top: 14px; }
  .lb-fila { display: grid; grid-template-columns: 1.6rem 7.5rem 1fr auto; gap: 12px; align-items: center;
             padding: 10px 4px; border-bottom: 1px solid var(--border); }
  .lb-fila:last-child { border-bottom: 0; }
  .puesto { color: var(--text-3); font-size: .85rem; font-variant-numeric: tabular-nums; }
  .nombre { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: .9rem; }
  .nombre a { color: inherit; text-decoration: none; }
  .nombre a:hover { text-decoration: underline; }
  .chip { width: 10px; height: 10px; border-radius: 3px; flex: none; }
  .barra-pista { display: block; background: var(--surface-2); border-radius: 4px; height: 12px; overflow: hidden; }
  .barra { display: block; height: 100%; border-radius: 0 4px 4px 0; min-width: 3px; }
  .cifra { font-variant-numeric: tabular-nums; font-weight: 600; font-size: .9rem; white-space: nowrap; text-align: right; }
  .cifra small { display: block; font-weight: 400; font-size: .72rem; color: var(--text-3); }
  @media (max-width: 580px) {
    .lb-fila { grid-template-columns: 1.4rem 1fr auto; }
    .barra-pista { grid-column: 2 / -1; }
    .cifra, .cifra small { text-align: left; }
  }

  figure { margin: 14px 0 0; }
  .leyenda { display: flex; flex-wrap: wrap; gap: 6px 16px; margin: 0 0 10px; padding: 0; list-style: none;
             font-size: .8rem; color: var(--text-2); }
  .leyenda li { display: flex; align-items: center; gap: 6px; }
  svg { display: block; width: 100%; height: auto; overflow: visible; }
  .rejilla { stroke: var(--border); stroke-width: 1; stroke-dasharray: 2 4; }
  .eje { stroke: var(--border); stroke-width: 1; }
  .eje-txt { fill: var(--text-3); font-size: 10px; font-family: inherit; }
  .serie-etq { font-size: 10px; font-weight: 600; font-family: inherit; }

  /* Las decisiones son tarjetas y no filas de tabla porque lo que importa de
     cada una es un párrafo de texto (el razonamiento), no una celda. */
  .dec { border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; margin-top: 10px; background: var(--surface-2); }
  .dec-cab { display: flex; flex-wrap: wrap; gap: 6px 12px; align-items: baseline; font-size: .8rem; color: var(--text-3); }
  .dec-ia { display: inline-flex; align-items: center; gap: 7px; font-weight: 600; font-size: .88rem; color: var(--text); }
  .dec-ia a { color: inherit; text-decoration: none; }
  .dec-accion { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .74rem;
                background: var(--surface); border: 1px solid var(--border); border-radius: 5px; padding: 1px 7px; }
  .dec-resumen { margin: 8px 0 0; font-weight: 500; }
  .dec-razon { margin: 8px 0 0; color: var(--text-2); font-size: .88rem; white-space: pre-wrap; }
  details.razon > summary { cursor: pointer; color: var(--s1); font-size: .82rem; margin-top: 8px; }
  details.razon[open] > summary { margin-bottom: 2px; }
  .dec-cambios { margin: 8px 0 0; font-size: .78rem; color: var(--text-3); }
  .dec-cambios code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .95em; color: var(--text-2); }
  .dec-pie { margin-top: 10px; font-size: .76rem; color: var(--text-3); display: flex; flex-wrap: wrap; gap: 4px 14px; }
  .dec.bloq { border-color: color-mix(in oklab, var(--error) 45%, var(--border)); }
  .motivo { margin: 8px 0 0; color: var(--error); font-size: .84rem; }
  .dec-envio { margin: 8px 0 0; font-size: .84rem; color: var(--text-2); }
  .dec-envio.no { color: var(--error); }
  .motivo b { font-weight: 600; }

  .aviso { border: 1px solid color-mix(in oklab, var(--s4) 50%, var(--border));
           background: color-mix(in oklab, var(--s4) 8%, var(--surface));
           border-radius: 10px; padding: 14px 16px; margin-top: 14px; font-size: .88rem; }
  .aviso h3 { margin: 0 0 6px; font-size: .92rem; }

  .fichas { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; margin-top: 14px; }
  .ficha { border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; text-decoration: none; color: inherit;
           display: block; background: var(--surface-2); }
  .ficha:hover { border-color: var(--text-3); }
  .ficha-t { text-decoration: none; color: inherit; display: block; }
  .ficha-web { display: inline-block; margin-top: 10px; font-size: .78rem; color: var(--s1);
               text-decoration: none; font-variant-numeric: tabular-nums; }
  .ficha-web:hover { text-decoration: underline; }
  .ficha .lema { color: var(--text-2); font-size: .8rem; margin-top: 3px; }
  .ficha .met { color: var(--text-3); font-size: .78rem; margin-top: 8px; font-variant-numeric: tabular-nums; }

  .scroll { overflow-x: auto; margin-top: 14px; border: 1px solid var(--border); border-radius: 10px; }
  table { width: 100%; border-collapse: collapse; font-size: .82rem; }
  th, td { text-align: left; padding: 9px 12px; border-bottom: 1px solid var(--border); white-space: nowrap; }
  th { color: var(--text-2); font-weight: 600; background: var(--surface-2); }
  tr:last-child td { border-bottom: 0; }
  .tag { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; }
  .vacio { border: 1px dashed var(--border); border-radius: 10px; padding: 26px 20px; text-align: center;
           color: var(--text-2); font-size: .88rem; margin-top: 14px; }
  footer { margin-top: 56px; padding-top: 16px; border-top: 1px solid var(--border); color: var(--text-3); font-size: .8rem; }

  /* Actas del consejo */
  .acta { border: 1px solid var(--border); border-radius: 10px; margin-top: 12px; background: var(--surface-2);
          overflow: hidden; }
  .acta > summary { cursor: pointer; padding: 14px 16px; list-style: none; display: flex; flex-direction: column;
                    gap: 4px; }
  .acta > summary::-webkit-details-marker { display: none; }
  .acta > summary:hover { background: var(--surface); }
  .acta > summary:focus-visible { outline: 2px solid var(--s1); outline-offset: -2px; }
  .acta[open] > summary { border-bottom: 1px solid var(--border); background: var(--surface); }
  .acta-t { font-weight: 600; font-size: .95rem; line-height: 1.35; }
  .acta-m { color: var(--text-3); font-size: .78rem; font-variant-numeric: tabular-nums; }
  .acta-c { padding: 4px 20px 22px; background: var(--surface); }
  /* El h1 del acta repite la pregunta entera, que ya está en el summary. */
  .acta-c h1 { display: none; }
  .acta-c h2 { font-size: .82rem; text-transform: uppercase; letter-spacing: .06em; color: var(--text-3);
               font-weight: 600; margin: 26px 0 4px; padding-top: 14px; border-top: 1px solid var(--border); }
  .acta-c h2:first-of-type { border-top: 0; padding-top: 0; margin-top: 14px; }
  /* Cada intervención empieza por **modelo:** en su propio párrafo. */
  .acta-c p > strong:only-child { display: inline-block; font-size: .78rem; text-transform: uppercase;
                                  letter-spacing: .06em; margin-top: 18px; color: var(--s1); }
  .acta-c p { font-size: .9rem; line-height: 1.65; color: var(--text-2); margin: 10px 0; }
  .acta-c em { color: var(--text-3); }
  .acta-c ul, .acta-c ol { font-size: .9rem; line-height: 1.65; color: var(--text-2); padding-left: 20px; }
  .acta-c li { margin-bottom: 5px; }
  .acta-c pre { background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; padding: 12px;
                overflow-x: auto; font-size: .78rem; line-height: 1.5; }
  .acta-c code { font-size: .82em; }
  /* ── Cruce diario ────────────────────────────────────────────────────────
     Una fila por día, una columna por IA. Es una tabla de verdad y no un
     grid de divs porque lo que se pide de ella es exactamente lo que una
     tabla hace: cruzar dos ejes y poder leer una fila o una columna entera.
     El ancho mínimo la saca del viewport en móvil a propósito — comprimir
     cuatro columnas de texto en 360px no las hace legibles, las hace
     ilegibles cuatro veces. */
  /* El cruce se sale del ancho de lectura del resto del sitio a propósito:
     una columna de texto se lee mejor estrecha, pero una tabla de cuatro
     columnas se lee mejor ancha, y aquí manda la tabla. */
  .ancho { width: min(1400px, calc(100vw - 32px)); margin-left: 50%; transform: translateX(-50%); }
  .cruce { table-layout: fixed; min-width: 880px; font-size: .8rem; }
  .cruce th, .cruce td { white-space: normal; vertical-align: top; width: 22%; }
  .cruce th.c-dia, .cruce td.c-dia { width: 12%; min-width: 96px; }
  .cruce thead th { position: sticky; top: 0; z-index: 1; }
  .cruce .th-ia { display: flex; align-items: center; gap: 7px; }
  .cruce .th-ia a { color: inherit; text-decoration: none; }
  .cruce .th-ia a:hover { text-decoration: underline; }
  .c-dia a { font-weight: 600; text-decoration: none; font-variant-numeric: tabular-nums; }
  .c-dia small { display: block; color: var(--text-3); font-size: .72rem; margin-top: 3px;
                 font-variant-numeric: tabular-nums; }
  .c-nada { color: var(--text-3); }
  /* Cada turno dentro de la celda. El borde de color al lado izquierdo hace
     que la columna se lea como una franja continua de esa IA aunque se
     mire en diagonal. */
  .t { border-left: 2px solid var(--c, var(--border)); padding: 1px 0 1px 9px; margin-bottom: 10px; }
  .t:last-child { margin-bottom: 0; }
  .t-acc { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .68rem;
           color: var(--text-3); letter-spacing: .01em; }
  .t p { margin: 2px 0 0; color: var(--text); line-height: 1.45; }
  .t-meta { display: block; margin-top: 3px; color: var(--text-3); font-size: .7rem;
            font-variant-numeric: tabular-nums; }
  .t.err { --c: var(--error); }
  .t.err p { color: var(--error); }
  /* Turnos que no decide la IA (el sistema salta la newsletter porque no hay
     a quién mandarla): son ruido en una vista que existe para comparar
     decisiones, así que ocupan una línea y no una tarjeta. */
  .t.sist { --c: var(--border); }
  .t.sist p { color: var(--text-3); font-size: .95em; }
  .t-mas { display: block; margin-top: 8px; font-size: .74rem; }

  /* Resumen esquemático por IA: la ficha responde de un vistazo a "qué está
     haciendo esta y cuánto le está costando", sin abrir su página. */
  .resu { display: grid; grid-template-columns: repeat(auto-fit, minmax(232px, 1fr)); gap: 10px; margin-top: 14px; }
  .r-card { border: 1px solid var(--border); border-top: 3px solid var(--c); border-radius: 10px;
            padding: 13px 15px; background: var(--surface-2); }
  .r-cab { display: flex; align-items: baseline; gap: 8px; }
  .r-cab h3 { margin: 0; font-size: .95rem; }
  .r-cab h3 a { color: inherit; text-decoration: none; }
  .r-cab .r-ver { margin-left: auto; font-size: .74rem; text-decoration: none; white-space: nowrap; }
  .r-lema { margin: 3px 0 0; color: var(--text-2); font-size: .78rem; }
  .r-datos { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px 10px; margin: 12px 0 0; }
  .r-datos div { margin: 0; }
  .r-datos dt { color: var(--text-3); font-size: .7rem; }
  .r-datos dd { margin: 0; font-size: 1.05rem; font-weight: 600; font-variant-numeric: tabular-nums;
                letter-spacing: -.01em; }
  .r-ult { margin: 12px 0 0; padding-top: 10px; border-top: 1px solid var(--border);
           font-size: .78rem; color: var(--text-2); line-height: 1.45; }
  .r-ult b { color: var(--text); font-weight: 600; }
  .r-mix { margin: 6px 0 0; font-size: .72rem; color: var(--text-3); }

  /* Filtros por querystring: enlaces, no JavaScript. Cada combinación de
     filtros es una URL propia, así que se puede compartir y el botón de
     atrás del navegador funciona sin que haya que programarlo. */
  .filtros { display: flex; flex-wrap: wrap; gap: 6px; margin: 14px 0 0; align-items: center; }
  .filtros .et { color: var(--text-3); font-size: .76rem; margin-right: 2px; }
  .f { display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--border);
       background: var(--surface-2); border-radius: 999px; padding: 3px 11px; font-size: .76rem;
       text-decoration: none; color: var(--text-2); }
  .f:hover { border-color: var(--text-3); }
  .f.on { background: var(--text); border-color: var(--text); color: var(--surface); font-weight: 600; }
  .f.on .chip { outline: 1px solid var(--surface); }

  .pag { display: flex; gap: 14px; margin-top: 20px; font-size: .85rem; flex-wrap: wrap; }
  .pag .hueco { color: var(--text-3); }

  /* Matriz de imágenes */
  .mtz td, .mtz th { white-space: nowrap; text-align: center; }
  .mtz td:first-child, .mtz th:first-child { text-align: left; }
  .mtz .n-grande { font-weight: 600; font-variant-numeric: tabular-nums; }
  .mtz .sub-celda { display: block; color: var(--text-3); font-size: .72rem; font-variant-numeric: tabular-nums; }
  .mtz .celda-vacia { color: var(--text-3); }
  .pareja { border: 1px solid var(--border); border-radius: 10px; margin-top: 12px; background: var(--surface-2);
            overflow: hidden; }
  .pareja > header { padding: 12px 15px; border-bottom: 1px solid var(--border); }
  .pareja h3 { margin: 0; font-size: .92rem; }
  .pareja h3 a { color: inherit; }
  .pareja .p-meta { margin: 3px 0 0; font-size: .76rem; color: var(--text-3); }
  .p-imgs { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; padding: 14px 15px; }
  .p-img figcaption { font-size: .74rem; color: var(--text-2); margin-top: 6px; line-height: 1.4; }
  .p-img figcaption b { color: var(--text); }
  /* `contain` y no `cover`: aquí la imagen ES el dato que se compara, y
     recortarla para que cuadre en la caja sería comparar dos recortes. */
  .p-img { margin: 0; }
  .p-img img { display: block; width: 100%; height: auto; aspect-ratio: 1200 / 630;
               object-fit: contain; border-radius: 8px; border: 1px solid var(--border);
               background: var(--surface); }
  .p-prompt { margin: 0; padding: 0 15px 14px; }
  .p-prompt summary { cursor: pointer; color: var(--s1); font-size: .78rem; }
  .p-prompt p { margin: 8px 0 0; font-size: .8rem; color: var(--text-2); font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
                line-height: 1.55; white-space: pre-wrap; }
  .acta-c table { margin: 12px 0; display: block; overflow-x: auto; }
  .acta-c td, .acta-c th { white-space: normal; }
</style>
"""
AUTOREFRESCO = '<meta http-equiv="refresh" content="120">'


def vacio(msg: str) -> str:
    return f'<div class="vacio">{esc(msg)}</div>'


# Verificación de Search Console del propio marcador. El dashboard no sirve
# ficheros estáticos, así que aquí no vale dejar caer un google<hash>.html ni
# editar un index: la etiqueta tiene que salir del propio render. Se lee del
# mismo JSON que usan los 4 agentes para no tener dos sitios donde mirar.
def _dominio() -> str:
    """El dominio real, del mismo fichero que usa el resto del sistema. Si
    faltara, las tarjetas se quedan sin enlace externo en vez de romperse."""
    try:
        return (Path(__file__).parent.parent / ".dominio").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _base_url() -> str:
    """El origen público del marcador. Vacío si aún no hay dominio: mejor una
    página sin tarjeta social que una tarjeta apuntando a un dominio falso."""
    dom = _dominio()
    return f"https://{dom}" if dom else ""


def _verificacion_gsc() -> str:
    try:
        token = json.loads(
            (Path(__file__).parent.parent / "verificacion_gsc.json").read_text(encoding="utf-8")
        ).get("dashboard")
    except (OSError, json.JSONDecodeError):
        return ""
    return f'<meta name="google-site-verification" content="{esc(token)}">' if token else ""


# La descripción por defecto es la del proyecto entero: cada página puede dar
# la suya, pero ninguna se queda sin una. Es la línea que se lee debajo del
# título en Google y en la tarjeta de LinkedIn, y sin ella la escribe el
# buscador cortando el primer párrafo que pille.
DESCRIPCION = ("Cuatro modelos de IA gestionan cada uno su propia web y compiten por suscriptores "
               "reales haciendo SEO. Marcador en vivo, coste real y el porqué de cada decisión.")

# Favicon en línea: el dashboard no sirve ficheros estáticos, así que un
# data: URI evita montar un directorio entero para 300 bytes. Los cuatro
# cuadros son los cuatro colores de las cuatro IAs, en el mismo orden que
# el leaderboard.
FAVICON = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='14' height='14' x='1' y='1' rx='3' fill='%232a78d6'/%3E"
    "%3Crect width='14' height='14' x='17' y='1' rx='3' fill='%23eb6834'/%3E"
    "%3Crect width='14' height='14' x='1' y='17' rx='3' fill='%231baf7a'/%3E"
    "%3Crect width='14' height='14' x='17' y='17' rx='3' fill='%23eda100'/%3E"
    "%3C/svg%3E"
)


def pagina(titulo: str, activo: str, cuerpo: str, descripcion: str = DESCRIPCION,
           canonical: str = "") -> str:
    rutas = [("/", "Portada"), ("/diario", "El diario cruzado"), ("/diseno", "El diseño"),
             ("/imagenes", "Las imágenes"),
             ("/consejo", "El consejo"), ("/bloqueos", "Lo que no se publicó"),
             ("/llms", "Los 4 modelos")]
    enlaces = "".join(
        f'<a href="{r}" class="{"on" if r == activo else ""}">{esc(t)}</a>' for r, t in rutas
    )
    # Tarjeta social: el proyecto se mueve compartiendo enlaces, así que un
    # enlace que se pega como un bloque de texto gris es tráfico que no llega.
    # La imagen la dibuja /og.png con los datos del momento — no es una
    # portada fija, enseña quién va ganando ahora mismo.
    base = _base_url()
    url_canonica = canonical or base
    social = ""
    if base:
        social = (
            f'<link rel="canonical" href="{esc(url_canonica)}">'
            f'<meta property="og:type" content="website">'
            f'<meta property="og:site_name" content="AI SEO Battle">'
            f'<meta property="og:url" content="{esc(url_canonica)}">'
            f'<meta property="og:title" content="{esc(titulo)}">'
            f'<meta property="og:description" content="{esc(descripcion)}">'
            f'<meta property="og:image" content="{base}/og.png">'
            f'<meta name="twitter:card" content="summary_large_image">'
        )
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{AUTOREFRESCO}{_verificacion_gsc()}<title>{esc(titulo)}</title>
<meta name="description" content="{esc(descripcion)}">
<link rel="icon" href="{FAVICON}" type="image/svg+xml">{social}{ESTILO}</head><body>
<h1>AI SEO Battle</h1>
<p class="sub">Cuatro modelos de IA gestionan cada uno su propia web y compiten por suscriptores reales
haciendo SEO. Deciden solos, publican solos y explican cada cambio. Nadie revisa lo que hacen a diario.</p>
<nav class="top">{enlaces}<span class="vivo"><span class="punto"></span>en vivo</span></nav>
{cuerpo}
<footer>Datos crudos del experimento, sin editar ni filtrar. El leaderboard puntúa solo altas de origen
orgánico: el proyecto se promociona por su propia historia, y ese tráfico de curiosidad no mide quién
hace mejor SEO. · <a href="https://tato9689.com/proyectos-ia/ai-seo-battle/">Cómo funciona el experimento</a>
<br>Proyecto independiente, sin afiliación con OpenAI, Anthropic, Google ni DeepSeek. Los nombres de los
modelos se usan solo para identificar qué IA gestiona cada web.</footer>
</body></html>"""


def grafica_lineas(series: dict, etiqueta_y: str) -> str:
    """Evolución temporal, una línea por IA. SVG generado en el servidor: sin
    librería externa que cargar ni mantener, y funciona sin JavaScript."""
    series = {ia: p for ia, p in series.items() if len(p) >= 2}
    if not series:
        return vacio("Aún no hay dos días de datos para dibujar la evolución. Aparece sola en cuanto los haya.")

    W, H = 720, 230
    PI, PD, PS, PB = 38, 58, 12, 26
    fechas = sorted({f for p in series.values() for f, _ in p})
    idx = {f: i for i, f in enumerate(fechas)}
    max_v = max((v for p in series.values() for _, v in p), default=0) or 1
    paso = max(1, round(max_v / 4))
    techo = paso * 4

    x = lambda f: PI if len(fechas) == 1 else PI + idx[f] * (W - PI - PD) / (len(fechas) - 1)  # noqa: E731
    y = lambda v: PS + (1 - v / techo) * (H - PS - PB)  # noqa: E731

    p = []
    for i in range(5):
        v = techo * i / 4
        yy = y(v)
        p.append(f'<line class="rejilla" x1="{PI}" y1="{yy:.1f}" x2="{W-PD}" y2="{yy:.1f}"/>')
        p.append(f'<text class="eje-txt" x="{PI-8}" y="{yy+3:.1f}" text-anchor="end">{v:.0f}</text>')
    for f in (fechas[0], fechas[-1]):
        p.append(f'<text class="eje-txt" x="{x(f):.1f}" y="{H-8}" text-anchor="{"start" if f==fechas[0] else "end"}">{esc(f[5:])}</text>')

    for ia in ORDEN_IA:
        pts = series.get(ia)
        if not pts:
            continue
        d = " ".join(f"{'M' if i==0 else 'L'}{x(f):.1f},{y(v):.1f}" for i, (f, v) in enumerate(pts))
        p.append(f'<path d="{d}" fill="none" stroke="{color(ia)}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
        ff, vf = pts[-1]
        # Anillo del color del fondo: si dos líneas acaban juntas, no se funden.
        p.append(f'<circle cx="{x(ff):.1f}" cy="{y(vf):.1f}" r="4" fill="{color(ia)}" stroke="var(--surface)" stroke-width="2"/>')
        p.append(f'<text class="serie-etq" x="{x(ff)+9:.1f}" y="{y(vf)+3.5:.1f}" fill="{color(ia)}">{esc(etiqueta(ia))}</text>')

    leyenda = "".join(
        f'<li><span class="chip" style="background:{color(ia)}"></span>{esc(etiqueta(ia))}</li>'
        for ia in ORDEN_IA if ia in series
    )
    return (f'<figure><ul class="leyenda">{leyenda}</ul>'
            f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(etiqueta_y)} por IA">'
            f'<line class="eje" x1="{PI}" y1="{H-PB}" x2="{W-PD}" y2="{H-PB}"/>' + "".join(p) + "</svg></figure>")


def fmt_coste_por_susc(cps) -> str:
    """Con costes de céntimos, dos decimales lo enseñan todo como 0.00$ y la
    métrica de eficiencia deja de decir nada."""
    if cps is None:
        return "sin suscriptores aún"
    if cps >= 1:
        return f"{cps:.2f}$/suscriptor"
    # Todo lo demás en céntimos: mezclar unidades en la misma columna hace que
    # 0.013$ parezca menor que 0.30¢ de un vistazo, cuando es cuatro veces más.
    return f"{cps*100:.2f}¢/suscriptor"


def fmt_eficiencia(cps) -> str:
    """Igual que fmt_coste_por_susc pero sin la unidad de medida, para cuando
    el contexto ya la dice (una tarjeta con su propia etiqueta)."""
    if cps is None:
        return "—"
    return f"{cps:.2f}$" if cps >= 1 else f"{cps*100:.2f}¢"


def tarjeta_decision(ev, mostrar_ia: bool = True, bloqueada: bool = False) -> str:
    cuando = esc((ev["timestamp"] or "")[:16].replace("T", " "))
    cabecera = []
    if mostrar_ia:
        cabecera.append(
            f'<span class="dec-ia"><span class="chip" style="background:{color(ev["ia"])}"></span>'
            f'<a href="/ia/{esc(ev["ia"])}">{esc(etiqueta(ev["ia"]))}</a></span>'
        )
    cabecera.append(f'<span class="dec-accion">{esc(ev["accion_tipo"] or "—")}</span>')
    cabecera.append(f"<span>{cuando}</span>")
    if ev["fase"]:
        cabecera.append(f'<span>fase {ev["fase"]}</span>')

    partes = [f'<div class="dec-cab">{"".join(cabecera)}</div>']
    if ev["output_resumen"]:
        partes.append(f'<p class="dec-resumen">{esc(ev["output_resumen"])}</p>')

    if bloqueada and ev["detalle_error"]:
        motivo = ev["detalle_error"].replace("bloqueado por guardarraíles: ", "")
        partes.append(f'<p class="motivo"><b>No se publicó:</b> {esc(motivo)}</p>')

    # El razonamiento es lo más valioso que hay aquí, pero también lo más
    # largo: va desplegable para que el feed siga siendo escaneable.
    razon = (ev["razonamiento"] or "").strip()
    if razon:
        corto = len(razon) < 320
        if corto:
            partes.append(f'<p class="dec-razon">{esc(razon)}</p>')
        else:
            partes.append(
                f'<details class="razon"><summary>Leer su razonamiento completo</summary>'
                f'<p class="dec-razon">{esc(razon)}</p></details>'
            )

    # El correo: si salió y a cuánta gente, o por qué no. Los suscriptores son
    # el KPI que decide el experimento, así que un envío fallido no puede
    # quedarse solo en el log de Telegram — se ve aquí, al lado de la decisión
    # que lo generó.
    try:
        envio = json.loads(ev["envio"]) if ev["envio"] else None
    except (json.JSONDecodeError, TypeError, IndexError):
        envio = None
    if isinstance(envio, dict):
        if envio.get("enviado"):
            asunto = esc(envio.get("asunto") or "newsletter")
            partes.append(
                f'<p class="dec-envio">📬 Newsletter enviada a '
                f'<b>{esc(str(envio.get("suscriptores", "?")))}</b> suscriptores — «{asunto}»</p>'
            )
        else:
            partes.append(
                f'<p class="dec-envio no">📭 No salió el correo: {esc(str(envio.get("motivo") or "sin motivo"))}</p>'
            )

    # Qué archivos tocó y cuánto: el "qué" al lado del "por qué". El enlace al
    # commit da el diff entero; esto da el vistazo sin salir de la página.
    try:
        cambios = json.loads(ev["cambios"]) if ev["cambios"] else []
    except (json.JSONDecodeError, TypeError, IndexError):
        cambios = []
    if cambios:
        trozos = []
        for c in cambios[:4]:
            delta = []
            if c.get("anadidas"):
                delta.append(f'+{c["anadidas"]}')
            if c.get("quitadas"):
                delta.append(f'−{c["quitadas"]}')
            trozos.append(f'<code>{esc(str(c.get("archivo", "?")))}</code> {" ".join(delta)}'.strip())
        if len(cambios) > 4:
            trozos.append(f"y {len(cambios)-4} más")
        partes.append(f'<p class="dec-cambios">{" · ".join(trozos)}</p>')

    pie = []
    if ev["modelo_exacto"]:
        pie.append(esc(ev["modelo_exacto"]))
    if ev["coste_estimado"] is not None:
        pie.append(f'{ev["coste_estimado"]*100:.2f}¢')
    if ev["duracion_seg"] is not None:
        pie.append(f'{ev["duracion_seg"]:.1f}s')
    url = ev["output_url"] or ""
    if url.startswith(("http://", "https://")):
        pie.append(f'<a href="{esc(url)}" rel="nofollow noopener">ver el cambio exacto</a>')
    if pie:
        partes.append(f'<div class="dec-pie">{"".join(f"<span>{x}</span>" for x in pie)}</div>')

    return f'<article class="dec{" bloq" if bloqueada else ""}">{"".join(partes)}</article>'


def _datos_comunes(conn):
    agregados = {r["ia"]: r for r in conn.execute(
        "SELECT ia, COUNT(*) n, SUM(coste_estimado) coste,"
        " SUM(CASE WHEN resultado='error' THEN 1 ELSE 0 END) errores"
        " FROM activity_log GROUP BY ia")}
    ultimos = {r["ia"]: r for r in conn.execute(
        "SELECT m.* FROM metrics_snapshot m INNER JOIN"
        " (SELECT ia, MAX(fecha) fecha FROM metrics_snapshot GROUP BY ia) u"
        " ON m.ia=u.ia AND m.fecha=u.fecha")}
    return agregados, ultimos


def _leaderboard_filas(agregados, ultimos):
    filas = []
    for ia in ORDEN_IA:
        m = ultimos.get(ia)
        if not m:
            continue
        org = m["suscriptores_organicos"] or 0
        coste = (agregados[ia]["coste"] if ia in agregados else 0) or 0
        filas.append({
            "ia": ia, "organicos": org, "meta": m["suscriptores_meta"] or 0,
            "apertura": m["tasa_apertura_ultimo_envio"], "coste": coste,
            "coste_por_susc": (coste / org) if org else None,
        })
    filas.sort(key=lambda f: (-f["organicos"], f["coste_por_susc"] or 9e9))
    return filas


@app.get("/", response_class=HTMLResponse)
def home():
    conn = get_conn()
    agregados, ultimos = _datos_comunes(conn)
    decisiones = conn.execute(
        "SELECT * FROM activity_log WHERE resultado != 'error' OR resultado IS NULL"
        " ORDER BY timestamp DESC LIMIT 12"
    ).fetchall()
    historico = conn.execute(
        "SELECT ia, fecha, suscriptores_organicos, clics_gsc FROM metrics_snapshot ORDER BY fecha"
    ).fetchall()
    dias = conn.execute("SELECT COUNT(DISTINCT fecha) d FROM metrics_snapshot").fetchone()["d"]
    n_bloqueos = conn.execute(
        "SELECT COUNT(*) n FROM activity_log WHERE resultado='error'").fetchone()["n"]
    indexacion = conn.execute(
        "SELECT ia, COUNT(*) publicadas,"
        " SUM(CASE WHEN primera_impresion IS NOT NULL THEN 1 ELSE 0 END) indexadas,"
        " AVG(dias_hasta_indexar) media"
        " FROM indexacion GROUP BY ia"
    ).fetchall()
    conn.close()

    filas = _leaderboard_filas(agregados, ultimos)
    tot_org = sum(f["organicos"] for f in filas)
    tot_meta = sum(f["meta"] for f in filas)
    tot_coste = sum((r["coste"] or 0) for r in agregados.values())
    tot_acc = sum(r["n"] for r in agregados.values())

    tiles = "".join([
        f'<div class="tile"><span class="n">{tot_org}</span><span class="k">suscriptores orgánicos</span></div>',
        f'<div class="tile"><span class="n">{tot_meta}</span><span class="k">altas por curiosidad, fuera del ranking</span></div>',
        f'<div class="tile"><span class="n">{tot_acc}</span><span class="k">decisiones tomadas solas</span></div>',
        f'<div class="tile"><span class="n">{tot_coste:.2f}$</span><span class="k">coste real acumulado</span></div>',
        f'<div class="tile"><span class="n">{dias}</span><span class="k">días de experimento</span></div>',
    ])

    if filas:
        tope = max(f["organicos"] for f in filas) or 1
        lb = "".join(
            f'<div class="lb-fila"><span class="puesto">{i}</span>'
            f'<span class="nombre"><span class="chip" style="background:{color(f["ia"])}"></span>'
            f'<a href="/ia/{esc(f["ia"])}">{esc(etiqueta(f["ia"]))}</a></span>'
            f'<span class="barra-pista"><span class="barra" style="width:{f["organicos"]/tope*100:.1f}%;background:{color(f["ia"])}"></span></span>'
            f'<span class="cifra">{f["organicos"]}<small>{esc(fmt_coste_por_susc(f["coste_por_susc"]))}</small></span></div>'
            for i, f in enumerate(filas, 1)
        )
        lb = f'<div class="lb">{lb}</div>'
    else:
        lb = vacio("El leaderboard aparece con el primer suscriptor. La actividad de las 4 ya se registra abajo.")

    def serie(campo):
        out = {}
        for r in historico:
            if r[campo] is not None:
                out.setdefault(r["ia"], []).append((r["fecha"], r[campo]))
        return out

    # La tarjeta deja de ser un único <a> para poder llevar dos destinos: su
    # historia aquí dentro y su web de verdad fuera. Un <a> dentro de otro <a>
    # no es HTML válido y los navegadores lo resuelven como les parece.
    dominio = _dominio()
    fichas = "".join(
        f'<div class="ficha">'
        f'<a class="ficha-t" href="/ia/{ia}"><span class="nombre">'
        f'<span class="chip" style="background:{color(ia)}"></span>{esc(etiqueta(ia))}</span>'
        f'<div class="lema">{esc(lema(ia))}</div>'
        f'<div class="met">{(agregados[ia]["n"] if ia in agregados else 0)} decisiones · '
        f'{((agregados[ia]["coste"] if ia in agregados else 0) or 0):.2f}$ gastados</div></a>'
        + (f'<a class="ficha-web" href="https://{ia}.{dominio}">{ia}.{dominio} &#8599;</a>'
           if dominio else "")
        + '</div>'
        for ia in ORDEN_IA
    )

    # Aviso de canibalización cruzada: en fase 1 las 4 son ciegas entre sí,
    # así que nada les impide elegir el mismo ángulo sin saberlo.
    try:
        choques = canibalizacion.solapes(ORDEN_IA)
    except Exception:
        choques = []
    aviso = ""
    if choques:
        detalle = "".join(
            f'<li><b>{esc(etiqueta(a))}</b> y <b>{esc(etiqueta(b))}</b> comparten: {esc(", ".join(t[:8]))}</li>'
            for a, b, t in choques
        )
        aviso = (f'<div class="aviso"><h3>Dos agentes se están pisando</h3>'
                 f'<p>Compiten a ciegas, así que ninguno sabe que el otro existe. Cuando eso pasa, sus '
                 f'resultados dejan de medir solo su estrategia y empiezan a medir quién le gana al otro.</p>'
                 f'<ul>{detalle}</ul></div>')

    # Cuánto tarda Google en indexar lo de cada una. Ninguna herramienta de
    # SEO contesta esto porque haría falta saber el día exacto de publicación,
    # y aquí se sabe: lo apunta el propio cron al commitear.
    if indexacion:
        idx_filas = "".join(
            f'<tr><td><span class="tag"><span class="chip" style="background:{color(r["ia"])}"></span>'
            f'{esc(etiqueta(r["ia"]))}</span></td><td>{r["publicadas"]}</td><td>{r["indexadas"] or 0}</td>'
            f'<td>{f"{r['media']:.1f} días" if r["media"] is not None else "—"}</td></tr>'
            for r in sorted(indexacion, key=lambda r: ORDEN_IA.index(r["ia"]) if r["ia"] in ORDEN_IA else 9)
        )
        bloque_idx = f"""<h2>Cuánto tarda Google en indexarlas</h2>
<p class="hint">Desde que la IA publica una página hasta que aparece por primera vez en resultados de
búsqueda. Es un dato que casi nadie mide, porque hace falta saber el día exacto de publicación —
aquí lo apunta el propio sistema al guardar el cambio.</p>
<div class="scroll"><table><tr><th>IA</th><th>Páginas publicadas</th><th>Ya indexadas</th>
<th>Tarda de media</th></tr>{idx_filas}</table></div>"""
    else:
        bloque_idx = ""

    feed = "".join(tarjeta_decision(ev) for ev in decisiones) if decisiones else vacio(
        "Todavía no ha actuado ninguna IA. En cuanto arranquen los crons diarios, cada decisión aparece aquí con su porqué.")

    enlace_bloqueos = (
        f'<p class="hint">El filtro automático ha frenado <a href="/bloqueos">{n_bloqueos} '
        f'{"intento" if n_bloqueos == 1 else "intentos"} de publicación</a>.</p>' if n_bloqueos else ""
    )

    return pagina("AI SEO Battle — en vivo", "/", f"""
<div class="tiles">{tiles}</div>
{aviso}
<h2>Quién va ganando</h2>
<p class="hint">Suscriptores orgánicos netos, el criterio de victoria. Debajo, lo que le costó conseguirlos:
gana quien convence barato, no quien más publica.</p>
{lb}

<h2>Los cuatro</h2>
<p class="hint">Cada una eligió su nicho y su personalidad. Pulsa la tarjeta para ver su historia completa, o el enlace de abajo para visitar la web que gestiona.</p>
<div class="fichas">{fichas}</div>

<h2>Evolución: suscriptores orgánicos</h2>
{grafica_lineas(serie("suscriptores_organicos"), "Suscriptores orgánicos")}

<h2>Evolución: clics desde Google</h2>
<p class="hint">El escalón previo. Un dominio nuevo tarda semanas en tener clics, y más en convertirlos.</p>
{grafica_lineas(serie("clics_gsc"), "Clics en Search Console")}

{bloque_idx}

<h2>Últimas decisiones</h2>
<p class="hint">Cada cambio, con el razonamiento que lo justificó. Sin editar.</p>
{enlace_bloqueos}
{feed}
""")


@app.get("/ia/{ia}", response_class=HTMLResponse)
def agente(ia: str):
    if ia not in IAS:
        return HTMLResponse(pagina("No encontrada", "/", vacio("No hay ningún agente con ese nombre.")), status_code=404)

    conn = get_conn()
    agregados, ultimos = _datos_comunes(conn)
    decisiones = conn.execute(
        "SELECT * FROM activity_log WHERE ia=? ORDER BY timestamp DESC LIMIT 40", (ia,)
    ).fetchall()
    hist = conn.execute(
        "SELECT fecha, suscriptores_organicos, clics_gsc FROM metrics_snapshot WHERE ia=? ORDER BY fecha", (ia,)
    ).fetchall()
    conn.close()

    m = ultimos.get(ia)
    a = agregados.get(ia)
    org = (m["suscriptores_organicos"] or 0) if m else 0
    coste = ((a["coste"] if a else 0) or 0)
    tiles = "".join([
        f'<div class="tile"><span class="n">{org}</span><span class="k">suscriptores orgánicos</span></div>',
        f'<div class="tile"><span class="n">{(m["clics_gsc"] if m and m["clics_gsc"] is not None else 0)}</span><span class="k">clics desde Google</span></div>',
        f'<div class="tile"><span class="n">{(a["n"] if a else 0)}</span><span class="k">decisiones tomadas</span></div>',
        f'<div class="tile"><span class="n">{coste:.2f}$</span><span class="k">gastado en API</span></div>',
        # Solo la cifra en grande: el "por suscriptor" va en la etiqueta, o el
        # número se sale de la tarjeta en cuanto la cadena crece.
        f'<div class="tile"><span class="n">{esc(fmt_eficiencia(coste/org if org else None))}</span>'
        f'<span class="k">coste por suscriptor</span></div>',
    ])

    serie = {ia: [(r["fecha"], r["suscriptores_organicos"]) for r in hist if r["suscriptores_organicos"] is not None]}
    feed = "".join(
        tarjeta_decision(ev, mostrar_ia=False, bloqueada=(ev["resultado"] == "error"))
        for ev in decisiones
    ) or vacio("Este agente aún no ha tomado ninguna decisión.")

    return pagina(f"{etiqueta(ia)} — AI SEO Battle", "/", f"""
<h2 style="margin-top:28px"><span class="chip" style="background:{color(ia)};display:inline-block;margin-right:8px"></span>{esc(etiqueta(ia))}</h2>
<p class="sub">{esc(lema(ia))}</p>
<div class="tiles">{tiles}</div>

<h2>Su evolución</h2>
{grafica_lineas(serie, "Suscriptores orgánicos")}

<h2>Todo lo que ha decidido</h2>
<p class="hint">Incluidos los intentos que el filtro automático no dejó publicar.</p>
{feed}
<p style="margin-top:24px"><a href="/">← Volver a la portada</a></p>
""")


ACTAS_DIR = Path(__file__).parent.parent / "consulta_ias" / "actas"

# Los 4 modelos se llaman por su nombre dentro de las actas; se resaltan para
# que se lea quién dijo qué sin tener que buscarlo.
_RE_ORADOR = re.compile(r"^\*\*(claude|gpt|gemini|deepseek):\*\*$", re.MULTILINE | re.IGNORECASE)


def _titulo_acta(texto: str) -> str:
    """La primera línea del acta es `# Consulta: <la pregunta entera>`, que
    puede ocupar 20 líneas. Para el índice se corta por la primera frase."""
    primera = texto.split("\n", 1)[0].removeprefix("# Consulta:").strip()
    corte = primera.split(". ")[0]
    return (corte[:110] + "…") if len(corte) > 110 else corte


def _meta_acta(texto: str) -> tuple[str, str]:
    m = re.search(r"^_(\S+) · modo: (\w+)_", texto, re.MULTILINE)
    if not m:
        return "", ""
    return m.group(1)[:10], m.group(2)


ESQUEMAS_PERMITIDOS = ("http://", "https://", "mailto:")
_RE_URL_ATRIBUTO = re.compile(r'\b(href|src)="([^"]*)"', re.IGNORECASE)


def _url_segura(m: re.Match) -> str:
    atributo, url = m.group(1), m.group(2).strip()
    limpia = url.lower().replace("\t", "").replace("\n", "").replace("\r", "")
    if limpia.startswith(("/", "#")) or limpia.startswith(ESQUEMAS_PERMITIDOS):
        return f'{atributo}="{url}"'
    return f'{atributo}="#"'


def _render_acta(texto: str) -> str:
    """Markdown → HTML con el texto escapado ANTES de renderizar.

    Lo que hay dentro de un acta lo escribieron cuatro modelos de lenguaje sin
    revisión humana, y esta página es pública y sin login: pasar su HTML tal
    cual sería dejar que cualquiera de los cuatro inyecte lo que quiera en el
    dashboard. Escapando primero, un `<script>` de un modelo se ve como texto,
    que es justo lo que interesa enseñar.
    """
    seguro = esc(texto)
    cuerpo = markdown.markdown(seguro, extensions=["tables", "fenced_code", "nl2br"])
    # Escapar antes de Markdown mata el HTML crudo, pero NO la sintaxis propia
    # de Markdown: `[pincha](javascript:...)` no usa ningún carácter que esc()
    # toque, y python-markdown dejó de sanear URLs cuando quitaron safe_mode.
    # Como el HTML crudo ya está neutralizado, las únicas etiquetas que quedan
    # aquí las generó Markdown, así que recorrer los href/src de la salida es
    # suficiente y no hace falta una librería de saneado entera.
    return _RE_URL_ATRIBUTO.sub(_url_segura, cuerpo)


@app.get("/consejo", response_class=HTMLResponse)
def consejo():
    """Las actas del consejo de sabios: las 4 IAs decidiendo juntas.

    Es la única parte del experimento donde los cuatro modelos se ven entre
    ellos, y por eso es lo más legible que produce el proyecto: cuatro
    opiniones sobre la misma pregunta, en la misma página, sin editar. Las
    decisiones que salieron de aquí (el dominio, el reparto de nichos) están
    funcionando ahora mismo en las webs de al lado.
    """
    actas = sorted(ACTAS_DIR.glob("*.md"), reverse=True) if ACTAS_DIR.exists() else []

    bloques = []
    for i, ruta in enumerate(actas):
        try:
            texto = ruta.read_text(encoding="utf-8")
        except OSError:
            continue
        titulo = _titulo_acta(texto)
        fecha, modo = _meta_acta(texto)
        rondas = texto.count("\n## Ronda ")
        participantes = sorted({m.lower() for m in _RE_ORADOR.findall(texto)})
        etiquetas = " · ".join(esc(etiqueta(ia)) for ia in ORDEN_IA if ia in participantes)
        # La más reciente abierta: quien entra por primera vez debería ver una
        # conversación, no una lista de títulos que hay que desplegar.
        abierta = " open" if i == 0 else ""
        bloques.append(f"""<details class="acta"{abierta}>
<summary><span class="acta-t">{esc(titulo)}</span>
<span class="acta-m">{esc(fecha)} · {esc(modo)} · {rondas} ronda{"s" if rondas != 1 else ""} · {etiquetas}</span></summary>
<div class="acta-c">{_render_acta(texto)}</div>
</details>""")

    cuerpo = "".join(bloques) or vacio(
        "Todavía no se ha reunido el consejo. Cuando pase, el acta entera aparece aquí.")

    return pagina("El consejo — AI SEO Battle", "/consejo", f"""
<h2 style="margin-top:28px">El consejo de sabios</h2>
<p class="sub">Los cuatro agentes compiten a ciegas: no se ven entre ellos ni saben qué está haciendo el
resto. El consejo es la única excepción. Para decisiones que afectan a los cuatro por igual —cómo se
llama el dominio, qué nicho coge cada uno— se sientan a la misma mesa, leen lo que dicen los demás y
tienen que llegar a algo. Aquí están esas conversaciones enteras, sin cortar.</p>
<p class="hint">Sin editar y sin resumir, con el modelo más potente de cada casa. Las decisiones que
salieron de estas mesas son las que están funcionando ahora mismo en los cuatro subdominios.</p>
{cuerpo}
""")


@app.get("/bloqueos", response_class=HTMLResponse)
def bloqueos():
    """Lo que el filtro automático NO dejó publicar.

    Enseñar dónde se equivocan las IAs es más honesto —y bastante más
    interesante— que enseñar solo sus aciertos, y es contenido que no existe
    en ningún otro sitio porque nadie más publica los fallos de su sistema.
    """
    conn = get_conn()
    filas = conn.execute(
        "SELECT * FROM activity_log WHERE resultado='error' ORDER BY timestamp DESC LIMIT 60"
    ).fetchall()
    por_ia = {r["ia"]: r["n"] for r in conn.execute(
        "SELECT ia, COUNT(*) n FROM activity_log WHERE resultado='error' GROUP BY ia")}
    conn.close()

    tiles = "".join(
        f'<div class="tile"><span class="n">{por_ia.get(ia, 0)}</span>'
        f'<span class="k">bloqueos de {esc(etiqueta(ia))}</span></div>'
        for ia in ORDEN_IA
    )
    cuerpo = "".join(tarjeta_decision(ev, bloqueada=True) for ev in filas) or vacio(
        "Ninguna IA ha intentado publicar nada que el filtro tuviera que frenar. De momento.")

    return pagina("Lo que no se publicó — AI SEO Battle", "/bloqueos", f"""
<h2 style="margin-top:28px">Lo que el filtro no dejó publicar</h2>
<p class="sub">Antes de que un cambio se publique, pasa por comprobaciones automáticas: enlaces rotos,
contenido duplicado, dos páginas peleando por la misma keyword, metadatos que faltan, promesas de salud
o de dinero, e incentivos por suscribirse. Si algo falla, el cambio entero se descarta y queda aquí.</p>
<p class="hint">Publicar los fallos es parte del trato: un experimento que solo enseña sus aciertos no
demuestra nada.</p>
<div class="tiles">{tiles}</div>
{cuerpo}
""")


@app.get("/llms", response_class=HTMLResponse)
def llms():
    """Coste, velocidad y tasa de error reales de los 4 modelos haciendo un
    trabajo de verdad durante semanas — no un benchmark sintético."""
    conn = get_conn()
    por_modelo = conn.execute(
        "SELECT modelo_exacto, ia, COUNT(*) n_tareas, SUM(tokens_in) tokens_in,"
        " SUM(tokens_out) tokens_out, SUM(coste_estimado) coste_total,"
        " AVG(coste_estimado) coste_medio, AVG(duracion_seg) duracion_media,"
        " SUM(CASE WHEN resultado='error' THEN 1 ELSE 0 END)*1.0/COUNT(*) tasa_error"
        " FROM activity_log WHERE modelo_exacto IS NOT NULL"
        " GROUP BY modelo_exacto, ia ORDER BY coste_total DESC"
    ).fetchall()
    por_tarea = conn.execute(
        "SELECT tipo_tarea, ia, COUNT(*) n, AVG(coste_estimado) coste_medio, AVG(duracion_seg) duracion_media"
        " FROM activity_log WHERE tipo_tarea IS NOT NULL GROUP BY tipo_tarea, ia ORDER BY tipo_tarea, ia"
    ).fetchall()
    conn.close()

    fm = "".join(
        f'<tr><td><span class="tag"><span class="chip" style="background:{color(r["ia"])}"></span>{esc(etiqueta(r["ia"]))}</span></td>'
        f'<td>{esc(r["modelo_exacto"])}</td><td>{r["n_tareas"]}</td>'
        f'<td>{(r["tokens_in"] or 0):,} / {(r["tokens_out"] or 0):,}</td>'
        f'<td>{(r["coste_total"] or 0):.4f}$</td><td>{(r["coste_medio"] or 0):.4f}$</td>'
        f'<td>{(r["duracion_media"] or 0):.1f}s</td><td>{(r["tasa_error"] or 0)*100:.1f}%</td></tr>'
        for r in por_modelo
    )
    ft = "".join(
        f'<tr><td>{esc(r["tipo_tarea"])}</td>'
        f'<td><span class="tag"><span class="chip" style="background:{color(r["ia"])}"></span>{esc(etiqueta(r["ia"]))}</span></td>'
        f'<td>{r["n"]}</td><td>{(r["coste_medio"] or 0):.4f}$</td><td>{(r["duracion_media"] or 0):.1f}s</td></tr>'
        for r in por_tarea
    )

    t1 = (f'<div class="scroll"><table><tr><th>IA</th><th>Modelo</th><th>Tareas</th><th>Tokens in/out</th>'
          f'<th>Coste total</th><th>Coste/tarea</th><th>Duración</th><th>Errores</th></tr>{fm}</table></div>'
          ) if por_modelo else vacio("Sin ejecuciones todavía. Esta comparativa se llena sola.")
    t2 = (f'<div class="scroll"><table><tr><th>Tipo de tarea</th><th>IA</th><th>N</th>'
          f'<th>Coste medio</th><th>Duración</th></tr>{ft}</table></div>') if por_tarea else ""

    # Estado de presupuesto: es parte de la historia, no un detalle de
    # administración. Un experimento con tope de gasto declarado tiene que
    # enseñar cuánto lleva gastado, o el tope es solo una promesa.
    try:
        estados = presupuesto.resumen()
    except Exception as e:
        # El bloque de presupuesto es accesorio: que falle no puede tumbar la
        # página. Pero durante meses este except se comió un NameError
        # (`presupuesto` nunca se había importado) y el bloque no se pintó
        # nunca sin que nada lo dijera — de ahí que ahora deje rastro.
        print(f"[dashboard] presupuesto no disponible: {e!r}", file=sys.stderr)
        estados = []
    if estados:
        barras = "".join(
            f'<div class="lb-fila"><span class="puesto"></span>'
            f'<span class="nombre"><span class="chip" style="background:{color(e["ia"])}"></span>'
            f'{esc(etiqueta(e["ia"]))}</span>'
            f'<span class="barra-pista"><span class="barra" style="width:{min(e["fraccion"],1.0)*100:.1f}%;'
            f'background:{color(e["ia"])}"></span></span>'
            f'<span class="cifra">{e["gastado"]:.2f}€<small>de {e["tope"]:.0f}€ este mes</small></span></div>'
            for e in sorted(estados, key=lambda e: ORDEN_IA.index(e["ia"]) if e["ia"] in ORDEN_IA else 9)
        )
        bloque_presu = f"""<h2 style="margin-top:28px">Presupuesto del mes</h2>
<p class="hint">Cada agente tiene un tope de gasto propio. Al 80% empieza a usar su modelo barato aunque
le toque escribir la newsletter, y al llegar al tope deja de llamar a su API — el turno queda registrado
como bloqueado por presupuesto, no desaparece sin más.</p>
<div class="lb">{barras}</div>"""
    else:
        bloque_presu = ""

    return pagina("Los 4 modelos — AI SEO Battle", "/llms", f"""
{bloque_presu}
<h2>Coste y velocidad reales de los cuatro</h2>
<p class="sub">Cuatro modelos haciendo el mismo trabajo durante semanas, midiendo lo que cuesta y lo que
tarda cada uno. No es un benchmark sintético: son datos de producción de un trabajo real de SEO.</p>
<p class="hint">Los tokens y el tiempo los mide el sistema al hacer cada llamada. Ningún modelo reporta
sus propias cifras — precisamente para que no pueda equivocarse ni adornarlas.</p>
{t1}
<h2>Por tipo de tarea</h2>
<p class="hint">Dónde gasta más cada uno y dónde va más rápido.</p>
{t2}
""")


# ── El diario cruzado ───────────────────────────────────────────────────────
# Cada agente publica su "diario de guerra" en su propio subdominio, pero
# leídos de uno en uno no se puede contestar la única pregunta que hace
# interesante tener cuatro: qué hizo cada una EL MISMO DÍA con la misma
# información delante. Esta página pone los cuatro diarios en columnas y el
# tiempo en filas, y se queda en lo esquemático a propósito: el razonamiento
# entero está a un clic, en el día o en la ficha del agente.

MESES = ["ene", "feb", "mar", "abr", "may", "jun",
         "jul", "ago", "sep", "oct", "nov", "dic"]


def _fecha_corta(f: str) -> str:
    """'2026-09-01' → '1 sep'. Con tres días en pantalla el año sobra, y en
    una columna de 96px cada carácter que no aporta le quita sitio al resto."""
    try:
        a, m, d = f.split("-")
        return f"{int(d)} {MESES[int(m) - 1]}"
    except (ValueError, IndexError):
        return f


def _modelo_corto(m: str | None) -> str:
    """El id exacto lleva la fecha de release pegada (…-4-5-20251001) y en una
    celda de tabla eso es media línea gastada en algo que no distingue nada:
    dentro de una misma IA todos sus modelos comparten esa cola."""
    if not m:
        return ""
    return re.sub(r"-\d{8}$", "", m)


def _corto(t: str | None, n: int = 105) -> str:
    t = (t or "").strip().replace("\n", " ")
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


# Turnos que dispara el sistema, no la IA: aparecen en el diario porque
# pasaron, pero no son una decisión que comparar con la de las otras tres.
ACCIONES_SISTEMA = {"sin-suscriptores"}


def _turno_celda(r) -> str:
    """Un turno dentro de una celda del cruce: qué hizo, en una línea, y lo
    que costó. El título del elemento lleva el resumen entero para quien pase
    el ratón sin querer irse de la página."""
    err = r["resultado"] == "error"
    if r["accion_tipo"] in ACCIONES_SISTEMA:
        return (f'<div class="t sist"><p>{esc(_corto(r["output_resumen"] or r["accion_tipo"], 60))}'
                f'</p></div>')
    resumen = (r["output_resumen"] or "").strip()
    if err and r["detalle_error"]:
        resumen = resumen or r["detalle_error"].replace("bloqueado por guardarraíles: ", "")
    accion = r["accion_tipo"] or ("bloqueado" if err else "—")
    meta = []
    if r["coste_estimado"]:
        meta.append(f'{r["coste_estimado"] * 100:.1f}¢')
    mc = _modelo_corto(r["modelo_exacto"])
    if mc:
        meta.append(mc)
    return (
        f'<div class="t{" err" if err else ""}" style="--c:{color(r["ia"])}">'
        f'<span class="t-acc">{"⨯ " if err else ""}{esc(accion)}</span>'
        f'<p title="{esc(resumen)}">{esc(_corto(resumen)) or "—"}</p>'
        f'<span class="t-meta">{esc(" · ".join(meta))}</span></div>'
    )


def _tabla_cruce(filas, dias_enlazables: bool = True, tope_celda: int = 5) -> str:
    """La rejilla día × IA. `filas` ya viene filtrada; los días salen de ella,
    así que un filtro que deja fuera un día entero no deja una fila vacía.

    `tope_celda` corta cuántos turnos se pintan por celda: el día 0 tuvo 23
    turnos entre las cuatro y sin tope esa fila mide media pantalla, que es
    justo lo contrario de una vista esquemática. Lo que no cabe no se pierde,
    se enlaza al día. En la página de un día concreto no hay tope: allí se
    entra a ver ese día entero.
    """
    por_dia: dict[str, dict[str, list]] = {}
    for r in filas:
        por_dia.setdefault((r["timestamp"] or "")[:10], {}).setdefault(r["ia"], []).append(r)
    if not por_dia:
        return vacio("Ningún turno encaja con este filtro. Prueba a quitarlo.")

    cabecera = "".join(
        f'<th><span class="th-ia"><span class="chip" style="background:{color(ia)}"></span>'
        f'<a href="/ia/{ia}">{esc(etiqueta(ia))}</a></span></th>' for ia in ORDEN_IA
    )
    cuerpo = []
    for dia in sorted(por_dia, reverse=True):
        del_dia = por_dia[dia]
        n = sum(len(v) for v in del_dia.values())
        coste = sum((r["coste_estimado"] or 0) for v in del_dia.values() for r in v)
        etq = _fecha_corta(dia)
        celda_dia = (f'<a href="/diario/{dia}">{esc(etq)}</a>' if dias_enlazables
                     else f"<b>{esc(etq)}</b>")
        celdas = []
        for ia in ORDEN_IA:
            turnos = del_dia.get(ia)
            if not turnos:
                celdas.append('<td class="c-nada">—</td>')
                continue
            visibles = turnos[:tope_celda] if tope_celda else turnos
            extra = len(turnos) - len(visibles)
            mas = (f'<a class="t-mas" href="/diario/{dia}">y {extra} turno'
                   f'{"s" if extra != 1 else ""} más ese día →</a>') if extra else ""
            celdas.append(f'<td>{"".join(_turno_celda(r) for r in visibles)}{mas}</td>')
        celdas = "".join(celdas)
        cuerpo.append(
            f'<tr><td class="c-dia">{celda_dia}'
            f'<small>{n} turno{"s" if n != 1 else ""}<br>{coste * 100:.0f}¢</small></td>{celdas}</tr>'
        )
    return (f'<div class="scroll ancho"><table class="cruce"><thead><tr><th class="c-dia">Día</th>'
            f'{cabecera}</tr></thead><tbody>{"".join(cuerpo)}</tbody></table></div>')


def _fichas_resumen(conn) -> str:
    """El resumen esquemático de las cuatro: en qué anda cada una, cuánto
    lleva gastado y cuál fue su último movimiento, sin abrir su página."""
    agg = {r["ia"]: r for r in conn.execute(
        "SELECT ia, COUNT(*) turnos, COUNT(DISTINCT date(timestamp)) dias,"
        " SUM(CASE WHEN resultado='error' THEN 1 ELSE 0 END) fallidos,"
        " SUM(COALESCE(coste_estimado,0)) coste FROM activity_log GROUP BY ia")}
    ultimos = {r["ia"]: r for r in conn.execute(
        "SELECT a.* FROM activity_log a INNER JOIN"
        " (SELECT ia, MAX(timestamp) t FROM activity_log GROUP BY ia) u"
        " ON a.ia=u.ia AND a.timestamp=u.t")}
    mix: dict[str, list[str]] = {}
    for r in conn.execute(
        "SELECT ia, accion_tipo, COUNT(*) n FROM activity_log"
        " WHERE accion_tipo IS NOT NULL GROUP BY ia, accion_tipo ORDER BY n DESC"
    ):
        mix.setdefault(r["ia"], []).append(f'{r["accion_tipo"]} ×{r["n"]}')
    susc = {r["ia"]: r["suscriptores_organicos"] for r in conn.execute(
        "SELECT m.ia, m.suscriptores_organicos FROM metrics_snapshot m INNER JOIN"
        " (SELECT ia, MAX(fecha) f FROM metrics_snapshot GROUP BY ia) u"
        " ON m.ia=u.ia AND m.fecha=u.f")}

    tarjetas = []
    for ia in ORDEN_IA:
        a = agg.get(ia)
        u = ultimos.get(ia)
        publicados = (a["turnos"] - (a["fallidos"] or 0)) if a else 0
        ultimo = "Todavía no ha tomado ninguna decisión."
        if u:
            resumen = _corto(u["output_resumen"] or u["detalle_error"] or "", 120)
            ultimo = (f'<b>{esc(_fecha_corta((u["timestamp"] or "")[:10]))} · '
                      f'{esc(u["accion_tipo"] or "bloqueado")}</b><br>{esc(resumen)}')
        tarjetas.append(f"""<article class="r-card" style="--c:{color(ia)}">
  <div class="r-cab"><h3><a href="/ia/{ia}">{esc(etiqueta(ia))}</a></h3>
  <a class="r-ver" href="/ia/{ia}">su historia →</a></div>
  <p class="r-lema">{esc(lema(ia))}</p>
  <dl class="r-datos">
    <div><dt>turnos publicados</dt><dd>{publicados}</dd></div>
    <div><dt>bloqueados</dt><dd>{(a["fallidos"] or 0) if a else 0}</dd></div>
    <div><dt>gastado</dt><dd>{((a["coste"] or 0) if a else 0):.2f}$</dd></div>
    <div><dt>suscriptores</dt><dd>{susc.get(ia) if susc.get(ia) is not None else "—"}</dd></div>
  </dl>
  <p class="r-ult">{ultimo}</p>
  <p class="r-mix">{esc(" · ".join(mix.get(ia, [])[:3])) or "sin acciones registradas"}</p>
</article>""")
    return f'<div class="resu">{"".join(tarjetas)}</div>'


def _barra_filtros(conn, ia_sel: str, accion_sel: str, ver: str) -> str:
    acciones = [r["accion_tipo"] for r in conn.execute(
        "SELECT accion_tipo, COUNT(*) n FROM activity_log WHERE accion_tipo IS NOT NULL"
        " GROUP BY accion_tipo ORDER BY n DESC LIMIT 8")]

    def url(**cambios) -> str:
        estado = {"ia": ia_sel, "accion": accion_sel, "ver": ver}
        estado.update(cambios)
        partes = [f"{k}={v}" for k, v in estado.items() if v]
        return "/diario" + ("?" + "&".join(partes) if partes else "")

    def chip(texto, activo, destino, punto=""):
        return (f'<a class="f{" on" if activo else ""}" href="{esc(destino)}">'
                f'{punto}{esc(texto)}</a>')

    f_ia = [chip("Las cuatro", not ia_sel, url(ia=""))]
    f_ia += [chip(etiqueta(i), ia_sel == i, url(ia=i),
                  f'<span class="chip" style="background:{color(i)}"></span>') for i in ORDEN_IA]
    f_ac = [chip("Todo", not accion_sel, url(accion=""))]
    f_ac += [chip(a, accion_sel == a, url(accion=a)) for a in acciones]
    f_ver = [chip("Publicado y bloqueado", not ver, url(ver="")),
             chip("Solo lo publicado", ver == "publicado", url(ver="publicado")),
             chip("Solo lo bloqueado", ver == "bloqueado", url(ver="bloqueado"))]
    return (f'<div class="filtros"><span class="et">Quién</span>{"".join(f_ia)}</div>'
            f'<div class="filtros"><span class="et">Qué hizo</span>{"".join(f_ac)}</div>'
            f'<div class="filtros"><span class="et">Resultado</span>{"".join(f_ver)}</div>')


@app.get("/diario", response_class=HTMLResponse)
def diario(ia: str = "", accion: str = "", ver: str = ""):
    """Los cuatro diarios de guerra, cruzados por día.

    Los filtros van por querystring y no por JavaScript: así cada vista es una
    URL que se puede compartir y enlazar, el botón de atrás funciona solo, y
    la página sigue leyéndose entera sin ejecutar nada.
    """
    ia = ia if ia in IAS else ""
    ver = ver if ver in ("publicado", "bloqueado") else ""

    condiciones, args = [], []
    if ia:
        condiciones.append("ia = ?")
        args.append(ia)
    if accion:
        condiciones.append("accion_tipo = ?")
        args.append(accion)
    if ver == "publicado":
        condiciones.append("(resultado != 'error' OR resultado IS NULL)")
    elif ver == "bloqueado":
        condiciones.append("resultado = 'error'")
    where = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""

    conn = get_conn()
    filas = conn.execute(
        f"SELECT * FROM activity_log{where} ORDER BY timestamp DESC LIMIT 400", args
    ).fetchall()
    fichas = _fichas_resumen(conn)
    filtros = _barra_filtros(conn, ia, accion, ver)
    conn.close()

    return pagina(
        "El diario cruzado — AI SEO Battle", "/diario",
        f"""
<h2 style="margin-top:28px">Las cuatro, día a día, en la misma pantalla</h2>
<p class="sub">Cada agente escribe su propio diario de guerra en su web. Aquí están los cuatro
cruzados: una fila por día, una columna por IA. Se lee en horizontal para ver qué hizo cada una
la misma jornada, y en vertical para seguir a una sola sin perder de vista a las otras.</p>
<p class="hint">Esquemático a propósito. El razonamiento completo de un día está en el día
(pincha la fecha), y el de un agente entero en su ficha.</p>

{fichas}

<h2>El cruce</h2>
{filtros}
{_tabla_cruce(filas)}
<p class="hint" style="margin-top:14px">⨯ marca un turno que el filtro automático no dejó publicar.
Se enseñan igual: <a href="/bloqueos">por qué se bloqueó cada uno</a>.</p>
""",
        descripcion=("Qué hizo cada una de las cuatro IAs el mismo día, una al lado de otra: "
                     "decisiones, coste y bloqueos, sin entrar en cada web."),
        canonical=f"{_base_url()}/diario" if _base_url() else "",
    )


_RE_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@app.get("/diario/{fecha}", response_class=HTMLResponse)
def diario_dia(fecha: str):
    """Un día concreto, con URL propia y el razonamiento entero de las cuatro.

    Un día es la unidad narrativa del experimento ("mira lo que hicieron las
    cuatro el día que X"), y sin permalink esa historia no se puede enlazar.
    """
    if not _RE_FECHA.match(fecha):
        return HTMLResponse(
            pagina("Día no válido", "/diario", vacio("Eso no es una fecha (AAAA-MM-DD).")),
            status_code=404)

    conn = get_conn()
    filas = conn.execute(
        "SELECT * FROM activity_log WHERE date(timestamp)=? ORDER BY timestamp", (fecha,)
    ).fetchall()
    anterior = conn.execute(
        "SELECT date(timestamp) d FROM activity_log WHERE date(timestamp)<?"
        " ORDER BY timestamp DESC LIMIT 1", (fecha,)).fetchone()
    siguiente = conn.execute(
        "SELECT date(timestamp) d FROM activity_log WHERE date(timestamp)>?"
        " ORDER BY timestamp LIMIT 1", (fecha,)).fetchone()
    metricas = {r["ia"]: r for r in conn.execute(
        "SELECT * FROM metrics_snapshot WHERE fecha=?", (fecha,))}
    conn.close()

    if not filas:
        return HTMLResponse(pagina(
            f"{_fecha_corta(fecha)} — AI SEO Battle", "/diario",
            vacio(f"Ningún agente registró nada el {esc(fecha)}.") +
            '<p class="pag"><a href="/diario">← Volver al cruce</a></p>'), status_code=404)

    coste = sum((r["coste_estimado"] or 0) for r in filas)
    bloqueos = sum(1 for r in filas if r["resultado"] == "error")
    activas = len({r["ia"] for r in filas})
    tiles = "".join([
        f'<div class="tile"><span class="n">{activas}/4</span><span class="k">IAs con turno</span></div>',
        f'<div class="tile"><span class="n">{len(filas)}</span><span class="k">turnos del día</span></div>',
        f'<div class="tile"><span class="n">{bloqueos}</span><span class="k">bloqueados</span></div>',
        f'<div class="tile"><span class="n">{coste:.2f}$</span><span class="k">gastado ese día</span></div>',
    ])

    bloques = []
    for ia_ in ORDEN_IA:
        suyas = [r for r in filas if r["ia"] == ia_]
        if not suyas:
            continue
        m = metricas.get(ia_)
        pie = ""
        if m:
            pie = (f'<p class="hint">Ese día: {m["clics_gsc"] or 0} clics · '
                   f'{m["impresiones_gsc"] or 0} impresiones · '
                   f'{m["suscriptores_organicos"] or 0} suscriptores orgánicos.</p>')
        tarjetas = "".join(
            tarjeta_decision(ev, mostrar_ia=False, bloqueada=(ev["resultado"] == "error"))
            for ev in suyas)
        bloques.append(
            f'<h2><span class="chip" style="background:{color(ia_)};display:inline-block;'
            f'margin-right:8px"></span>{esc(etiqueta(ia_))}</h2>{pie}{tarjetas}')

    nav = []
    nav.append(f'<a href="/diario/{anterior["d"]}">← {esc(_fecha_corta(anterior["d"]))}</a>'
               if anterior else '<span class="hueco">← primer día</span>')
    nav.append('<a href="/diario">Volver al cruce</a>')
    nav.append(f'<a href="/diario/{siguiente["d"]}">{esc(_fecha_corta(siguiente["d"]))} →</a>'
               if siguiente else '<span class="hueco">último día →</span>')

    return pagina(
        f"{_fecha_corta(fecha)} de 2026 — AI SEO Battle", "/diario",
        f"""
<h2 style="margin-top:28px">El día {esc(fecha)}</h2>
<p class="sub">Todo lo que decidieron las cuatro esa jornada, con el razonamiento entero de cada una.</p>
<div class="tiles">{tiles}</div>
<div class="pag">{"".join(nav)}</div>
{_tabla_cruce(filas, dias_enlazables=False, tope_celda=0)}
{"".join(bloques)}
<div class="pag">{"".join(nav)}</div>
""",
        descripcion=f"Qué decidieron las cuatro IAs del experimento el {fecha}, y por qué.",
        canonical=f"{_base_url()}/diario/{fecha}" if _base_url() else "",
    )


# ── La matriz de imágenes ───────────────────────────────────────────────────

GENERADORES = [("openai", "OpenAI"), ("gemini", "Gemini")]
_RE_NOMBRE_SEGURO = re.compile(r"^[A-Za-z0-9._-]+$")


def _url_imagen(ia: str, ruta_local: str | None) -> str:
    """La ruta del fichero en disco → su URL pública en el subdominio de esa
    IA. Se reconstruye a partir del nombre en vez de servir el fichero desde
    aquí: Caddy ya lo publica, y el dashboard sigue sin tocar el disco de los
    agentes. El nombre se valida porque acaba dentro de un href de una página
    pública y viene de una fila de base de datos, no de una constante."""
    dom = _dominio()
    if not ruta_local or not dom or ia not in IAS:
        return ""
    nombre = Path(ruta_local).name
    if not _RE_NOMBRE_SEGURO.match(nombre):
        return ""
    return f"https://{ia}.{dom}/og/matriz/{nombre}"


@app.get("/imagenes", response_class=HTMLResponse)
def imagenes():
    """El experimento dentro del experimento: quién escribe el prompt de una
    imagen y quién la dibuja son dos decisiones distintas, y nadie ha medido
    qué PAREJA funciona mejor. Con 4 diseñadores y 2 generadores salen 8
    combinaciones, cada una seguible hasta el CTR de la pieza que acompaña.
    """
    conn = get_conn()
    filas = conn.execute(
        "SELECT * FROM imagenes_matriz WHERE resultado='exito' ORDER BY creado_el DESC LIMIT 60"
    ).fetchall()
    celdas = {(r["disenador"], r["generador"]): r for r in conn.execute(
        "SELECT disenador, generador, COUNT(*) n, AVG(ctr) ctr, SUM(clics) clics,"
        " SUM(impresiones) impresiones, AVG(coste_prompt_usd + coste_imagen_usd) coste,"
        " AVG(seg_imagen) seg FROM imagenes_matriz WHERE resultado='exito'"
        " GROUP BY disenador, generador")}
    fallos = conn.execute(
        "SELECT COUNT(*) n FROM imagenes_matriz WHERE resultado='error'").fetchone()["n"]
    conn.close()

    if not celdas:
        cuerpo_matriz = vacio("Todavía no hay ninguna pareja con imágenes. La matriz se llena sola "
                              "conforme cada agente publica piezas nuevas.")
    else:
        cab = "".join(f"<th>lo dibuja {esc(n)}</th>" for _, n in GENERADORES)
        cuerpos = []
        for dis in ORDEN_IA:
            tds = []
            for gen, _ in GENERADORES:
                c = celdas.get((dis, gen))
                if not c:
                    tds.append('<td class="celda-vacia">—</td>')
                    continue
                ctr = (f'{c["ctr"] * 100:.2f}% CTR' if c["ctr"] is not None
                       else "CTR aún sin datos")
                tds.append(
                    f'<td><span class="n-grande">{ctr}</span>'
                    f'<span class="sub-celda">{c["n"]} imagen{"es" if c["n"] != 1 else ""} · '
                    f'{(c["coste"] or 0) * 100:.1f}¢ · {(c["seg"] or 0):.0f}s</span></td>')
            cuerpos.append(
                f'<tr><td><span class="tag"><span class="chip" style="background:{color(dis)}">'
                f'</span>lo piensa {esc(etiqueta(dis))}</span></td>{"".join(tds)}</tr>')
        cuerpo_matriz = (f'<div class="scroll"><table class="mtz"><tr><th></th>{cab}</tr>'
                         f'{"".join(cuerpos)}</table></div>')

    # Galería: las imágenes de una misma pieza, juntas. Es la comparación que
    # de verdad se puede hacer a ojo — mismo prompt, mismo artículo, dos
    # dibujantes — y sin ella la matriz es una tabla de números sin cara.
    por_pieza: dict[tuple, list] = {}
    for r in filas:
        por_pieza.setdefault((r["ia"], r["slug"], r["url_articulo"]), []).append(r)
    tarjetas = []
    for (ia_, slug, url_art), imgs in list(por_pieza.items())[:12]:
        cajas = []
        for r in imgs:
            src = _url_imagen(r["ia"], r["ruta_local"])
            if not src:
                continue
            ctr = (f'{r["ctr"] * 100:.2f}% CTR' if r["ctr"] is not None else "sin datos de CTR aún")
            cajas.append(f"""<figure class="p-img">
<img src="{esc(src)}" alt="og:image de {esc(slug)} dibujada por {esc(r["generador"])}"
     width="1200" height="630" loading="lazy">
<figcaption><b>La piensa {esc(etiqueta(r["disenador"]))} · la dibuja {esc(r["generador"])}</b><br>
{esc(ctr)} · {(r["coste_imagen_usd"] or 0) * 100:.1f}¢ · {(r["seg_imagen"] or 0):.0f}s ·
{(r["bytes"] or 0) // 1024} KB</figcaption></figure>""")
        if not cajas:
            continue
        prompt = (imgs[0]["prompt"] or "").strip()
        url_ok = url_art if (url_art or "").startswith(("http://", "https://")) else ""
        titulo = (f'<a href="{esc(url_ok)}" rel="nofollow noopener">{esc(slug)}</a>'
                  if url_ok else esc(slug))
        tarjetas.append(f"""<section class="pareja">
<header><h3><span class="chip" style="background:{color(ia_)};display:inline-block;
margin-right:7px"></span>{titulo}</h3>
<p class="p-meta">en la web de {esc(etiqueta(ia_))}</p></header>
<div class="p-imgs">{"".join(cajas)}</div>
<details class="p-prompt"><summary>El prompt exacto que se usó</summary>
<p>{esc(prompt)}</p></details></section>""")

    galeria = "".join(tarjetas) or vacio(
        "Todavía no hay imágenes publicadas que comparar.")
    nota_fallos = (f'<p class="hint">{fallos} intento{"s" if fallos != 1 else ""} de generación '
                   f'falló y no está aquí: una imagen que no salió no es un resultado de la '
                   f'pareja, es un error de la API.</p>' if fallos else "")

    return pagina(
        "La matriz de imágenes — AI SEO Battle", "/imagenes", f"""
<h2 style="margin-top:28px">Quién la piensa y quién la dibuja</h2>
<p class="sub">Una imagen social son dos decisiones distintas: escribir el prompt y generar el
dibujo. La pregunta que nadie ha medido no es qué IA hace mejores imágenes, sino qué
<b>pareja</b> funciona mejor. Cuatro que escriben el prompt, dos que dibujan: ocho combinaciones,
cada una siguiendo hasta el CTR real de la pieza que acompaña.</p>
<p class="hint">Corre sobre la <code>og:image</code> y no sobre las imágenes del artículo a
propósito: la og:image no está en la página, así que no pesa ni empeora el tiempo de carga, y sí
decide si alguien hace clic cuando el enlace se comparte. Es el único sitio donde una imagen
generada se paga sola.</p>
{cuerpo_matriz}
{nota_fallos}
<h2>Las parejas, una al lado de otra</h2>
<p class="hint">Mismo artículo y mismo prompt, dos dibujantes. La comparación que sí se puede
hacer a ojo.</p>
{galeria}
""",
        descripcion=("Cuatro IAs escriben prompts de imagen y dos las dibujan: ocho parejas "
                     "medidas hasta el CTR real. El experimento dentro del experimento."),
        canonical=f"{_base_url()}/imagenes" if _base_url() else "",
    )


@app.get("/og.png")
def og_png():
    """La tarjeta social, dibujada con el marcador del momento."""
    conn = get_conn()
    agregados, ultimos = _datos_comunes(conn)
    dias = conn.execute("SELECT COUNT(DISTINCT fecha) d FROM metrics_snapshot").fetchone()["d"]
    firma = str(conn.execute(
        "SELECT COUNT(*), MAX(ingested_at) FROM metrics_snapshot").fetchone()[:])
    conn.close()

    filas = [{"ia": f["ia"], "etiqueta": etiqueta(f["ia"]), "organicos": f["organicos"]}
             for f in _leaderboard_filas(agregados, ultimos)]
    # Sin datos todavía, la tarjeta enseña a las cuatro a cero en vez de salir
    # vacía: "aún no ha empezado a puntuar" también es información.
    if not filas:
        filas = [{"ia": i, "etiqueta": etiqueta(i), "organicos": 0} for i in ORDEN_IA]

    png = tarjeta_og.generar(filas, dias, f"{firma}|{len(filas)}")
    return Response(content=png, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=900"})


# ── El diario de diseño ─────────────────────────────────────────────────────
# Los turnos de diseño son raros: martes y jueves cada agente rehace una
# pieza de SU PROPIO sitio, con su presupuesto aparte y con un prompt de
# diseño que escribió ella misma para sí misma. Mezclados con los turnos
# diarios de contenido se pierden —son 2 de cada 9— y son justo los
# que se pueden mirar con los ojos en vez de leerlos: la única página del
# marcador donde el enlace importante es "ve a ver cómo quedó".


@app.get("/diseno", response_class=HTMLResponse)
def diseno():
    conn = get_conn()
    turnos = conn.execute(
        "SELECT * FROM activity_log WHERE tipo_tarea='diseno' ORDER BY timestamp DESC"
    ).fetchall()
    agregado = {r["ia"]: r for r in conn.execute(
        "SELECT ia, COUNT(*) n, SUM(CASE WHEN resultado='error' THEN 1 ELSE 0 END) fallidos,"
        " SUM(COALESCE(coste_estimado,0)) coste, MAX(timestamp) ultimo"
        " FROM activity_log WHERE tipo_tarea='diseno' GROUP BY ia")}
    conn.close()

    if not turnos:
        return pagina("El diario de diseño — AI SEO Battle", "/diseno", f"""
<h2 style="margin-top:28px">El diario de diseño</h2>
{vacio("Todavía no ha habido ningún turno de diseño. Corren los martes y los jueves.")}""")

    dom = _dominio()
    ultimo_por_ia = {}
    for t in turnos:
        ultimo_por_ia.setdefault(t["ia"], t)

    tarjetas = []
    for ia in ORDEN_IA:
        a = agregado.get(ia)
        u = ultimo_por_ia.get(ia)
        # El bote de diseño es aparte del de contenido (5 € contra 10 €), y
        # esta es la única página donde esa cifra significa algo.
        try:
            bote = presupuesto.estado(ia, tipo=presupuesto.TIPO_DISENO)
        except Exception:
            bote = None
        hecho = (f'<b>{esc(_fecha_corta((u["timestamp"] or "")[:10]))}</b><br>'
                 f'{esc(_corto(u["output_resumen"] or u["detalle_error"] or "", 130))}'
                 if u else "Aún no ha tenido ningún turno de diseño.")
        barra = ""
        if bote:
            barra = (f'<span class="barra-pista" style="margin-top:8px">'
                     f'<span class="barra" style="width:{min(bote["fraccion"],1.0)*100:.1f}%;'
                     f'background:{color(ia)}"></span></span>'
                     f'<span class="r-mix">{bote["gastado"]:.2f}€ de {bote["tope"]:.0f}€ '
                     f'de su bote de diseño este mes</span>')
        visitar = (f'<a class="r-ver" href="https://{ia}.{dom}" rel="nofollow noopener">'
                   f'ver su web →</a>' if dom else "")
        tarjetas.append(f"""<article class="r-card" style="--c:{color(ia)}">
  <div class="r-cab"><h3><a href="/ia/{ia}">{esc(etiqueta(ia))}</a></h3>{visitar}</div>
  <dl class="r-datos">
    <div><dt>turnos de diseño</dt><dd>{(a["n"] - (a["fallidos"] or 0)) if a else 0}</dd></div>
    <div><dt>fallidos</dt><dd>{(a["fallidos"] or 0) if a else 0}</dd></div>
  </dl>
  <p class="r-ult">{hecho}</p>
  {barra}
</article>""")

    # Qué ficheros toca cada una al rediseñar: es el resumen más honesto de
    # en qué está trabajando cada agente, y no se ve en ningún otro sitio.
    ficheros: dict[str, dict[str, int]] = {}
    for t in turnos:
        try:
            for c in json.loads(t["cambios"] or "[]"):
                arch = str(c.get("archivo", ""))
                if arch and not arch.startswith(("og/", "log.json", "memoria/")):
                    ficheros.setdefault(t["ia"], {})[arch] = (
                        ficheros.get(t["ia"], {}).get(arch, 0) + (c.get("anadidas") or 0))
        except (json.JSONDecodeError, TypeError):
            continue
    filas_f = "".join(
        f'<tr><td><span class="tag"><span class="chip" style="background:{color(ia)}"></span>'
        f'{esc(etiqueta(ia))}</span></td><td>'
        + " · ".join(f"<code>{esc(a)}</code> +{n}"
                     for a, n in sorted(ficheros[ia].items(), key=lambda x: -x[1])[:6])
        + "</td></tr>"
        for ia in ORDEN_IA if ficheros.get(ia)
    )
    tabla_f = (f'<div class="scroll"><table><tr><th>IA</th><th>Qué ha construido</th></tr>'
               f'{filas_f}</table></div>') if filas_f else ""

    por_dia: dict[str, list] = {}
    for t in turnos:
        por_dia.setdefault((t["timestamp"] or "")[:10], []).append(t)
    bloques = []
    for dia in sorted(por_dia, reverse=True):
        cuerpo = "".join(
            tarjeta_decision(ev, bloqueada=(ev["resultado"] == "error")) for ev in por_dia[dia])
        bloques.append(f'<h2>{esc(_fecha_corta(dia))} · <a href="/diario/{dia}">ver el día '
                       f'completo</a></h2>{cuerpo}')

    return pagina(
        "El diario de diseño — AI SEO Battle", "/diseno", f"""
<h2 style="margin-top:28px">Martes y jueves, cada una rehace su propia web</h2>
<p class="sub">El turno de diseño es distinto a los demás: cae dos días por semana, tiene su propio presupuesto
aparte del de contenido, y cada agente lo ejecuta con un prompt de diseño que escribió ella misma
para sí misma. Nadie les dice cómo tiene que quedar.</p>
<p class="hint">Es la única parte del experimento que se mira en vez de leerse: los enlaces de
«ver su web» llevan al resultado en vivo. Debajo está el porqué de cada decisión, entero.</p>

<div class="resu">{"".join(tarjetas)}</div>

{f'<h2>En qué está trabajando cada una</h2><p class="hint">Los ficheros que ha tocado rediseñando, y cuántas líneas les ha metido.</p>{tabla_f}' if tabla_f else ''}

<h2>El cruce, turno a turno</h2>
{_tabla_cruce(turnos, tope_celda=0)}

{"".join(bloques)}
""",
        descripcion=("Martes y jueves las cuatro IAs rediseñan su propia web con su propio "
                     "presupuesto. Qué cambió cada una, por qué, y cómo quedó."),
        canonical=f"{_base_url()}/diseno" if _base_url() else "",
    )
