"""Wrappers mínimos para llamar a las 4 APIs con el mismo prompt.

Dos capas: `llamar_<ia>(system, user)` devuelve solo texto — la usa
consulta_ias/debate.py para el consejo de sabios. `llamar_con_metadata(ia,
system, user, modelo=None)` devuelve además tokens/duración reales — la usa
cron_agente.py para poblar el activity_log con datos de verdad, no
inventados. Las keys se leen de variables de entorno, ninguna se guarda en
disco.
"""
import os
import time

import httpx

TIMEOUT = 300

# La API de Anthropic exige max_tokens explícito; OpenAI, Gemini y DeepSeek no
# lo piden y sirven su máximo por defecto. Estaba en 2048, que da para una
# respuesta de consejo pero NO para un turno de agente: escribir un index.html
# entera más un artículo se pasa de ahí, la respuesta llega cortada y el bloque
# JSON final no parsea. Es un fallo doble — el turno de Claude se pierde, y
# además Claude compite con un techo de salida que las otras tres no tienen.
MAX_SALIDA = 16000

# Tres tiers: "diaria" (barato, tarea rutinaria de cron), "semanal"
# (flagship de coste contenido, para la newsletter semanal de cada agente)
# y "consejo" (el más potente de cada casa, solo para el consejo de sabios
# — decisiones puntuales no-cron como nombre de dominio o checkpoints, ver
# consulta_ias/debate.py). Nombres verificados en vivo contra el ListModels
# real de cada proveedor el 2026-08-29, no adivinados:
#   - Gemini: no hay "pro" estable con fecha en la línea 3.x todavía, solo
#     gemini-3.1-pro-preview (preview, floating). Se usa igualmente en
#     "consejo" porque esta herramienta la dispara Tato a mano y revisa el
#     resultado — el riesgo de un preview que cambie es aceptable aquí,
#     no en el cron diario desatendido (por eso "diaria"/"semanal" de
#     Gemini siguen en gemini-3.7-flash, estable y con fecha).
#   - GPT: gpt-5.5-pro-2026-04-23, el pro dated más reciente disponible.
#   - Claude: claude-opus-5, el flagship actual de Anthropic.
#   - DeepSeek: deepseek-reasoner ya es su tier más potente, sin cambio.
# Verificado contra la API de cada proveedor el 2026-08-29 (no de memoria).
# `diaria` y `semanal` son las dos opciones entre las que elige el propio
# agente ("barato" / "potente", ver presupuesto.py), así que **tienen que ser
# modelos distintos y con precios distintos**: si coinciden, ese agente no
# tiene ninguna decisión que tomar y el experimento deja de ser simétrico.
MODELOS = {
    "claude": {
        "diaria": "claude-haiku-4-5-20251001",
        "semanal": "claude-sonnet-5",
        "consejo": "claude-opus-5",
    },
    "gpt": {
        # gpt-5.2-mini NO EXISTE (404 en la API): habría hecho fallar todas
        # las ejecuciones diarias de GPT. Se pasa a la familia 5.4, que tiene
        # las dos variantes de la misma generación.
        "diaria": "gpt-5.4-mini",
        "semanal": "gpt-5.4",
        "consejo": "gpt-5.5-pro-2026-04-23",
    },
    "gemini": {
        # Antes ambas eran gemini-3.7-flash: Gemini no tenía elección posible.
        "diaria": "gemini-3.1-flash-lite",
        "semanal": "gemini-3.7-flash",
        "consejo": "gemini-3.1-pro-preview",
    },
    "deepseek": {
        # Los alias deepseek-chat y deepseek-reasoner sirven AMBOS
        # deepseek-v4-flash (comprobado mirando el modelo que devuelve la
        # API), así que tampoco tenía elección. Se usan los nombres reales.
        "diaria": "deepseek-v4-flash",
        "semanal": "deepseek-v4-pro",
        "consejo": "deepseek-v4-pro",
    },
}


