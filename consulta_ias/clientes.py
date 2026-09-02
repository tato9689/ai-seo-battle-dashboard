"""Wrappers mínimos para llamar a las 4 APIs con el mismo prompt.

Dos capas: `llamar_<ia>(system, user)` devuelve solo texto — la usa
consulta_ias/debate.py para el consejo de sabios. `llamar_con_metadata(ia,
system, user, modelo=None)` devuelve además tokens/duración reales — la usa
cron_agente.py para poblar el activity_log con datos de verdad, no
inventados. Las keys se leen de variables de entorno, ninguna se guarda en
disco.
"""
import os
import sys
import time

import httpx

# 900 y no 300: desde que los encargos del consejo dejaron de llevar límite
# de extensión, una respuesta larga de un modelo que razona antes de escribir
# se pasa de 5 minutos y muere por timeout de red — pasó con Claude el
# 2026-09-01 en el encargo del agente de diseño, con las otras 3 ya pagadas.
TIMEOUT = 900

# Precios (entrada, salida) en USD por millón de tokens, CONTRASTADOS con la
# documentación oficial de los 4 proveedores el 2026-08-29. Vive aquí (y no
# en cron_agente.py, donde nació) porque consulta_ias/debate.py — el consejo
# de sabios — también necesita saber cuánto cuesta cada llamada, sobre todo
# en el tier "consejo": es el más caro con diferencia (gpt-5.5-pro a 180
# $/M tokens de salida) y el que se dispara a mano sin freno de presupuesto
# diario. Se acabaron 10$ de crédito real de OpenAI el 2026-08-30 sin que
# nada lo avisara con tiempo — motivo de este cambio.
PRECIOS_APROX_POR_M_TOKENS = {
    # Anthropic — precios de la referencia oficial de la API.
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-opus-5": (5.0, 25.0),
    # OpenAI — developers.openai.com/api/docs/pricing.
    "gpt-5.4-mini": (0.75, 4.5),
    "gpt-5.4": (2.5, 15.0),
    "gpt-5.5-pro-2026-04-23": (30.0, 180.0),
    # Google — ai.google.dev/gemini-api/docs/pricing. Flash tiene precio
    # promocional hasta el 31/12/2026 (después dobla): el experimento acaba
    # mucho antes, pero conviene saberlo si se alarga.
    "gemini-3.1-flash-lite": (0.25, 1.5),
    "gemini-3.7-flash": (0.75, 3.75),
    "gemini-3.1-pro-preview": (2.0, 12.0),
    # DeepSeek — api-docs.deepseek.com. Tiene tarifa punta y valle (la valle
    # es la mitad); se apuntan los precios de PUNTA a propósito, porque
    # sobreestimar el gasto es el error barato en un freno de presupuesto.
    # Horas punta: 01:00-04:00 y 06:00-10:00 UTC de lunes a viernes.
    "deepseek-v4-flash": (0.44, 1.32),
    "deepseek-v4-pro": (1.32, 3.96),
}


def precio_de(modelo: str) -> tuple[float, float] | None:
    """Precio del modelo, tolerando los snapshots con fecha.

    Las APIs devuelven el snapshot exacto que sirvieron (`gpt-5.4-mini` llega
    como `gpt-5.4-mini-2026-03-17`), y buscarlo tal cual en la tabla no
    encontraba nada: el coste salía `None` y el freno de presupuesto se
    quedaba ciego para ese agente sin que nada lo avisara. Se busca primero
    la coincidencia exacta y luego el nombre base más largo que encaje.
    """
    if not modelo:
        return None
    if modelo in PRECIOS_APROX_POR_M_TOKENS:
        return PRECIOS_APROX_POR_M_TOKENS[modelo]
    candidatos = [k for k in PRECIOS_APROX_POR_M_TOKENS if modelo.startswith(k)]
    if not candidatos:
        return None
    # El más largo evita que "gpt-5.4" se lleve lo que es de "gpt-5.4-mini".
    return PRECIOS_APROX_POR_M_TOKENS[max(candidatos, key=len)]


def coste_estimado(modelo: str, tokens_in: int | None, tokens_out: int | None) -> float | None:
    precio = precio_de(modelo)
    if precio is None:
        # Avisar en voz alta: un modelo sin precio no suma al gasto, y el
        # freno de presupuesto (o el consejo) lo daría por gratis indefinidamente.
        print(f"AVISO: sin precio para {modelo!r}, esta llamada no cuenta para el gasto", file=sys.stderr)
        return None
    if tokens_in is None or tokens_out is None:
        return None
    precio_in, precio_out = precio
    return round(tokens_in / 1_000_000 * precio_in + tokens_out / 1_000_000 * precio_out, 6)

