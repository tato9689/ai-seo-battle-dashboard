"""Difusión pública del experimento a un canal de Telegram.

Distinto de avisos.py, que son alertas privadas para Tato (errores, hitos).
Esto es el canal público: cada vez que una IA publica algo nuevo, se anuncia
con enlace, para que el experimento tenga un sitio donde seguirse en vivo sin
depender de que alguien recargue el dashboard.

Por qué Telegram y no notificaciones push web, al menos para empezar:
  - Cero fricción: no pide permisos al visitante ni depende de que acepte un
    popup (que además hunde la conversión y es un patrón oscuro si salta al
    cargar).
  - Cero RGPD adicional: no se guarda ningún dato de nadie, a diferencia del
    endpoint de suscripción push, que sí es dato personal y multiplicaría por
    cuatro las obligaciones legales del proyecto.
  - Funciona en iOS, donde el push web solo llega si el usuario instala la
    web como PWA.
El push web queda como fase 2, y solo tras una acción explícita del usuario.

Solo emite: nunca lee ni responde mensajes de desconocidos, coherente con el
guardarraíl ya cerrado de no interactuar en automático con terceros.

Uso:  python difusion.py [--dry-run]
"""
import json
import sys
from pathlib import Path

import httpx

BASE = Path(__file__).parent
CONFIG_PATH = BASE / "config.json"
TELEGRAM_CONFIG = Path("/root/.config/telegram-web/config.json")
# Qué se ha anunciado ya. Sin esto, cada pase reenviaría el catálogo entero.
ESTADO_PATH = BASE / "cache" / "difusion_publicada.json"

NOMBRES = {"claude": "Claude", "gpt": "GPT", "gemini": "Gemini", "deepseek": "DeepSeek"}
MAX_POR_PASE = 4  # un agente que publique en lote no debe inundar el canal


def _cfg_telegram() -> dict:
    with open(TELEGRAM_CONFIG, encoding="utf-8") as fh:
        return json.load(fh)


def canal_destino(cfg_tg: dict) -> str | None:
    """Canal público del experimento. Si no está configurado, no se difunde
    nada: publicar en el chat privado de Tato lo que va dirigido al público
    sería peor que no publicar."""
    return cfg_tg.get("canal_publico_seo_battle")


def cargar_estado() -> dict:
    if ESTADO_PATH.exists():
        try:
            return json.loads(ESTADO_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # Un estado corrupto no debe romper el pase; se prefiere perder el
            # historial de anuncios (y como mucho repetir uno) a quedarse
            # mudo para siempre.
            print("estado de difusión corrupto, se empieza de cero", file=sys.stderr)
    return {}


def guardar_estado(estado: dict):
    ESTADO_PATH.parent.mkdir(parents=True, exist_ok=True)
    ESTADO_PATH.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")


def articulos_de(repo_dir: Path, base_url: str) -> list[tuple[str, str, str]]:
    """(id_estable, título, url) de cada artículo publicado por ese agente.
    Se lee del rss.xml que ya genera generar_feeds.py — misma fuente que ven
    los lectores, así no hay dos definiciones distintas de 'artículo'."""
    import generar_feeds

    salida = []
    for rel, titulo, _desc, _mod in generar_feeds._paginas(repo_dir):
        if rel in generar_feeds.NO_SON_ARTICULOS:
            continue
        salida.append((rel, titulo, generar_feeds._url_publica(base_url, rel)))
    return salida


def enviar(chat_id: str, texto: str, dry_run: bool):
    if dry_run:
        print(f"--dry-run → {chat_id}:\n{texto}\n")
        return
    cfg = _cfg_telegram()
    resp = httpx.post(
        f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage",
        json={"chat_id": chat_id, "text": texto, "disable_web_page_preview": False},
        timeout=15,
    )
    resp.raise_for_status()
    if not resp.json().get("ok"):
        raise RuntimeError(f"Telegram respondió sin ok: {resp.json()}")


def main(dry_run: bool = False):
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        cfg = json.load(fh)

    cfg_tg = _cfg_telegram()
    canal = canal_destino(cfg_tg)
    if not canal and not dry_run:
        print("Sin 'canal_publico_seo_battle' en la config de Telegram — no se difunde nada.", file=sys.stderr)
        return

    estado = cargar_estado()
    enviados = 0

    for agente in cfg["agentes"]:
        ia = agente["ia"]
        log_url = agente.get("log_url", "")
        base_url = log_url[: -len("/log.json")] if log_url.endswith("/log.json") else ""
        if not base_url or "PENDIENTE" in base_url:
            continue

        repo_dir = Path(f"/root/aisb-{ia}")
        if not repo_dir.exists():
            continue

        ya = set(estado.get(ia, []))
        nuevos = [a for a in articulos_de(repo_dir, base_url) if a[0] not in ya]

        for id_art, titulo, url in nuevos[:MAX_POR_PASE]:
            if enviados >= MAX_POR_PASE:
                break
            enviar(
                canal or "DRY",
                f"🤖 {NOMBRES.get(ia, ia)} acaba de publicar:\n\n{titulo}\n{url}\n\n"
                f"Decidido y escrito por la IA sola, sin revisión humana. "
                f"Por qué lo hizo: {base_url}/log",
                dry_run,
            )
            ya.add(id_art)
            enviados += 1

        estado[ia] = sorted(ya)

    if not dry_run:
        guardar_estado(estado)
    print(f"difusión: {enviados} anuncios enviados")


if __name__ == "__main__":
    main("--dry-run" in sys.argv[1:])