def _post(url: str, headers: dict, cuerpo: dict) -> httpx.Response:
    """POST con reintentos ante 429 y 5xx. Un 503 puntual de un proveedor
    tiraba el consejo de sabios entero, incluidas las respuestas de las
    otras 3 ya pagadas (pasó el 2026-08-30 en la ronda 2). Los errores 4xx
    reales (key mala, modelo inexistente) no se reintentan: no van a
    arreglarse esperando."""
    resp = None
    for intento in range(4):
        resp = httpx.post(url, headers=headers, json=cuerpo, timeout=TIMEOUT)
        if resp.status_code != 429 and resp.status_code < 500:
            return resp
        if intento < 3:
            time.sleep(2 ** intento)
    return resp


def _falta_key(nombre_env: str) -> str | None:
    if not os.environ.get(nombre_env):
        return f"[sin {nombre_env} configurada]"
    return None


def _llamar_claude_meta(system: str, user: str, modelo: str) -> dict:
    if err := _falta_key("ANTHROPIC_API_KEY"):
        return {"texto": err, "tokens_in": None, "tokens_out": None, "duracion_seg": None, "modelo": modelo}
    t0 = time.monotonic()
    resp = _post(
        "https://api.anthropic.com/v1/messages",
        {
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        {"model": modelo, "max_tokens": MAX_SALIDA, "system": system, "messages": [{"role": "user", "content": user}]},
    )
    duracion = time.monotonic() - t0
    resp.raise_for_status()
    data = resp.json()
    usage = data.get("usage", {})
    # No se puede dar por hecho que content[0] sea el texto: los modelos con
    # razonamiento activado (Opus 5 lo trae de serie) devuelven primero un
    # bloque de pensamiento sin campo "text", y coger el índice 0 reventaba
    # con KeyError justo en el tier del consejo de sabios.
    texto = next(
        (b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"),
        "",
    )
    return {
        "texto": texto,
        "tokens_in": usage.get("input_tokens"),
        "tokens_out": usage.get("output_tokens"),
        "duracion_seg": round(duracion, 2),
        # data.get("model") es el snapshot que Anthropic sirvió de verdad;
        # si el alias pedido flota con el tiempo, esto guarda la realidad,
        # no lo que se pidió (ver punto 8 de la revisión de Claude Opus).
        "modelo": data.get("model", modelo),
    }


def _llamar_openai_compat(url: str, header_key: str, system: str, user: str, modelo: str) -> dict:
    """GPT y DeepSeek comparten el formato de API (chat/completions)."""
    if err := _falta_key(header_key):
        return {"texto": err, "tokens_in": None, "tokens_out": None, "duracion_seg": None, "modelo": modelo}
    t0 = time.monotonic()
    resp = _post(
        url,
        {"Authorization": f"Bearer {os.environ[header_key]}"},
        {"model": modelo, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
    )
    duracion = time.monotonic() - t0
    resp.raise_for_status()
    data = resp.json()
    usage = data.get("usage", {})
    return {
        "texto": data["choices"][0]["message"]["content"],
        "tokens_in": usage.get("prompt_tokens"),
        "tokens_out": usage.get("completion_tokens"),
        "duracion_seg": round(duracion, 2),
        # data.get("model") es el snapshot real servido por OpenAI/DeepSeek,
        # no el alias que se pidió (ambas APIs devuelven este campo).
        "modelo": data.get("model", modelo),
    }


def _llamar_gpt_responses_meta(system: str, user: str, modelo: str) -> dict:
    """Los modelos "pro" de OpenAI (gpt-5.5-pro y superiores) no están
    expuestos en /v1/chat/completions (da 404) — solo en /v1/responses, con
    formato de request/response distinto. Confirmado en vivo el 2026-08-29
    al dar de alta el tier "consejo"."""
    if err := _falta_key("OPENAI_API_KEY"):
        return {"texto": err, "tokens_in": None, "tokens_out": None, "duracion_seg": None, "modelo": modelo}
    t0 = time.monotonic()
    resp = _post(
        "https://api.openai.com/v1/responses",
        {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        {"model": modelo, "instructions": system, "input": user},
    )
    duracion = time.monotonic() - t0
    resp.raise_for_status()
    data = resp.json()
    texto = next(
        (
            c["text"]
            for item in data.get("output", [])
            if item.get("type") == "message"
            for c in item.get("content", [])
            if c.get("type") == "output_text"
        ),
        "",
    )
    usage = data.get("usage", {})
    return {
        "texto": texto,
        "tokens_in": usage.get("input_tokens"),
        "tokens_out": usage.get("output_tokens"),
        "duracion_seg": round(duracion, 2),
        "modelo": data.get("model", modelo),
    }


def _llamar_gemini_meta(system: str, user: str, modelo: str) -> dict:
    if err := _falta_key("GOOGLE_API_KEY"):
        return {"texto": err, "tokens_in": None, "tokens_out": None, "duracion_seg": None, "modelo": modelo}
    t0 = time.monotonic()
    resp = _post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
        {"x-goog-api-key": os.environ["GOOGLE_API_KEY"]},
        {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
        },
    )
    duracion = time.monotonic() - t0
    resp.raise_for_status()
    data = resp.json()
    usage = data.get("usageMetadata", {})
    return {
        "texto": data["candidates"][0]["content"]["parts"][0]["text"],
        "tokens_in": usage.get("promptTokenCount"),
        "tokens_out": usage.get("candidatesTokenCount"),
        "duracion_seg": round(duracion, 2),
        # modelVersion es el snapshot real servido por Gemini, no el alias pedido.
        "modelo": data.get("modelVersion", modelo),
    }


_LLAMADAS_META = {
    "claude": lambda system, user, modelo: _llamar_claude_meta(system, user, modelo),
    # Los modelos "pro" de OpenAI solo viven en /v1/responses (ver
    # _llamar_gpt_responses_meta) — el resto sigue por chat/completions.
    "gpt": lambda system, user, modelo: (
        _llamar_gpt_responses_meta(system, user, modelo)
        if "pro" in modelo
        else _llamar_openai_compat("https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY", system, user, modelo)
    ),
    "gemini": lambda system, user, modelo: _llamar_gemini_meta(system, user, modelo),
    "deepseek": lambda system, user, modelo: _llamar_openai_compat(
        "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY", system, user, modelo
    ),
}


def llamar_con_metadata(ia: str, system: str, user: str, tier: str = "diaria", modelo: str | None = None) -> dict:
    """tier: 'diaria' (variante barata) o 'semanal' (variante flagship,
    para la newsletter). `modelo` fuerza un modelo concreto si se pasa."""
    modelo = modelo or MODELOS[ia][tier]
    return _LLAMADAS_META[ia](system, user, modelo)


# --- wrappers de solo texto, usados por consulta_ias/debate.py (consejo de
# sabios) — tier "consejo": el modelo más potente de cada casa, ver MODELOS ---

def llamar_claude(system: str, user: str) -> str:
    return llamar_con_metadata("claude", system, user, tier="consejo")["texto"]


def llamar_gpt(system: str, user: str) -> str:
    return llamar_con_metadata("gpt", system, user, tier="consejo")["texto"]


def llamar_gemini(system: str, user: str) -> str:
    return llamar_con_metadata("gemini", system, user, tier="consejo")["texto"]


def llamar_deepseek(system: str, user: str) -> str:
    return llamar_con_metadata("deepseek", system, user, tier="consejo")["texto"]


IAS = {
    "claude": llamar_claude,
    "gpt": llamar_gpt,
    "gemini": llamar_gemini,
    "deepseek": llamar_deepseek,
}
