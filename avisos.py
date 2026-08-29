"""Avisos por Telegram de hitos del experimento. Reutiliza el mismo bot que
ya usa el blog (/root/blog-tato9689/avisar_telegram.py) — mismo canal por el
que habla Claude Code con Tato.
"""
import json
from pathlib import Path

import httpx

CONFIG_PATH = Path("/root/.config/telegram-web/config.json")


def cargar_config():
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def enviar(texto: str):
    cfg = cargar_config()
    url = f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage"
    resp = httpx.post(
        url,
        json={"chat_id": cfg["owner_chat_id"], "text": texto, "disable_web_page_preview": False},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram respondió sin ok: {data}")
