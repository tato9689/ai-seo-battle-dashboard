"""Dashboard público del experimento AI SEO Battle.

Sin auth (a diferencia de tato9689-panel): la gracia del experimento es que
se vea en vivo. Lee directamente la SQLite que rellenan poller.py y
poller_metrics.py — este proceso nunca escribe en la base, solo consulta.

Se va a compartir en LinkedIn/HN y se va a ver sobre todo en móvil, así que
no es un volcado de tablas: hay un leaderboard con el KPI de victoria, la
evolución de las 10 semanas, y la tabla completa debajo para quien quiera
el detalle.
"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import get_conn  # noqa: E402

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

esc = html.escape
app = FastAPI()

# Orden fijo de color por IA (nunca ciclado, nunca por posición en el
# ranking): el color identifica al agente, así que un cambio de puesto no
# puede repintar a nadie. Slots 1-4 de la paleta categórica, validados en
# claro y oscuro con el validador del método (adjacent pairlist).
COLOR_IA = {
    "claude": ("--s1", "Claude"),
    "gpt": ("--s2", "GPT"),
    "gemini": ("--s3", "Gemini"),
    "deepseek": ("--s4", "DeepSeek"),
}
ORDEN_IA = ["claude", "gpt", "gemini", "deepseek"]


def etiqueta(ia: str) -> str:
    return COLOR_IA.get(ia, ("--s1", ia))[1]


def color(ia: str) -> str:
    return f"var({COLOR_IA.get(ia, ('--s1', ia))[0]})"


ESTILO = """
<style>
  :root {
    color-scheme: light;
    --surface: #fcfcfb;
    --surface-2: #f3f3f1;
    --border: #e2e2dd;
    --text: #0b0b0b;
    --text-2: #52514e;
    --text-3: #78776f;
    --s1: #2a78d6; --s2: #eb6834; --s3: #1baf7a; --s4: #eda100;
    --error: #e34948;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      color-scheme: dark;
      --surface: #1a1a19;
      --surface-2: #232322;
      --border: #34342f;
      --text: #ffffff;
      --text-2: #c3c2b7;
      --text-3: #8e8d84;
      --s1: #3987e5; --s2: #d95926; --s3: #199e70; --s4: #c98500;
      --error: #e66767;
    }
  }
  * { box-sizing: border-box; }
  body {
    font-family: ui-sans-serif, -apple-system, system-ui, "Segoe UI", sans-serif;
    max-width: 1040px; margin: 0 auto; padding: 32px 20px 64px;
    background: var(--surface); color: var(--text);
    line-height: 1.5; -webkit-font-smoothing: antialiased;
  }
  a { color: var(--s1); }
  header.top { display: flex; flex-wrap: wrap; gap: 12px 24px; align-items: baseline; justify-content: space-between; margin-bottom: 4px; }
  h1 { font-size: 1.5rem; margin: 0; letter-spacing: -0.01em; }
  h2 { font-size: 1.05rem; margin: 40px 0 4px; letter-spacing: -0.01em; }
  .sub { color: var(--text-2); font-size: 0.9rem; margin: 4px 0 0; }
  .hint { color: var(--text-3); font-size: 0.8rem; margin: 4px 0 16px; }
  .vivo { display: inline-flex; align-items: center; gap: 7px; font-size: 0.8rem; color: var(--text-2); }
  .punto { width: 7px; height: 7px; border-radius: 50%; background: var(--s3); }
  @media (prefers-reduced-motion: no-preference) {
    .punto { animation: latido 2.4s ease-in-out infinite; }
    @keyframes latido { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
  }

  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 16px; }
  .tile { background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
  .tile .n { display: block; font-size: 1.7rem; font-weight: 600; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
  .tile .k { display: block; font-size: 0.78rem; color: var(--text-2); margin-top: 2px; }

  .lb { display: flex; flex-direction: column; gap: 2px; margin-top: 14px; }
  .lb-fila { display: grid; grid-template-columns: 1.6rem 6.5rem 1fr auto; gap: 12px; align-items: center; padding: 9px 4px; border-bottom: 1px solid var(--border); }
  .lb-fila:last-child { border-bottom: 0; }
  .puesto { color: var(--text-3); font-size: 0.85rem; font-variant-numeric: tabular-nums; }
  .nombre { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 0.9rem; }
  .chip { width: 10px; height: 10px; border-radius: 3px; flex: none; }
  /* display:block en ambos a propósito: un <span> inline ignora width/height,
     que es justo lo que la barra necesita para representar el dato. */
  .barra-pista { display: block; background: var(--surface-2); border-radius: 4px; height: 12px; overflow: hidden; }
  .barra { display: block; height: 100%; border-radius: 0 4px 4px 0; min-width: 3px; }
  .cifra { font-variant-numeric: tabular-nums; font-weight: 600; font-size: 0.9rem; white-space: nowrap; }
  .cifra small { display: block; font-weight: 400; font-size: 0.72rem; color: var(--text-3); text-align: right; }
  @media (max-width: 560px) {
    /* La barra pasa a su propia línea: a 390px no caben nombre, barra y cifra
       en una fila sin que la barra quede demasiado corta para leerse. */
    .lb-fila { grid-template-columns: 1.4rem 1fr auto; }
    .barra-pista { grid-column: 2 / -1; }
    .cifra, .cifra small { text-align: left; }
  }

  figure { margin: 14px 0 0; }
  .leyenda { display: flex; flex-wrap: wrap; gap: 6px 16px; margin: 0 0 10px; padding: 0; list-style: none; font-size: 0.8rem; color: var(--text-2); }
  .leyenda li { display: flex; align-items: center; gap: 6px; }
  svg { display: block; width: 100%; height: auto; overflow: visible; }
  .eje { stroke: var(--border); stroke-width: 1; }
  .rejilla { stroke: var(--border); stroke-width: 1; stroke-dasharray: 2 4; }
  .eje-txt { fill: var(--text-3); font-size: 10px; font-family: inherit; }
  .serie-etq { font-size: 10px; font-weight: 600; font-family: inherit; }

  .scroll { overflow-x: auto; margin-top: 14px; border: 1px solid var(--border); border-radius: 10px; }
  table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
  th, td { text-align: left; padding: 9px 12px; border-bottom: 1px solid var(--border); vertical-align: top; white-space: nowrap; }
  th { color: var(--text-2); font-weight: 600; position: sticky; top: 0; background: var(--surface-2); }
  tr:last-child td { border-bottom: 0; }
  td.resumen { white-space: normal; min-width: 260px; color: var(--text-2); }
  .tag { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; }
  .error { color: var(--error); font-weight: 600; }
  .vacio { border: 1px dashed var(--border); border-radius: 10px; padding: 28px 20px; text-align: center; color: var(--text-2); font-size: 0.88rem; margin-top: 14px; }
  footer { margin-top: 56px; padding-top: 16px; border-top: 1px solid var(--border); color: var(--text-3); font-size: 0.8rem; }
</style>
"""


def vacio(mensaje: str) -> str:
    return f'<div class="vacio">{esc(mensaje)}</div>'


def grafica_lineas(series: dict[str, list[tuple[str, float]]], etiqueta_y: str) -> str:
    """Evolución temporal, una línea por IA. SVG generado en el servidor: sin
    librería externa que cargar, funciona sin JS y no añade dependencias que
    mantener durante 10 semanas.

    series: {ia: [(fecha_iso, valor), ...]} ya ordenado por fecha.
    """
    series = {ia: puntos for ia, puntos in series.items() if len(puntos) >= 2}
    if not series:
        return vacio("Aún no hay suficientes días de datos para dibujar la evolución. "
                     "Aparecerá sola en cuanto haya dos snapshots.")

    W, H = 720, 240
    PAD_I, PAD_D, PAD_S, PAD_B = 38, 54, 12, 26
    fechas = sorted({f for puntos in series.values() for f, _ in puntos})
    idx = {f: i for i, f in enumerate(fechas)}
    max_v = max((v for puntos in series.values() for _, v in puntos), default=0) or 1
    # Techo redondeado hacia arriba: un eje que acaba en 37 se lee peor que uno
    # que acaba en 40.
    paso = max(1, round(max_v / 4))
    techo = paso * 4

    def x(f):
        return PAD_I if len(fechas) == 1 else PAD_I + idx[f] * (W - PAD_I - PAD_D) / (len(fechas) - 1)

    def y(v):
        return PAD_S + (1 - v / techo) * (H - PAD_S - PAD_B)

    partes = []
    for i in range(5):
        v = techo * i / 4
        yy = y(v)
        partes.append(f'<line class="rejilla" x1="{PAD_I}" y1="{yy:.1f}" x2="{W - PAD_D}" y2="{yy:.1f}"/>')
        partes.append(f'<text class="eje-txt" x="{PAD_I - 8}" y="{yy + 3:.1f}" text-anchor="end">{v:.0f}</text>')

    # Solo primera y última fecha: etiquetar cada día colisiona en móvil.
    for f in (fechas[0], fechas[-1]) if len(fechas) > 1 else (fechas[0],):
        ancla = "start" if f == fechas[0] else "end"
        partes.append(f'<text class="eje-txt" x="{x(f):.1f}" y="{H - 8}" text-anchor="{ancla}">{esc(f[5:])}</text>')

    for ia in ORDEN_IA:
        puntos = series.get(ia)
        if not puntos:
            continue
        d = " ".join(
            f"{'M' if i == 0 else 'L'}{x(f):.1f},{y(v):.1f}" for i, (f, v) in enumerate(puntos)
        )
        partes.append(f'<path d="{d}" fill="none" stroke="{color(ia)}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
        f_fin, v_fin = puntos[-1]
        # Anillo del color de la superficie para que dos líneas que acaban
        # juntas no se fundan en una sola mancha.
        partes.append(f'<circle cx="{x(f_fin):.1f}" cy="{y(v_fin):.1f}" r="4" fill="{color(ia)}" stroke="var(--surface)" stroke-width="2"/>')
        partes.append(
            f'<text class="serie-etq" x="{x(f_fin) + 9:.1f}" y="{y(v_fin) + 3.5:.1f}" fill="{color(ia)}">{esc(etiqueta(ia))}</text>'
        )

    leyenda = "".join(
        f'<li><span class="chip" style="background:{color(ia)}"></span>{esc(etiqueta(ia))}</li>'
        for ia in ORDEN_IA if ia in series
    )
    return (
        f'<figure><ul class="leyenda">{leyenda}</ul>'
        f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(etiqueta_y)} por IA a lo largo del experimento">'
        f'<line class="eje" x1="{PAD_I}" y1="{H - PAD_B}" x2="{W - PAD_D}" y2="{H - PAD_B}"/>'
        + "".join(partes)
        + "</svg></figure>"
    )


def leaderboard(filas: list[dict]) -> str:
    """Ranking por el KPI de victoria: suscriptores orgánicos netos.

    Deliberadamente NO es un score compuesto — un número opaco en un panel
    público invita a discutir la fórmula en vez de los datos. El resto de
    métricas van al lado, visibles pero sin fundirse en una sola cifra.
    """
    if not filas:
        return vacio("El leaderboard aparece con el primer suscriptor. "
                     "Mientras tanto, la actividad de las 4 IAs ya se registra abajo.")
    tope = max((f["organicos"] for f in filas), default=0) or 1
    salida = []
    for puesto, f in enumerate(filas, 1):
        ancho = f["organicos"] / tope * 100
        cps = f["coste_por_susc"]
        # Con costes de céntimos, dos decimales lo enseñan todo como "0.00$" y
        # la métrica de eficiencia deja de decir nada. Se ajusta la precisión
        # al orden de magnitud en vez de fijarla.
        if cps is None:
            coste_txt = "sin suscriptores aún"
        elif cps >= 1:
            coste_txt = f"{cps:.2f}$/suscriptor"
        elif cps >= 0.01:
            coste_txt = f"{cps:.3f}$/suscriptor"
        else:
            coste_txt = f"{cps * 100:.2f}¢/suscriptor"
        salida.append(
            f'<div class="lb-fila">'
            f'<span class="puesto">{puesto}</span>'
            f'<span class="nombre"><span class="chip" style="background:{color(f["ia"])}"></span>{esc(etiqueta(f["ia"]))}</span>'
            f'<span class="barra-pista"><span class="barra" style="width:{ancho:.1f}%;background:{color(f["ia"])}"></span></span>'
            f'<span class="cifra">{f["organicos"]}<small>{coste_txt}</small></span>'
            f"</div>"
        )
    return f'<div class="lb">{"".join(salida)}</div>'


def _cabecera(titulo: str, activo: str) -> str:
    nav = {"/": "Actividad", "/llms": "Modelos"}
    enlaces = " · ".join(
        f'<a href="{ruta}" {"style=\"color:var(--text-3)\"" if ruta == activo else ""}>{txt}</a>'
        for ruta, txt in nav.items()
    )
    return (
        f'<header class="top"><div><h1>{esc(titulo)}</h1>'
        f'<p class="sub">Cuatro modelos de IA compiten por suscriptores reales haciendo SEO en sus propias webs, sin supervisión humana diaria.</p></div>'
        f'<span class="vivo"><span class="punto"></span>en vivo · {enlaces}</span></header>'
    )


PIE = (
    '<footer>Datos crudos del experimento, sin editar. El leaderboard puntúa solo altas de '
    'origen orgánico: el proyecto se promociona por su propia historia y ese tráfico de '
    'curiosidad no mide quién hace mejor SEO. · '
    '<a href="https://tato9689.com/proyectos-ia/ai-seo-battle/">Sobre el experimento</a></footer>'
)
# Refresco pasivo: el poller escribe cada 15 min, así que recargar cada 2 es
# de sobra para que se sienta vivo sin machacar el servidor.
AUTOREFRESCO = '<meta http-equiv="refresh" content="120">'


@app.get("/", response_class=HTMLResponse)
def home():
    conn = get_conn()
    agregados = {
        row["ia"]: row
        for row in conn.execute(
            """
            SELECT ia, COUNT(*) AS n, SUM(coste_estimado) AS coste,
                   SUM(CASE WHEN resultado='error' THEN 1 ELSE 0 END) AS errores
            FROM activity_log GROUP BY ia
            """
        )
    }
    # 30 y no 100: el feed es para dar sensación de actividad viva, no para
    # auditar el histórico (eso es export.py). Con 100 filas repetitivas la
    # tabla se come la página y entierra el leaderboard y las gráficas.
    eventos = conn.execute(
        "SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT 30"
    ).fetchall()
    ultimos = {
        row["ia"]: row
        for row in conn.execute(
            """
            SELECT m.* FROM metrics_snapshot m
            INNER JOIN (SELECT ia, MAX(fecha) AS fecha FROM metrics_snapshot GROUP BY ia) ult
                ON m.ia = ult.ia AND m.fecha = ult.fecha
            """
        )
    }
    historico = conn.execute(
        "SELECT ia, fecha, suscriptores_organicos, clics_gsc FROM metrics_snapshot ORDER BY fecha"
    ).fetchall()
    dias = conn.execute("SELECT COUNT(DISTINCT fecha) AS d FROM metrics_snapshot").fetchone()["d"]
    conn.close()

    # --- Leaderboard: orgánicos netos, y coste por suscriptor orgánico ---
    filas_lb = []
    for ia in ORDEN_IA:
        m = ultimos.get(ia)
        if not m:
            continue
        organicos = m["suscriptores_organicos"] or 0
        coste = (agregados.get(ia, {})["coste"] if ia in agregados else 0) or 0
        filas_lb.append({
            "ia": ia,
            "organicos": organicos,
            "meta": m["suscriptores_meta"] or 0,
            "coste": coste,
            # La eficiencia es la comparación honesta: premia a quien convierte
            # barato, no a quien más publica.
            "coste_por_susc": (coste / organicos) if organicos else None,
        })
    filas_lb.sort(key=lambda f: (-f["organicos"], f["coste_por_susc"] or 9e9))

    total_org = sum(f["organicos"] for f in filas_lb)
    total_meta = sum(f["meta"] for f in filas_lb)
    total_coste = sum((r["coste"] or 0) for r in agregados.values())
    total_acciones = sum(r["n"] for r in agregados.values())

    tiles = "".join([
        f'<div class="tile"><span class="n">{total_org}</span><span class="k">suscriptores orgánicos</span></div>',
        f'<div class="tile"><span class="n">{total_meta}</span><span class="k">altas por curiosidad (fuera del ranking)</span></div>',
        f'<div class="tile"><span class="n">{total_acciones}</span><span class="k">decisiones tomadas por las IAs</span></div>',
        f'<div class="tile"><span class="n">{total_coste:.2f}$</span><span class="k">coste real acumulado</span></div>',
        f'<div class="tile"><span class="n">{dias}</span><span class="k">días de experimento</span></div>',
    ])

    def serie(campo):
        out = {}
        for row in historico:
            if row[campo] is not None:
                out.setdefault(row["ia"], []).append((row["fecha"], row[campo]))
        return out

    filas = "".join(
        f"<tr>"
        f'<td>{esc((ev["timestamp"] or "")[:16].replace("T", " "))}</td>'
        f'<td><span class="tag"><span class="chip" style="background:{color(ev["ia"])}"></span>{esc(etiqueta(ev["ia"]))}</span></td>'
        f'<td>fase {ev["fase"]}</td>'
        f'<td>{esc(ev["modelo_exacto"] or "—")}</td>'
        f'<td>{esc(ev["accion_tipo"] or "—")}</td>'
        f'<td class="resumen">{esc(ev["output_resumen"] or "")}</td>'
        f'<td class="{"error" if ev["resultado"] == "error" else ""}">{esc(ev["resultado"] or "")}</td>'
        f"</tr>"
        for ev in eventos
    )
    tabla = (
        '<div class="scroll"><table>'
        "<tr><th>Cuándo</th><th>IA</th><th>Fase</th><th>Modelo</th><th>Acción</th><th>Qué hizo y por qué</th><th></th></tr>"
        f"{filas}</table></div>"
    ) if eventos else vacio("Todavía no ha actuado ninguna IA. En cuanto arranquen los crons diarios, cada decisión aparece aquí.")

    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{AUTOREFRESCO}
<title>AI SEO Battle — actividad en vivo</title>{ESTILO}</head>
<body>
{_cabecera("AI SEO Battle", "/")}
<div class="tiles">{tiles}</div>

<h2>Leaderboard</h2>
<p class="hint">Suscriptores orgánicos netos — el criterio de victoria. Debajo de cada cifra, lo que le costó conseguirlos.</p>
{leaderboard(filas_lb)}

<h2>Evolución: suscriptores orgánicos</h2>
<p class="hint">Lo que decide el experimento, semana a semana.</p>
{grafica_lineas(serie("suscriptores_organicos"), "Suscriptores orgánicos")}

<h2>Evolución: clics desde Google</h2>
<p class="hint">El escalón previo. Un dominio nuevo tarda semanas en tener clics, y meses en convertirlos.</p>
{grafica_lineas(serie("clics_gsc"), "Clics en Search Console")}

<h2>Últimas decisiones</h2>
<p class="hint">Sin filtrar y sin editar, incluidos los intentos bloqueados por los guardarraíles.</p>
{tabla}
{PIE}
</body></html>"""


@app.get("/llms", response_class=HTMLResponse)
def llms():
    """Observatorio de rendimiento real de los 4 modelos en tareas SEO en
    producción, no en un benchmark sintético: coste, velocidad y volumen
    tal como salió del propio experimento. Subproducto de activity_log,
    sin infraestructura propia."""
    conn = get_conn()
    por_modelo = conn.execute(
        """
        SELECT modelo_exacto, ia, COUNT(*) AS n_tareas,
               SUM(tokens_in) AS tokens_in, SUM(tokens_out) AS tokens_out,
               SUM(coste_estimado) AS coste_total,
               AVG(coste_estimado) AS coste_medio,
               AVG(duracion_seg) AS duracion_media,
               SUM(CASE WHEN resultado='error' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS tasa_error
        FROM activity_log
        WHERE modelo_exacto IS NOT NULL
        GROUP BY modelo_exacto, ia
        ORDER BY coste_total DESC
        """
    ).fetchall()
    por_tarea = conn.execute(
        """
        SELECT tipo_tarea, ia, COUNT(*) AS n, AVG(coste_estimado) AS coste_medio, AVG(duracion_seg) AS duracion_media
        FROM activity_log
        WHERE tipo_tarea IS NOT NULL
        GROUP BY tipo_tarea, ia
        ORDER BY tipo_tarea, ia
        """
    ).fetchall()
    conn.close()

    filas_modelo = "".join(
        f'<tr><td><span class="tag"><span class="chip" style="background:{color(r["ia"])}"></span>{esc(etiqueta(r["ia"]))}</span></td>'
        f'<td>{esc(r["modelo_exacto"])}</td>'
        f'<td>{r["n_tareas"]}</td>'
        f'<td>{(r["tokens_in"] or 0):,} / {(r["tokens_out"] or 0):,}</td>'
        f'<td>{(r["coste_total"] or 0):.4f}$</td>'
        f'<td>{(r["coste_medio"] or 0):.4f}$</td>'
        f'<td>{(r["duracion_media"] or 0):.1f}s</td>'
        f'<td>{(r["tasa_error"] or 0) * 100:.1f}%</td></tr>'
        for r in por_modelo
    )
    filas_tarea = "".join(
        f'<tr><td>{esc(r["tipo_tarea"])}</td>'
        f'<td><span class="tag"><span class="chip" style="background:{color(r["ia"])}"></span>{esc(etiqueta(r["ia"]))}</span></td>'
        f'<td>{r["n"]}</td><td>{(r["coste_medio"] or 0):.4f}$</td><td>{(r["duracion_media"] or 0):.1f}s</td></tr>'
        for r in por_tarea
    )

    cuerpo_modelo = (
        '<div class="scroll"><table>'
        "<tr><th>IA</th><th>Modelo</th><th>Tareas</th><th>Tokens in/out</th>"
        "<th>Coste total</th><th>Coste/tarea</th><th>Duración media</th><th>Tasa error</th></tr>"
        f"{filas_modelo}</table></div>"
    ) if por_modelo else vacio("Sin ejecuciones todavía. Esta comparativa se llena sola con cada tarea real.")

    cuerpo_tarea = (
        '<div class="scroll"><table>'
        "<tr><th>Tipo de tarea</th><th>IA</th><th>N</th><th>Coste medio</th><th>Duración media</th></tr>"
        f"{filas_tarea}</table></div>"
    ) if por_tarea else ""

    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{AUTOREFRESCO}
<title>AI SEO Battle — comparativa de modelos</title>{ESTILO}</head>
<body>
{_cabecera("Comparativa de modelos", "/llms")}
<h2>Coste y velocidad reales</h2>
<p class="hint">Agregado directo del registro de actividad: datos de producción de un trabajo real de SEO
sostenido durante semanas, no un benchmark sintético. Los tokens y el coste los mide el propio
sistema al hacer cada llamada, nunca los reporta el modelo sobre sí mismo.</p>
{cuerpo_modelo}

<h2>Por tipo de tarea</h2>
<p class="hint">Dónde cada modelo gasta más y dónde va más rápido.</p>
{cuerpo_tarea}
{PIE}
</body></html>"""
