#!/usr/bin/env python3
"""Repone el script que clasifica el origen del alta en las páginas ya
publicadas de un agente.

Mismo criterio que `verificacion.py` y `og_image.py`: lo que la IA no puede
permitirse perder no vive en su prompt, vive en el despliegue. El agente
reescribe su `index.html` entera en cada turno, así que cualquier cosa que
tenga que sobrevivir a eso se repone después, no se le pide por favor.

Qué se pierde si falta: el formulario lleva un campo oculto
`attribs_origen`, y este script es lo único que lo rellena mirando de dónde
vino la visita. Sin él todas las altas se guardan como "directo" y **ninguna
cuenta como orgánica**, que es la única categoría que puntúa en el
leaderboard. Y no se puede reconstruir después: el referrer solo existe en
el momento de la visita.

Pasó de verdad el 2026-09-02: el turno de diseño de Gemini rehizo su portada
y se llevó el script por delante dejando el campo. El guardarraíl lo detectó
—como aviso, que es lo que toca: el alta entra igual— pero un aviso llega en
el turno siguiente, y para entonces las altas de ese día ya están mal
clasificadas.

No identifica a nadie: guarda una de tres etiquetas, nunca la URL de
procedencia ni nada personal. Por eso no necesita consentimiento de cookies:
no almacena nada en el navegador.

Uso: origen_alta.py <ia> [raiz_web]
"""
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent

SCRIPT = """<script>
  /* Clasificación del origen del alta — la repone origen_alta.py en cada
     despliegue. No la edites en el HTML: se sobrescribe. */
  (function () {
    var campo = document.getElementById("origen");
    if (!campo) return;
    var BUSCADORES = /google\\.|bing\\.|duckduckgo\\.|ecosia\\.|yahoo\\.|yandex\\.|brave\\.|startpage\\./i;
    var origen = "directo";
    try {
      if (/[?&]utm_/.test(location.search)) {
        origen = "meta";
      } else if (document.referrer) {
        var host = new URL(document.referrer).hostname;
        if (host && host !== location.hostname) {
          origen = BUSCADORES.test(host) ? "organico" : "meta";
        }
      }
    } catch (e) {
      /* Un referrer malformado no debe impedir que alguien se suscriba. */
    }
    campo.value = origen;
  })();
</script>"""

RE_YA_ESTA = re.compile(r'getElementById\(\s*["\']origen["\']\s*\)')
RE_CAMPO = re.compile(r'id=["\']origen["\']', re.IGNORECASE)


def aplicar(raiz: Path) -> tuple[int, int]:
    """Devuelve (páginas arregladas, páginas que ya lo tenían)."""
    puestas = ya = 0
    for pagina in sorted(raiz.rglob("*.html")):
        html = pagina.read_text(encoding="utf-8", errors="ignore")
        # Solo donde hay campo que rellenar: una página sin formulario no lo
        # necesita, y meterlo sería peso muerto.
        if not RE_CAMPO.search(html):
            continue
        if RE_YA_ESTA.search(html):
            ya += 1
            continue
        if "</body>" not in html:
            continue
        pagina.write_text(html.replace("</body>", f"  {SCRIPT}\n</body>", 1), encoding="utf-8")
        puestas += 1
    return puestas, ya


if __name__ == "__main__":
    ia = sys.argv[1]
    if len(sys.argv) > 2:
        raiz = Path(sys.argv[2])
    else:
        dominio = (BASE / ".dominio").read_text(encoding="utf-8").strip()
        raiz = Path(f"/var/www/{ia}.{dominio}")
    puestas, ya = aplicar(raiz)
    if puestas:
        print(f"[{ia}] script de origen del alta repuesto en {puestas} páginas "
              f"(otras {ya} ya lo tenían)")
    else:
        print(f"[{ia}] script de origen del alta: correcto en {ya} páginas")
