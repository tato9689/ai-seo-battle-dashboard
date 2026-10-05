"""¿Se desborda un sitio en móvil? Abre la portada y los 2 últimos artículos
en Chrome headless a 390 px, mide el ancho real del documento y avisa por
Telegram. Nació el 2026-10-05 para vigilar el desborde de GPT tras sus turnos
de diseño. Uso: python comprobar_movil.py gpt [claude ...]

Usa /usr/bin/python3 (tiene websockets; el venv no)."""
import asyncio, json, re, shutil, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path



def enviar_telegram(texto):
    # Sin avisos.py: ese tira de httpx, que no está en el python del sistema.
    cfg = json.loads(Path("/root/.config/telegram-web/config.json").read_text())
    datos = json.dumps({"chat_id": cfg["owner_chat_id"], "text": texto,
                        "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage",
                                 data=datos, headers={"Content-Type": "application/json"})
    if not json.load(urllib.request.urlopen(req, timeout=15)).get("ok"):
        raise RuntimeError("Telegram respondió sin ok")

PUERTO = 9334
JS = r"""(()=>{const W=document.documentElement.clientWidth;const sw=document.documentElement.scrollWidth;
const culpables=[];document.querySelectorAll('body *').forEach(e=>{const r=e.getBoundingClientRect();
if(r.right>W+1&&r.width>0){const p=e.parentElement,pr=p&&p.getBoundingClientRect();
if(!pr||pr.right<=W+1)culpables.push(e.tagName.toLowerCase()+(e.className?'.'+String(e.className).split(' ')[0]:'')+' '+Math.round(r.width)+'px')}});
return JSON.stringify({W,sw,culpables:[...new Set(culpables)].slice(0,4)})})()"""


async def medir(url):
    import websockets
    tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/json"))
    ws = [t for t in tabs if t["type"] == "page"][0]["webSocketDebuggerUrl"]
    async with websockets.connect(ws, max_size=None) as w:
        await w.send(json.dumps({"id": 1, "method": "Emulation.setDeviceMetricsOverride",
                                 "params": {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True}}))
        await w.recv()
        await w.send(json.dumps({"id": 2, "method": "Page.navigate", "params": {"url": url}}))
        await asyncio.sleep(5)
        await w.send(json.dumps({"id": 3, "method": "Runtime.evaluate", "params": {"expression": JS, "returnByValue": True}}))
        while True:
            m = json.loads(await w.recv())
            if m.get("id") == 3:
                return json.loads(m["result"]["result"]["value"])


def urls(ia):
    rss = Path(f"/var/www/{ia}.retoseo.com/rss.xml").read_text(encoding="utf-8")
    base = f"https://{ia}.retoseo.com/"
    # El rss.xml lo escribe la propia IA: solo se abren URLs de su sitio, nunca
    # file://, IPs internas ni dominios ajenos con un Chrome que va como root.
    arts = [u.strip() for u in re.findall(r"<item>.*?<link>([^<]+)</link>", rss, re.S)]
    return [base] + [u for u in arts if u.startswith(base) and re.fullmatch(r"[\w./:%-]+", u)][:2]


def main(ias):
    # --no-sandbox es obligatorio: Chrome no arranca como root con sandbox.
    # El puerto de depuración solo escucha en 127.0.0.1 y el perfil es temporal.
    perfil = tempfile.mkdtemp(prefix="comprobar-movil-")
    chrome = subprocess.Popen(["google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu",
                               "--remote-debugging-address=127.0.0.1", f"--user-data-dir={perfil}",
                               f"--remote-debugging-port={PUERTO}", "about:blank"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    lineas = []
    try:
        time.sleep(3)
        for ia in ias:
            for u in urls(ia):
                try:
                    r = asyncio.run(medir(u + ("&" if "?" in u else "?") + f"m={int(time.time())}"))
                    if r["sw"] > r["W"] + 1:
                        lineas.append(f"❌ {u}\n   se sale: {r['sw']} px en pantalla de {r['W']} · {', '.join(r['culpables'])}")
                    else:
                        lineas.append(f"✅ {u}\n   cabe ({r['sw']} px)")
                except Exception as e:
                    lineas.append(f"⚠️ {u}\n   no se pudo medir: {e}")
    finally:
        chrome.terminate()
        chrome.wait(timeout=10)
        shutil.rmtree(perfil, ignore_errors=True)
    texto = "📱 Comprobación móvil (390 px) tras el turno de diseño\n\n" + "\n".join(lineas)
    print(texto)
    if "--sin-aviso" not in sys.argv:
        enviar_telegram(texto)


if __name__ == "__main__":
    main([a for a in sys.argv[1:] if not a.startswith("--")] or ["gpt"])
