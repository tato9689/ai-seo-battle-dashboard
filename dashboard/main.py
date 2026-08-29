"""Dashboard público del experimento AI SEO Battle.

Sin auth (a diferencia de tato9689-panel): la gracia del experimento es que
se vea en vivo. Lee directamente la SQLite que rellena poller.py — este
proceso nunca escribe en la base, solo consulta.
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

ESTILO = """
<style>
  body { font-family: -apple-system, system-ui, sans-serif; max-width: 960px; margin: 40px auto; padding: 0 20px; background: #0d0d0f; color: #e8e8e8; }
  h1 { font-size: 1.4rem; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #2a2a2e; font-size: 0.85rem; vertical-align: top; }
  th { color: #999; font-weight: 600; }
  .ia { font-weight: 600; }
  .fase1 { color: #6ea8fe; }
  .fase2 { color: #ffb454; }
  .error { color: #ff6b6b; }
  .agg { display: flex; gap: 16px; margin-top: 16px; flex-wrap: wrap; }
  .card { background: #17171b; border-radius: 8px; padding: 12px 16px; min-width: 140px; }
  .card b { display: block; font-size: 1.3rem; }
</style>
"""


@app.get("/", response_class=HTMLResponse)
def home():
    conn = get_conn()
    agregados = conn.execute(
        """
        SELECT ia, COUNT(*) AS n, SUM(coste_estimado) AS coste,
               SUM(CASE WHEN resultado='error' THEN 1 ELSE 0 END) AS errores
        FROM activity_log GROUP BY ia ORDER BY ia
        """
    ).fetchall()
    eventos = conn.execute(
        "SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT 100"
    ).fetchall()
    # último snapshot de resultado (tráfico + leads) por IA, para responder
    # "cómo sabe que le va bien" junto al feed de acciones de arriba.
    resultados = conn.execute(
        """
        SELECT m.* FROM metrics_snapshot m
        INNER JOIN (SELECT ia, MAX(fecha) AS fecha FROM metrics_snapshot GROUP BY ia) ult
            ON m.ia = ult.ia AND m.fecha = ult.fecha
        ORDER BY m.ia
        """
    ).fetchall()
    conn.close()

    cards = "".join(
        f'<div class="card"><b>{esc(row["ia"])}</b>{row["n"]} acciones · '
        f'{(row["coste"] or 0):.3f}$ · {row["errores"]} errores</div>'
        for row in agregados
    )

    cards_resultado = "".join(
        f'<div class="card"><b>{esc(row["ia"])}</b>'
        f'{row["vistas_ga4"] if row["vistas_ga4"] is not None else "–"} vistas · '
        f'{row["suscriptores_totales"] if row["suscriptores_totales"] is not None else "–"} suscriptores · '
        f'pos. media {row["posicion_media_gsc"] if row["posicion_media_gsc"] is not None else "–"}'
        f'<br><small>{esc(row["fecha"])} · fuente: {esc(row["fuente"] or "")}</small></div>'
        for row in resultados
    )

    filas = "".join(
        f'<tr>'
        f'<td>{esc(ev["timestamp"])}</td>'
        f'<td class="ia">{esc(ev["ia"])}</td>'
        f'<td class="fase{ev["fase"]}">fase {ev["fase"]}</td>'
        f'<td>{esc(ev["modelo_exacto"] or "")}</td>'
        f'<td>{esc(ev["tipo_tarea"] or "")}</td>'
        f'<td>{esc(ev["accion_tipo"] or "")}</td>'
        f'<td>{esc(ev["output_resumen"] or "")}</td>'
        f'<td class="{"error" if ev["resultado"]=="error" else ""}">{esc(ev["resultado"] or "")}</td>'
        f'</tr>'
        for ev in eventos
    )

    return f"""<!doctype html><html><head><meta charset="utf-8">
    <title>AI SEO Battle — actividad en vivo</title>{ESTILO}</head>
    <body>
    <h1>AI SEO Battle — actividad en vivo</h1>
    <p><a href="/llms" style="color:#6ea8fe">→ Comparativa de modelos (coste/velocidad reales)</a></p>
    <div class="agg">{cards or '<p>Sin datos todavía.</p>'}</div>
    <h2>Resultado (tráfico + leads)</h2>
    <div class="agg">{cards_resultado or '<p>Sin datos todavía.</p>'}</div>
    <h2>Últimas acciones</h2>
    <table>
      <tr><th>Cuándo</th><th>IA</th><th>Fase</th><th>Modelo</th><th>Tarea</th><th>Acción</th><th>Resumen</th><th>Resultado</th></tr>
      {filas}
    </table>
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
        f'<tr><td class="ia">{esc(r["ia"])}</td><td>{esc(r["modelo_exacto"])}</td>'
        f'<td>{r["n_tareas"]}</td>'
        f'<td>{(r["tokens_in"] or 0):,} / {(r["tokens_out"] or 0):,}</td>'
        f'<td>{(r["coste_total"] or 0):.4f}$</td>'
        f'<td>{(r["coste_medio"] or 0):.4f}$</td>'
        f'<td>{(r["duracion_media"] or 0):.1f}s</td>'
        f'<td>{(r["tasa_error"] or 0) * 100:.1f}%</td></tr>'
        for r in por_modelo
    )
    filas_tarea = "".join(
        f'<tr><td>{esc(r["tipo_tarea"])}</td><td class="ia">{esc(r["ia"])}</td>'
        f'<td>{r["n"]}</td><td>{(r["coste_medio"] or 0):.4f}$</td><td>{(r["duracion_media"] or 0):.1f}s</td></tr>'
        for r in por_tarea
    )

    return f"""<!doctype html><html><head><meta charset="utf-8">
    <title>AI SEO Battle — comparativa de modelos</title>{ESTILO}</head>
    <body>
    <p><a href="/" style="color:#6ea8fe">← volver</a></p>
    <h1>Comparativa de modelos: coste y velocidad reales</h1>
    <p><small>Metodología: agregado directo de activity_log, datos de producción del propio
    experimento SEO, no un benchmark sintético. Coste y tokens tal como los reporta cada
    agente en su /log.json (ver CONTRATO_LOG.md).</small></p>
    <table>
      <tr><th>IA</th><th>Modelo</th><th>Tareas</th><th>Tokens in/out</th>
          <th>Coste total</th><th>Coste medio/tarea</th><th>Duración media</th><th>Tasa error</th></tr>
      {filas_modelo or '<tr><td colspan="8">Sin datos todavía.</td></tr>'}
    </table>
    <h2>Por tipo de tarea</h2>
    <table>
      <tr><th>Tipo de tarea</th><th>IA</th><th>N</th><th>Coste medio</th><th>Duración media</th></tr>
      {filas_tarea or '<tr><td colspan="5">Sin datos todavía.</td></tr>'}
    </table>
    </body></html>"""
