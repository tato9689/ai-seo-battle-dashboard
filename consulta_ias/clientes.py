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

TIMEOUT = 60

# Modelo por defecto (el que ya usaba consulta_ias) y variante barata para
# la tarea diaria rutinaria (ver prompts-sistema/README.md, tiering por
# tarea). Nombres de la variante barata de GPT/Gemini son la mejor
# estimación a fecha de este diseño — verificar el nombre exacto vigente
# al dar de alta las 4 cuentas este finde, pueden haber cambiado.
MODELOS = {
    "claude": {"diaria": "claude-haiku-4-5-20251001", "semanal": "claude-sonnet-5"},
    "gpt": {"diaria": "gpt-5.2-mini", "semanal": "gpt-5.2"},
    "gemini": {"diaria": "gemini-3.7-flash", "semanal": "gemini-3.7-flash"},
    "deepseek": {"diaria": "deepseek-chat", "semanal": "deepseek-reasoner"},
}


def _falta_key(nombre_env: str) -> str | None:
    if not os.environ.get(nombre_env):
        return f"[sin {nombre_env} configurada]"
    return None


def _llamar_claude_meta(system: str, user: str, modelo: str) -> dict:
    if err := _falta_key("ANTHROPIC_API_KEY"):
        return {"texto": err, "tokens_in": None, "tokens_out": None, "duracion_seg": None, "modelo": modelo}
    t0 = time.monotonic()
    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={"model": modelo, "max_tokens": 2048, "system": system, "messages": [{"role": "user", "content": user}]},
        timeout=TIMEOUT,
    )
    duracion = time.monotonic() - t0
    resp.raise_for_status()
    data = resp.json()
    usage = data.get("usage", {})
    return {
        "texto": data["content"][0]["text"],
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
    resp = httpx.post(
        url,
        headers={"Authorization": f"Bearer {os.environ[header_key]}"},
        json={"model": modelo, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
        timeout=TIMEOUT,
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


def _llamar_gemini_meta(system: str, user: str, modelo: str) -> dict:
    if err := _falta_key("GOOGLE_API_KEY"):
        return {"texto": err, "tokens_in": None, "tokens_out": None, "duracion_seg": None, "modelo": modelo}
    t0 = time.monotonic()
    resp = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
        headers={"x-goog-api-key": os.environ["GOOGLE_API_KEY"]},
        json={
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
        },
        timeout=TIMEOUT,
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
    "gpt": lambda system, user, modelo: _llamar_openai_compat(
        "https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY", system, user, modelo
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


# --- wrappers de solo texto, usados por consulta_ias/debate.py (consejo de sabios) ---

def llamar_claude(system: str, user: str) -> str:
    return llamar_con_metadata("claude", system, user, tier="semanal")["texto"]


def llamar_gpt(system: str, user: str) -> str:
    return llamar_con_metadata("gpt", system, user, tier="semanal")["texto"]


def llamar_gemini(system: str, user: str) -> str:
    return llamar_con_metadata("gemini", system, user, tier="semanal")["texto"]


def llamar_deepseek(system: str, user: str) -> str:
    return llamar_con_metadata("deepseek", system, user, tier="semanal")["texto"]


IAS = {
    "claude": llamar_claude,
    "gpt": llamar_gpt,
    "gemini": llamar_gemini,
    "deepseek": llamar_deepseek,
}
