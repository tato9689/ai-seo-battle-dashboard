"""Mesa redonda puntual entre las 4 IAs. Tres modos de consulta:

  paralelo  las 4 responden a la vez, sin verse — mide el instinto de cada
            una sin que el orden influya. Buena ronda 1.
  turnos    secuencial, cada IA ve lo que respondieron las anteriores en la
            misma ronda antes de contestar — debate real, pero con sesgo
            posicional (quien habla último tiene más contexto).
  mixto     (default) ronda 1 en paralelo, rondas siguientes en turnos con
            el orden rotado cada ronda para no favorecer siempre a la misma.
  checkpoint  como paralelo, pero cada IA además puntúa (1-10) las propuestas
            de las otras 3 en un bloque JSON al final de su respuesta, para
            medir consenso real entre modelos. Pensado para post-mortems en
            los checkpoints del experimento (semana 5, cierre), no para
            decisiones de producción normales como el dominio.

Uso: python debate.py "pregunta" [rondas] [paralelo|turnos|mixto|checkpoint]

No es parte del experimento (que sigue aislado en fase 1) — es una
herramienta de producción bajo demanda para que Tato decida con su input.
Cada ejecución genera un acta en markdown en actas/, versionable en el repo.
"""
import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from clientes import IAS

ACTAS_DIR = Path(__file__).parent / "actas"

SYSTEM = (
    "Participas en una consulta puntual entre 4 modelos de IA (Claude, GPT, "
    "Gemini, DeepSeek) para ayudar a Tato a decidir algo del proyecto AI SEO "
    "Battle. Sé conciso: propuesta concreta + justificación breve, sin "
    "repetir lo ya dicho por otras salvo para matizarlo o discrepar."
)

SYSTEM_CHECKPOINT = (
    "Participas en un checkpoint de post-mortem entre 4 modelos de IA (Claude, "
    "GPT, Gemini, DeepSeek) del experimento AI SEO Battle. Te damos tus propios "
    "resultados reales hasta ahora. Analiza qué ha funcionado y qué no, en 3-5 "
    "frases. Después de tu análisis, en la última línea añade un bloque de "
    "código ```json con este formato exacto, puntuando del 1 al 10 la "
    "estrategia de las OTRAS tres IAs (nunca la tuya propia):\n"
    '```json\n{"puntuaciones": {"ia_x": N, "ia_y": N, "ia_z": N}}\n```'
)

ORDEN_BASE = ["claude", "gpt", "gemini", "deepseek"]


async def _ronda_paralela(contexto: str, system: str = SYSTEM) -> dict[str, str]:
    tareas = {ia: asyncio.to_thread(func, system, contexto) for ia, func in IAS.items()}
    resultados = await asyncio.gather(*tareas.values())
    return dict(zip(tareas.keys(), resultados))


def ronda_paralela(contexto: str, system: str = SYSTEM) -> dict[str, str]:
    return asyncio.run(_ronda_paralela(contexto, system))


def extraer_puntuaciones(texto: str) -> dict | None:
    """Busca un bloque ```json {"puntuaciones": {...}} al final de la
    respuesta. Tolerante a fallos: si no lo encuentra o no parsea, None."""
    m = re.search(r"```json\s*(\{.*?\})\s*```", texto, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
        return data.get("puntuaciones")
    except (json.JSONDecodeError, AttributeError):
        return None


def ronda_turnos(contexto: str, orden: list[str]) -> tuple[dict[str, str], str]:
    respuestas = {}
    ctx = contexto
    for ia in orden:
        r = IAS[ia](SYSTEM, ctx)
        respuestas[ia] = r
        ctx += f"\n\n--- {ia} respondió ---\n{r}"
    return respuestas, ctx


def _orden_rotado(n_ronda: int) -> list[str]:
    i = (n_ronda - 1) % len(ORDEN_BASE)
    return ORDEN_BASE[i:] + ORDEN_BASE[:i]


def _formatear_ronda(acta_md: list, n_ronda: int, etiqueta: str, orden: list[str], respuestas: dict[str, str]):
    acta_md.append(f"## Ronda {n_ronda} ({etiqueta}, orden: {' → '.join(orden)})")
    for ia in orden:
        acta_md.append(f"\n**{ia}:**\n\n{respuestas[ia]}\n")


def debate(pregunta: str, rondas: int = 2, modo: str = "mixto") -> Path:
    assert modo in {"paralelo", "turnos", "mixto", "checkpoint"}
    acta_md = [f"# Consulta: {pregunta}", "", f"_{datetime.now(timezone.utc).isoformat()} · modo: {modo}_", ""]
    contexto = pregunta
    puntuaciones_por_ia: dict[str, dict] = {}

    if modo == "checkpoint":
        respuestas = ronda_paralela(contexto, system=SYSTEM_CHECKPOINT)
        _formatear_ronda(acta_md, 1, "checkpoint", ORDEN_BASE, respuestas)
        for ia, texto in respuestas.items():
            puntos = extraer_puntuaciones(texto)
            if puntos:
                puntuaciones_por_ia[ia] = puntos

        if puntuaciones_por_ia:
            acta_md.append("\n## Consenso (puntuación 1-10 a la estrategia de las otras)\n")
            acta_md.append("| puntúa \\ recibe | " + " | ".join(ORDEN_BASE) + " |")
            acta_md.append("|" + "---|" * (len(ORDEN_BASE) + 1))
            for evaluador in ORDEN_BASE:
                fila = [str(puntuaciones_por_ia.get(evaluador, {}).get(evaluado, "–")) for evaluado in ORDEN_BASE]
                acta_md.append(f"| {evaluador} | " + " | ".join(fila) + " |")
    else:
        for n_ronda in range(1, rondas + 1):
            usar_paralelo = modo == "paralelo" or (modo == "mixto" and n_ronda == 1)
            if usar_paralelo:
                respuestas = ronda_paralela(contexto)
                _formatear_ronda(acta_md, n_ronda, "paralelo", ORDEN_BASE, respuestas)
                contexto += "\n\n" + "\n".join(f"--- {ia} respondió ---\n{r}" for ia, r in respuestas.items())
            else:
                orden = _orden_rotado(n_ronda)
                respuestas, contexto = ronda_turnos(contexto, orden)
                _formatear_ronda(acta_md, n_ronda, "turnos", orden, respuestas)

    slug = "".join(c if c.isalnum() else "-" for c in pregunta.lower())[:50].strip("-")
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ACTAS_DIR.mkdir(exist_ok=True)
    path = ACTAS_DIR / f"{fecha}-{slug}.md"
    path.write_text("\n".join(acta_md), encoding="utf-8")
    return path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Uso: python debate.py "pregunta para las 4 IAs" [rondas] [paralelo|turnos|mixto|checkpoint]')
        sys.exit(1)
    pregunta = sys.argv[1]
    rondas = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    modo = sys.argv[3] if len(sys.argv) > 3 else "mixto"
    path = debate(pregunta, rondas, modo)
    print(f"Acta guardada en {path}")
