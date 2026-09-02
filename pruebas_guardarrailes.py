#!/usr/bin/env python3
"""Prueba de humo de los guardarraíles. Corre `validar()` ENTERO.

Nació de un fallo real del 2026-09-02: al aflojar `_transparencia()` se
quitaron dos regex (`_RE_ENLACE_LOG`, `_RE_UNA_IA`) que otra función,
`_diario_arriba()`, seguía usando. Las dos funciones que se tocaron se
probaron una por una y pasaron; nadie llamó a `validar()` completo. Los
cuatro turnos de diseño de ese miércoles reventaron con un NameError
DESPUÉS de haber llamado y pagado a los modelos: dinero gastado, nada
publicado y nada registrado.

La lección no es "probar más", es **probar la puerta por la que entra el
turno**. Los checks se llaman desde `validar()`, así que lo que hay que
ejecutar es `validar()`.

Uso: python pruebas_guardarrailes.py   (sale 1 si algo falla)
"""
import sys
import tempfile
from pathlib import Path

import guardarrailes

PAGINA_BUENA = """<!doctype html><html lang="es"><head>
<title>Calibrar tu impresora 3D sin morir en el intento</title>
<meta name="description" content="Guía de calibración con temperaturas verificadas, tabla de retracción y los tres fallos que más se repiten en FDM.">
<link rel="canonical" href="https://claude.retoseo.com/"></head><body>
<header><a href="/">Inicio</a></header>
<h1>Calibrar tu impresora</h1>
<p>Contenido útil de verdad sobre el nicho.</p>
<form action="https://panel.retoseo.com/subscription/form" method="post">
  <input type="email" id="email" name="email" required>
  <input type="hidden" name="l" value="3">
  <input type="hidden" name="attribs_origen" id="origen" value="directo">
  <p><input type="checkbox" id="consentimiento" name="consentimiento" required>
  <label for="consentimiento">Acepto la <a href="/privacidad">política de privacidad</a>.</label></p>
  <button type="submit">Suscribirme</button>
</form>
<script>document.getElementById("origen");</script>
<footer>
<p>Esta web la escribe y la gestiona una IA. Cada decisión, en el <a href="/log">diario de guerra</a>.</p>
<p><a href="https://retoseo.com">Ver el marcador en vivo</a></p>
<p>Proyecto independiente, sin afiliación con OpenAI, Anthropic, Google ni DeepSeek.</p>
</footer></body></html>"""

# Cada caso: (nombre, transformación de la página buena, debe_bloquear)
CASOS = [
    ("página correcta", lambda h: h, False),
    ("sin mención a IA", lambda h: h.replace("Esta web la escribe y la gestiona una IA.", "Hecho con cariño."), True),
    ("dice 'inteligencia artificial'", lambda h: h.replace("una IA", "una inteligencia artificial"), False),
    ("dice 'la IA Claude'", lambda h: h.replace("la gestiona una IA", "la gestiona la IA Claude"), False),
    ("enlace al diario absoluto", lambda h: h.replace('href="/log"', 'href="https://claude.retoseo.com/log"'), False),
    ("sin enlace al diario", lambda h: h.replace('href="/log"', 'href="/sobre"'), True),
    ("sin descargo de no-afiliación", lambda h: h.replace("sin afiliación", "asociados"), True),
    ("formulario decorativo", lambda h: h.replace(
        '<form action="https://panel.retoseo.com/subscription/form" method="post">',
        '<form action="#" method="post" onsubmit="event.preventDefault()">'), True),
    ("formulario sin consentimiento", lambda h: h.replace('name="consentimiento" required', 'name="otro"'), True),
    ("sin attribs_origen (solo avisa)", lambda h: h.replace('<input type="hidden" name="attribs_origen" id="origen" value="directo">', ""), False),
]


def main() -> int:
    fallos = []
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "privacidad.html").write_text("<html></html>", encoding="utf-8")
        (repo / "log.html").write_text("<html></html>", encoding="utf-8")
        for nombre, transformar, debe_bloquear in CASOS:
            html = transformar(PAGINA_BUENA)
            try:
                bloqueantes, avisos = guardarrailes.validar(repo, {"index.html": html})
            except Exception as e:  # noqa: BLE001 — cualquier excepción aquí tumba un turno real
                fallos.append(f"{nombre}: validar() REVIENTA con {type(e).__name__}: {e}")
                continue
            if bool(bloqueantes) != debe_bloquear:
                esperado = "bloquear" if debe_bloquear else "pasar"
                fallos.append(f"{nombre}: debía {esperado} y no lo hizo → {bloqueantes or avisos}")

    for f in fallos:
        print(f"✗ {f}")
    print(f"{len(CASOS) - len(fallos)}/{len(CASOS)} casos correctos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
