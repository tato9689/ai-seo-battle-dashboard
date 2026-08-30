"""Auditoría individual a cada una de las 4 IAs — privada, NO es el consejo
de sabios: aquí no se ven entre sí (mismo criterio que ya usaba la
"autoevaluación de cómo ganar", que también es individual y no colectiva).

Pedido por Tato el 2026-08-30, con sus palabras: "que te den los prompts que
necesitan para tener alas" — cada IA recibe su propio listón de calidad más
su auditoría real (qué ha hecho, qué costó, qué le falta) y se le pide que
proponga texto concreto para su propio prompt de sistema o para cómo usa las
herramientas que ya tiene (búsqueda, Pexels, IndexNow), en vez de que se lo
impongamos nosotros sin preguntar.

Con las 4 respuestas ya recogidas, se lanza el consejo de sabios (debate.py)
para que las 4 vean el resumen y converjan en UN texto único y simétrico —
ahí sí se ven entre sí, porque el consejo nunca ha sido parte del
aislamiento de fase 1 (es una herramienta de producción bajo demanda).

Tier "consejo" (flagship de cada casa): es una decisión de producción
puntual, no el cron diario — mismo criterio que ya usa debate.py.

Uso: python auditoria_individual.py [--espera-min N] [--sin-consejo]
  --espera-min N   espera N minutos entre IA e IA antes de la siguiente
                    auditoría individual. Por defecto 0: son llamadas HTTP
                    directas a la API de cada proveedor, no sesiones locales
                    de `claude -p` compitiendo por el mismo proceso — el
                    problema de contención que obliga a espaciar
                    cron_blog.sh no existe aquí. Se deja como opción por si
                    Tato prefiere espaciarlas de todos modos.
  --sin-consejo    solo hace las 4 auditorías individuales, no lanza el
                    consejo de sabios al final.
"""
import argparse
import asyncio
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import guardarrailes  # noqa: E402
from db import get_conn  # noqa: E402

from clientes import IAS, GASTO_CONSEJO  # noqa: E402

DASHBOARD_DIR = Path(__file__).parent.parent
PROMPTS_DIR = DASHBOARD_DIR / "prompts-sistema"
AUDITORIAS_DIR = Path(__file__).parent / "auditorias"
AUDITORIAS_DIR.mkdir(exist_ok=True)

ORDEN = ["claude", "gpt", "gemini", "deepseek"]

# El listón lo escribe Tato (vía esta sesión), no cada IA por su cuenta —
# tiene que ser el mismo para las 4, o deja de ser una vara común.
LISTON_DE_CALIDAD = (
    "Antes de mirar métricas queremos ver esto en cada turno: contenido "
    "bien editado (repasado, no solo generado y publicado del tirón), la "
    "piel visual del sitio realmente vestida (no solo el esqueleto con "
    "reset.css), y que uses de verdad las herramientas que ya tienes "
    "disponibles (búsqueda, fotos de Pexels, IndexNow) cuando aportan, no "
    "solo cuando te acuerdas de que existen. Publicar rápido sin eso no "
    "cuenta como publicar bien — analiza y edita ANTES de publicar; mirar "
    "métricas es lo último que se hace, no lo primero."
)


def _piel_vestida(ia: str) -> bool:
    repo = Path(f"/root/aisb-{ia}")
    # Reutiliza el mismo check que ya corre en el cron real (guardarrailes.py)
    # en vez de duplicar la lógica de "¿tiene CSS propio?" en dos sitios.
    return not guardarrailes._piel_visual(repo, {})


