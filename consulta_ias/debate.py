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
            los checkpoints del experimento (mes 5, cierre), no para
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

from clientes import IAS, GASTO_CONSEJO

ACTAS_DIR = Path(__file__).parent / "actas"

SYSTEM = (
    "Participas en una consulta puntual entre 4 modelos de IA (Claude, GPT, "
    "Gemini, DeepSeek) para ayudar a Tato a decidir algo del proyecto AI SEO "
    "Battle. Sé conciso: propuesta concreta + justificación breve, sin "
    "repetir lo ya dicho por otras salvo para matizarlo o discrepar."
)

NOMBRES = {"claude": "Claude", "gpt": "GPT", "gemini": "Gemini", "deepseek": "DeepSeek"}

# Decirle a cada modelo cuál de los cuatro es. Parece obvio y faltaba: el
# system solo decía "participas en una consulta entre 4 modelos" sin nombrar
# a ninguno, y en el consejo del 2026-09-02 Gemini abrió su respuesta de la
# ronda 1 con "Soy DeepSeek" y la de la ronda 3 con "Soy GPT". El acta
# atribuye por la API que hizo la llamada, así que el texto era suyo — pero
# quedaba un acta donde una IA se presenta como otra, que es exactamente lo
# que el proyecto no se puede permitir publicar. En rondas por turnos el
# contexto llega lleno de "--- gpt respondió ---", y un modelo al que nadie
# le ha dicho quién es acaba adoptando una de las etiquetas que ve.
IDENTIDAD = (
    "Eres {nombre}. Los otros tres participantes son {otros}. Hablas siempre "
    "en primera persona como {nombre} y no te presentas como ningún otro "
    "modelo: el acta pública te atribuye por la API que te llamó, así que "
    "decir que eres otro deja el acta mintiendo. No empieces tu respuesta "
    "presentándote."
)


def con_identidad(base) -> dict[str, str]:
    """El system de cada IA con su nombre delante. Acepta una cadena (la
    misma base para las 4) o un dict {ia: system} ya personalizado."""
    salida = {}
    for ia, nombre in NOMBRES.items():
        otros = ", ".join(n for i, n in NOMBRES.items() if i != ia)
        cabecera = IDENTIDAD.format(nombre=nombre, otros=otros)
        salida[ia] = cabecera + "\n\n" + (base[ia] if isinstance(base, dict) else base)
    return salida

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


def _system_de(system, ia: str) -> str:
    """El system puede ser una cadena (la misma para las 4, el caso normal) o
    un dict {ia: system} cuando cada una debe responder COMO ELLA MISMA, con
    su propia personalidad delante. Lo segundo hace falta para encargos donde
    la respuesta depende del nicho y el tono de cada agente — sin esto, las 4
    contestan como modelos genéricos y el encargo pierde el sentido."""
    return system[ia] if isinstance(system, dict) else system


async def _ronda_paralela(contexto: str, system=SYSTEM) -> dict[str, str]:
    tareas = {ia: asyncio.to_thread(func, _system_de(system, ia), contexto) for ia, func in IAS.items()}
    resultados = await asyncio.gather(*tareas.values())
    return dict(zip(tareas.keys(), resultados))


def ronda_paralela(contexto: str, system=SYSTEM) -> dict[str, str]:
    return asyncio.run(_ronda_paralela(contexto, system))


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts-sistema"


def system_con_personalidad() -> dict[str, str]:
    """Un system por IA: su propia personalidad + el encargo del consejo. NO
    incluye `base_comun.md` a propósito: son 5.300 palabras que se pagan por
    las 4 y cuyo contenido (guardarraíles, formato de salida) no cambia lo
    que se pregunta aquí. La personalidad sí, porque lleva el nicho."""
    salida = {}
    for ia in ORDEN_BASE:
        personalidad = (PROMPTS_DIR / f"personalidad_{ia}.md").read_text(encoding="utf-8")
        salida[ia] = (
            personalidad
            + "\n\n---\n\n"
            + "Además de lo anterior, que sigue siendo quien eres: participas en una "
            "consulta puntual del proyecto AI SEO Battle para ayudar a Tato a decidir. "
            "Responde COMO TÚ MISMA, desde tu nicho y tu personalidad. Sigues en fase 1: "
            "no menciones ni intentes deducir a las otras tres IAs."
        )
    return salida


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


def ronda_turnos(contexto: str, orden: list[str], system=SYSTEM) -> tuple[dict[str, str], str]:
    """El `system` era el global fijo y no un parámetro: cualquier modo que
    personalizara el system lo perdía en cuanto la ronda dejaba de ser
    paralela, en silencio y sin que el acta lo dijera."""
    respuestas = {}
    ctx = contexto
    for ia in orden:
        r = IAS[ia](_system_de(system, ia), ctx)
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
    assert modo in {"paralelo", "turnos", "mixto", "checkpoint", "personal"}
    if modo == "personal":
        # Cada IA responde como ella misma y sin ver a las demás. Una sola
        # ronda, siempre: en cuanto hay ronda 2 cada una lee las respuestas
        # de las otras, y una respuesta anclada en el nicho revela el nicho.
        # Eso rompería la fase ciega, así que aquí no es configurable.
        rondas = 1
    acta_md = [f"# Consulta: {pregunta}", "", f"_{datetime.now(timezone.utc).isoformat()} · modo: {modo}_", ""]
    contexto = pregunta
    puntuaciones_por_ia: dict[str, dict] = {}

    if modo == "checkpoint":
        respuestas = ronda_paralela(contexto, system=con_identidad(SYSTEM_CHECKPOINT))
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
            usar_paralelo = modo in ("paralelo", "personal") or (modo == "mixto" and n_ronda == 1)
            if usar_paralelo:
                sistema = system_con_personalidad() if modo == "personal" else SYSTEM
                respuestas = ronda_paralela(contexto, con_identidad(sistema))
                etiqueta = "paralelo, cada una como ella misma" if modo == "personal" else "paralelo"
                _formatear_ronda(acta_md, n_ronda, etiqueta, ORDEN_BASE, respuestas)
                contexto += "\n\n" + "\n".join(f"--- {ia} respondió ---\n{r}" for ia, r in respuestas.items())
            else:
                orden = _orden_rotado(n_ronda)
                respuestas, contexto = ronda_turnos(contexto, orden, con_identidad(SYSTEM))
                _formatear_ronda(acta_md, n_ronda, "turnos", orden, respuestas)

    if GASTO_CONSEJO:
        total = sum(c for _, _, c in GASTO_CONSEJO)
        acta_md.append("\n## Coste real de este consejo\n")
        for ia, modelo, coste in GASTO_CONSEJO:
            acta_md.append(f"- {ia} ({modelo}): ${coste:.4f}")
        acta_md.append(f"\n**Total: ${total:.4f}**")

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
    if GASTO_CONSEJO:
        print(f"Coste real de este consejo: ${sum(c for _, _, c in GASTO_CONSEJO):.4f}")
