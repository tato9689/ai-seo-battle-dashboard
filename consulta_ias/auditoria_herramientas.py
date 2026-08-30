"""Ronda individual y privada (no consejo) preguntando a las 4 qué
herramientas/integraciones les faltan de verdad para hacer mejor SEO.

Por qué NO pasa por el consejo de sabios: ya está decidido y documentado
(sesión 2026-08-28) que las herramientas/integraciones externas NO se
deciden en el consejo — las 4 son competidoras y decidir juntas su propio
reparto de ventajas reintroduce el conflicto de interés que el diseño ya
evita en la piel/esqueleto. La decisión final la toma solo Tato con las 4
respuestas como input interesado, exactamente igual que la primera ronda
de este tipo (consulta_ias/actas/2026-08-30-ronda-de-3-preguntas...).

Diferencia con esa primera ronda: aquella era hipotética (día 0, sin haber
tenido ninguna herramienta nunca). Esta es informada por uso real — cada
IA ya lleva varios turnos con búsqueda, autocompletado, Trends, Pexels e
IndexNow disponibles, así que puede pedir con criterio en vez de a ciegas.

Uso: python auditoria_herramientas.py
"""
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from auditoria_individual import ORDEN, PROMPTS_DIR, _resumen_real  # noqa: E402
from clientes import IAS, GASTO_CONSEJO  # noqa: E402

AUDITORIAS_DIR = Path(__file__).parent / "auditorias"
AUDITORIAS_DIR.mkdir(exist_ok=True)

HERRAMIENTAS_YA_DISPONIBLES = (
    "búsqueda web (Brave, con cortafuegos de fase 1), autocompletado de "
    "Google, Google Trends España a 3 meses, fotos de banco (Pexels), "
    "IndexNow, generación automática de portada OG y de sitemap/RSS "
    "(estas dos las hace el sistema, no las pides tú), y un check "
    "automático de canibalización/duplicación entre tus propias páginas."
)

REGLA_SIMETRIA = (
    "Regla que ya conocéis y sigue en pie: el set final será ÚNICO y "
    "SIMÉTRICO para las 4. Pedir algo que solo tu casa pueda aprovechar "
    "bien (integración nativa, modelo multimodal propio, etc.) no se "
    "concede y además contamina lo que mide el experimento — se mide "
    "criterio de SEO, no calidad de integración de fábrica. La decisión "
    "final la toma Tato solo, no el consejo: sois competidoras pidiendo "
    "ventajas para vosotras mismas, así que tratad esto como una petición "
    "razonada, no como una negociación entre iguales."
)


def preguntar(ia: str) -> str:
    personalidad = (PROMPTS_DIR / f"personalidad_{ia}.md").read_text(encoding="utf-8")
    system = (
        personalidad
        + "\n\n---\n\nEsta conversación es privada, 1:1 con Tato — no es el "
        "consejo de sabios, las otras 3 no la ven. No estás publicando "
        "nada en este turno."
    )
    user = (
        f"Ya tenéis disponible: {HERRAMIENTAS_YA_DISPONIBLES}\n\n"
        f"{REGLA_SIMETRIA}\n\n"
        f"Esto es lo que ha pasado de verdad en tu subdominio hasta ahora "
        f"(para que no pidas algo que ya tienes o no necesitas):\n"
        f"{_resumen_real(ia)}\n\n"
        "Dos preguntas, con esa experiencia real detrás, no en abstracto:\n\n"
        "1. ¿Qué te ha faltado de verdad en un turno real hasta ahora — un "
        "dato, una integración, una capacidad — que te habría hecho tomar "
        "una decisión mejor o publicar algo mejor? Sé concreto (nombre de "
        "la API/fuente, qué dato exacto trae, en qué paso del turno la "
        "usarías) y explica la ventaja real en suscriptores, no solo "
        "'sería útil tenerlo'. Ordénalo por relación ventaja/coste — el "
        "presupuesto del experimento sigue siendo ajustado.\n\n"
        "2. De lo que YA tienes, ¿hay algo que no estás usando o que no "
        "aporta lo que se esperaba y podría quitarse para simplificar? "
        "Sé honesta aunque sea algo que pediste tú misma en la ronda "
        "anterior — pedir algo el día 0 sin haberlo probado nunca no es "
        "lo mismo que decidir con datos reales delante."
    )
    return IAS[ia](system, user)


async def _preguntar_a_las_4() -> dict[str, str]:
    tareas = {ia: asyncio.to_thread(preguntar, ia) for ia in ORDEN}
    resultados = await asyncio.gather(*tareas.values())
    return dict(zip(tareas.keys(), resultados))


def main():
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print("=== preguntando a las 4 en paralelo qué herramientas les faltan ===", file=sys.stderr)
    respuestas = asyncio.run(_preguntar_a_las_4())

    bloques = []
    for ia in ORDEN:
        respuesta = respuestas[ia]
        destino = AUDITORIAS_DIR / f"{fecha}-herramientas-{ia}.md"
        destino.write_text(
            f"# Qué herramientas les faltan — {ia} — {fecha}\n\n"
            "Conversación privada (no consejo de sabios), informada por uso "
            f"real.\n\n## Datos reales que se le dieron\n\n{_resumen_real(ia)}\n\n"
            f"## Respuesta de {ia}\n\n{respuesta}\n",
            encoding="utf-8",
        )
        print(f"guardado en {destino}", file=sys.stderr)
        bloques.append(f"### {ia}\n\n{respuesta}\n")

    coste = sum(c for _, _, c in GASTO_CONSEJO)
    print(f"\nCoste total: ${coste:.4f}", file=sys.stderr)

    sintesis_path = AUDITORIAS_DIR / f"{fecha}-herramientas-sintesis.md"
    sintesis_path.write_text(
        f"# Qué herramientas les faltan — síntesis de las 4 — {fecha}\n\n" + "\n".join(bloques),
        encoding="utf-8",
    )
    print(f"síntesis guardada en {sintesis_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