# La API de Anthropic exige max_tokens explícito; OpenAI, Gemini y DeepSeek no
# lo piden y sirven su máximo por defecto. Estaba en 2048, que da para una
# respuesta de consejo pero NO para un turno de agente: escribir un index.html
# entera más un artículo se pasa de ahí, la respuesta llega cortada y el bloque
# JSON final no parsea. Es un fallo doble — el turno de Claude se pierde, y
# además Claude compite con un techo de salida que las otras tres no tienen.
#
# Subido de 16000 a 32000 el 2026-08-30 noche: volvió a pasar de verdad tras
# ampliar bastante base_comun.md (checklist de publicación, diseño con
# intención, anti-muletillas de IA...) — un turno real de Claude gastó 14562
# de los 16000 solo en razonamiento y se quedó sin espacio para el JSON.
# Deepseek y Gemini completaron turnos comparables con 21556 y 7563 tokens
# sin límite explícito, así que el problema es específico de este tope, no
# del tamaño del prompt en sí. Margen amplio a propósito: este límite ya
# mordió dos veces por quedarse corto, más vale pasarse que repetirlo.
MAX_SALIDA = 32000

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
    # Anthropic no publica variante fechada de la familia 5 (comprobado en
    # /v1/models el 2026-08-30: claude-sonnet-5 y claude-opus-5 solo existen
    # como alias; los únicos ids con fecha son de la familia 4.x). El diario
    # sí queda fijado porque haiku 4.5 sí la tiene. Para lo demás, la red es
    # el aviso de cambio de modelo servido que hace cron_agente.py.
    "claude": {
        "diaria": "claude-haiku-4-5-20251001",
        "semanal": "claude-sonnet-5",
        "consejo": "claude-opus-5",
    },
    "gpt": {
        # gpt-5.2-mini NO EXISTE (404 en la API): habría hecho fallar todas
        # las ejecuciones diarias de GPT. Se pasa a la familia 5.4, que tiene
        # las dos variantes de la misma generación.
        # Snapshots fechados, no alias: el experimento dura 10 meses y si
        # OpenAI mueve `gpt-5.4-mini` a mitad de camino, la comparación
        # antes/después del checkpoint deja de medir lo mismo. Verificados
        # contra /v1/models el 2026-08-30.
        "diaria": "gpt-5.4-mini-2026-03-17",
        "semanal": "gpt-5.4-2026-03-05",
        # Bajado de gpt-5.5-pro (30/180 $/M, el más caro de los 12) a
        # gpt-5.4 (2.5/15.0) el 2026-08-30: gpt-5.5-pro se comió 10$ de
        # crédito real de OpenAI en un puñado de consultas del consejo y
        # dejó la cuenta a cero (insufficient_quota). Sigue siendo el
        # flagship de la casa, solo que el de coste contenido en vez del
        # más caro del catálogo — mismo modelo que "semanal".
        "consejo": "gpt-5.4-2026-03-05",
    },
    # Google tampoco da ids fechados en su ListModels (verificado el
    # 2026-08-30): gemini-3.7-flash y gemini-3.1-* son alias movibles. Mismo
    # apaño que en Claude: se vigila el modelo que devuelve la API.
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
        # Crédito agotado: es un 429 pero reintentar con backoff no lo
        # arregla nunca (pasó el 2026-08-30, 4 intentos reales sin cambiar
        # nada). Se detecta por el cuerpo, no solo el código, y se corta ya.
        if resp.status_code == 429 and "insufficient_quota" in resp.text:
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
# sabios) — tier "consejo": el modelo más potente (de coste contenido) de
# cada casa, ver MODELOS ---

# Gasto real del consejo en curso, para que quede visible en la consola y en
# el acta — antes no se veía nada hasta que la cuenta se quedaba a cero
# (pasó el 2026-08-30 con gpt-5.5-pro). Se reinicia cada vez que se importa
# el módulo, o sea una vez por ejecución de debate.py: es justo lo que se
# quiere medir, el coste de ESE consejo.
GASTO_CONSEJO: list[tuple[str, str, float]] = []  # (ia, modelo, coste_usd)


def _llamar_consejo(ia: str, system: str, user: str) -> str:
    """Wrapper de una IA para el consejo: nunca deja que un fallo de ESTA
    IA (cuenta sin crédito, 5xx persistente) tire las respuestas de las
    otras 3, que ya están pagadas. Antes una excepción aquí reventaba el
    `asyncio.gather` entero y no se guardaba ni una sola acta — pasó tres
    veces el 2026-08-30 con las otras 3 ya respondidas y pagadas."""
    try:
        resultado = llamar_con_metadata(ia, system, user, tier="consejo")
    except httpx.HTTPStatusError as e:
        return f"[error de {ia} ({e.response.status_code}): {e.response.text[:200]}]"
    except httpx.RequestError as e:
        return f"[error de red llamando a {ia}: {e}]"
    coste = coste_estimado(resultado["modelo"], resultado.get("tokens_in"), resultado.get("tokens_out"))
    if coste is not None:
        GASTO_CONSEJO.append((ia, resultado["modelo"], coste))
        print(f"[{ia}] {resultado['modelo']}: ${coste:.4f} "
              f"({resultado.get('tokens_in')} in / {resultado.get('tokens_out')} out)", file=sys.stderr)
    return resultado["texto"]


def llamar_claude(system: str, user: str) -> str:
    return _llamar_consejo("claude", system, user)


def llamar_gpt(system: str, user: str) -> str:
    return _llamar_consejo("gpt", system, user)


def llamar_gemini(system: str, user: str) -> str:
    return _llamar_consejo("gemini", system, user)


def llamar_deepseek(system: str, user: str) -> str:
    return _llamar_consejo("deepseek", system, user)


IAS = {
    "claude": llamar_claude,
    "gpt": llamar_gpt,
    "gemini": llamar_gemini,
    "deepseek": llamar_deepseek,
}