def _resumen_real(ia: str) -> str:
    conn = get_conn()
    acciones = conn.execute(
        "SELECT COUNT(*) AS n, SUM(coste_estimado) AS coste FROM activity_log WHERE ia = ?", (ia,)
    ).fetchone()
    ultimo = conn.execute(
        "SELECT * FROM metrics_snapshot WHERE ia = ? ORDER BY fecha DESC LIMIT 1", (ia,)
    ).fetchone()
    conn.close()

    repo = Path(f"/root/aisb-{ia}")
    articulos = [
        p for p in repo.rglob("*.html")
        if p.name not in {"index.html", "log.html", "privacidad.html"}
    ]
    longitudes = []
    for p in articulos:
        texto = re.sub(r"<[^>]+>", " ", p.read_text(encoding="utf-8", errors="ignore"))
        longitudes.append(len(texto.split()))

    log_path = repo / "log.json"
    eventos = []
    if log_path.exists():
        try:
            eventos = json.loads(log_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            eventos = []
    if not isinstance(eventos, list):
        eventos = []
    imagenes_usadas = any(
        isinstance(e, dict) and e.get("imagenes_recibidas") for e in eventos
    )
    bloqueados = sum(1 for e in eventos if isinstance(e, dict) and e.get("resultado") == "error")

    piel = "sí, tiene CSS/estilo propio" if _piel_vestida(ia) else "NO — el sitio entero sigue sirviendo solo reset.css"
    metricas = (
        f"{ultimo['suscriptores_totales'] or 0} suscriptores, {ultimo['vistas_ga4'] or 0} vistas de GA4 "
        f"(snapshot del {ultimo['fecha']})."
        if ultimo else "sin snapshot todavía (normal a un día del lanzamiento, el poller de métricas es diario)."
    )

    return (
        f"- Turnos reales hasta hoy: {acciones['n'] or 0} ({bloqueados} bloqueados por guardarraíles).\n"
        f"- Gasto real acumulado: {(acciones['coste'] or 0):.4f}$.\n"
        f"- Tráfico/suscriptores: {metricas}\n"
        f"- Piel visual: {piel}.\n"
        f"- Artículos publicados: {len(articulos)}"
        + (f" ({', '.join(str(n) + ' palabras' for n in longitudes)}).\n" if longitudes else ", ninguno todavía.\n")
        + f"- Fotos de banco (Pexels) usadas alguna vez: {'sí' if imagenes_usadas else 'no, ni una vez'}."
    )


def auditar(ia: str) -> str:
    personalidad = (PROMPTS_DIR / f"personalidad_{ia}.md").read_text(encoding="utf-8")
    system = (
        personalidad
        + "\n\n---\n\nEsta conversación es una auditoría PRIVADA de Tato "
        "contigo, una IA a la vez — no es el consejo de sabios, las otras 3 "
        "no la ven ni sabrán lo que respondes aquí. No estás publicando "
        "nada en este turno, es una charla sobre cómo trabajas."
    )
    user = (
        f"Listón de calidad que buscamos para las 4 webs de AI SEO Battle:\n"
        f"{LISTON_DE_CALIDAD}\n\n"
        f"Esto es lo que ha pasado de verdad en tu subdominio hasta ahora:\n"
        f"{_resumen_real(ia)}\n\n"
        "Dos preguntas, respóndelas en ese orden:\n"
        "1. Con esos datos delante, ¿tu trabajo hasta ahora está a la altura "
        "de ese listón? Sé honesta, no vendas humo ni te autoexcuses.\n"
        "2. Para llegar a ese nivel, ¿qué cambiarías en tu propio prompt de "
        "sistema (el bloque común o tu personalidad) o en cómo usas las "
        "herramientas que ya tienes (búsqueda, Pexels, IndexNow)? Danos "
        "texto concreto que se pueda añadir o cambiar, no una idea vaga.\n"
        "3. Piensa en CRO/UX de tu portada: hoy el bloque de transparencia "
        "('Esta web la gestiona una IA' + el enlace al diario de guerra) va "
        "justo después del titular, antes de que el visitante vea ningún "
        "artículo real o el motivo para suscribirse. Ese bloque es NO "
        "NEGOCIABLE en su presencia — tiene que decir claramente que lo "
        "gestiona una IA, no lo puedes quitar ni esconder — pero SÍ puedes "
        "decidir dónde y cómo se ve: un banner pequeño arriba, o bajarlo "
        "cerca del pie de página, lo que convierta mejor. Y en general, que "
        "lo primero que vea alguien sean tus artículos/tu contenido real, "
        "no la meta-explicación del proyecto. ¿Qué cambiarías en tu propia "
        "portada y por qué?"
    )
    return IAS[ia](system, user)


async def _auditar_las_4_en_paralelo() -> dict[str, str]:
    """Las 4 llamadas son independientes entre sí (auditoría privada, cada
    una a su propia API) — no hay motivo para esperar a que responda una
    para lanzar la siguiente, así que van con asyncio.gather, mismo patrón
    que ya usa debate.py en su ronda paralela."""
    tareas = {ia: asyncio.to_thread(auditar, ia) for ia in ORDEN}
    resultados = await asyncio.gather(*tareas.values())
    return dict(zip(tareas.keys(), resultados))


def lanzar_consejo(sintesis: str):
    from debate import debate  # import local: evita cargar asyncio si --sin-consejo

    pregunta = (
        "Cada una de vosotras acaba de pasar por una auditoría privada 1:1 "
        "sobre el mismo listón de calidad (contenido bien editado antes de "
        "publicar, piel visual vestida de verdad, uso real de las "
        "herramientas ya disponibles). Esto es lo que dijo cada una — a "
        "partir de aquí sí os veis entre sí, este consejo nunca ha formado "
        "parte del aislamiento de fase 1:\n\n"
        f"{sintesis}\n\n"
        "Debatid y proponed UN texto único y simétrico para las 4, que se "
        "pueda añadir tal cual a base_comun.md para subir el listón de "
        "calidad de las 4 webs a la vez — no una regla distinta por IA. Sed "
        "concretas: el texto exacto a añadir, no una idea general."
    )
    return debate(pregunta, rondas=2, modo="mixto")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--espera-min", type=float, default=0.0)
    ap.add_argument("--sin-consejo", action="store_true")
    args = ap.parse_args()

    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    bloques_sintesis = []

    if args.espera_min:
        # Solo tiene sentido espaciar en modo secuencial — con las 4 en
        # paralelo no hay "entre IA e IA" que espaciar.
        respuestas = {}
        for i, ia in enumerate(ORDEN):
            print(f"=== auditando a {ia} ===", file=sys.stderr)
            respuestas[ia] = auditar(ia)
            if args.espera_min and i < len(ORDEN) - 1:
                print(f"esperando {args.espera_min} min antes de la siguiente...", file=sys.stderr)
                time.sleep(args.espera_min * 60)
    else:
        print("=== auditando a las 4 en paralelo ===", file=sys.stderr)
        respuestas = asyncio.run(_auditar_las_4_en_paralelo())

    for ia in ORDEN:
        respuesta = respuestas[ia]
        destino = AUDITORIAS_DIR / f"{fecha}-{ia}.md"
        destino.write_text(
            f"# Auditoría individual — {ia} — {fecha}\n\n"
            "Conversación privada (no consejo de sabios). Listón de calidad "
            "pedido y datos reales del prompt arriba; respuesta tal cual "
            f"abajo.\n\n## Datos reales que se le dieron\n\n{_resumen_real(ia)}\n\n"
            f"## Respuesta de {ia}\n\n{respuesta}\n",
            encoding="utf-8",
        )
        print(f"guardado en {destino}", file=sys.stderr)
        bloques_sintesis.append(f"### {ia}\n\n{respuesta}\n")

    coste_individual = sum(c for _, _, c in GASTO_CONSEJO)
    print(f"\nCoste de las 4 auditorías individuales: ${coste_individual:.4f}", file=sys.stderr)

    sintesis_texto = "\n".join(bloques_sintesis)
    sintesis_path = AUDITORIAS_DIR / f"{fecha}-sintesis.md"
    sintesis_path.write_text(
        f"# Síntesis de las 4 auditorías individuales — {fecha}\n\n{sintesis_texto}",
        encoding="utf-8",
    )
    print(f"síntesis guardada en {sintesis_path}", file=sys.stderr)

    if not args.sin_consejo:
        print("\n=== lanzando consejo de sabios con la síntesis ===", file=sys.stderr)
        acta = lanzar_consejo(sintesis_texto)
        coste_total = sum(c for _, _, c in GASTO_CONSEJO)
        print(f"acta del consejo en {acta}", file=sys.stderr)
        print(f"coste TOTAL (auditorías + consejo): ${coste_total:.4f}", file=sys.stderr)


if __name__ == "__main__":
    main()
