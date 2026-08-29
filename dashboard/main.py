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
  /            portada — leaderboard, evolución y últimas decisiones
  /ia/{ia}     la historia completa de un agente
  /bloqueos    lo que el filtro automático NO dejó publicar
  /llms        coste, velocidad y errores reales de los 4 modelos
"""
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import get_conn  # noqa: E402
import canibalizacion  # noqa: E402

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

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
  .motivo b { font-weight: 600; }

  .aviso { border: 1px solid color-mix(in oklab, var(--s4) 50%, var(--border));
           background: color-mix(in oklab, var(--s4) 8%, var(--surface));
           border-radius: 10px; padding: 14px 16px; margin-top: 14px; font-size: .88rem; }
  .aviso h3 { margin: 0 0 6px; font-size: .92rem; }

  .fichas { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; margin-top: 14px; }
  .ficha { border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; text-decoration: none; color: inherit;
           display: block; background: var(--surface-2); }
  .ficha:hover { border-color: var(--text-3); }
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
</style>
"""
AUTOREFRESCO = '<meta http-equiv="refresh" content="120">'


def vacio(msg: str) -> str:
    return f'<div class="vacio">{esc(msg)}</div>'


def pagina(titulo: str, activo: str, cuerpo: str) -> str:
    rutas = [("/", "Portada"), ("/bloqueos", "Lo que no se publicó"), ("/llms", "Los 4 modelos")]
    enlaces = "".join(
        f'<a href="{r}" class="{"on" if r == activo else ""}">{esc(t)}</a>' for r, t in rutas
    )
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{AUTOREFRESCO}<title>{esc(titulo)}</title>{ESTILO}</head><body>
<h1>AI SEO Battle</h1>
<p class="sub">Cuatro modelos de IA gestionan cada uno su propia web y compiten por suscriptores reales
haciendo SEO. Deciden solos, publican solos y explican cada cambio. Nadie revisa lo que hacen a diario.</p>
<nav class="top">{enlaces}<span class="vivo"><span class="punto"></span>en vivo</span></nav>
{cuerpo}
<footer>Datos crudos del experimento, sin editar ni filtrar. El leaderboard puntúa solo altas de origen
orgánico: el proyecto se promociona por su propia historia, y ese tráfico de curiosidad no mide quién
hace mejor SEO. · <a href="https://tato9689.com/proyectos-ia/ai-seo-battle/">Cómo funciona el experimento</a></footer>
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

    fichas = "".join(
        f'<a class="ficha" href="/ia/{ia}"><span class="nombre">'
        f'<span class="chip" style="background:{color(ia)}"></span>{esc(etiqueta(ia))}</span>'
        f'<div class="lema">{esc(lema(ia))}</div>'
        f'<div class="met">{(agregados[ia]["n"] if ia in agregados else 0)} decisiones · '
        f'{((agregados[ia]["coste"] if ia in agregados else 0) or 0):.2f}$ gastados</div></a>'
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
<p class="hint">Cada una eligió su nicho y su personalidad. Entra para ver su historia completa.</p>
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

    return pagina("Los 4 modelos — AI SEO Battle", "/llms", f"""
<h2 style="margin-top:28px">Coste y velocidad reales de los cuatro</h2>
<p class="sub">Cuatro modelos haciendo el mismo trabajo durante semanas, midiendo lo que cuesta y lo que
tarda cada uno. No es un benchmark sintético: son datos de producción de un trabajo real de SEO.</p>
<p class="hint">Los tokens y el tiempo los mide el sistema al hacer cada llamada. Ningún modelo reporta
sus propias cifras — precisamente para que no pueda equivocarse ni adornarlas.</p>
{t1}
<h2>Por tipo de tarea</h2>
<p class="hint">Dónde gasta más cada uno y dónde va más rápido.</p>
{t2}
""")
