#!/usr/bin/env python3
"""La matriz cruzada: diseñador × generador, con el resultado seguido hasta el CTR.

Cómo funciona una ronda, para un artículo de una IA:

  1. Se elige el DISEÑADOR (uno de los 4 modelos del experimento). Escribe el
     prompt de la og:image de ese artículo, sin saber quién la va a dibujar.
  2. Ese MISMO prompt se manda a los generadores disponibles (openai, gemini).
  3. Cada resultado se guarda como una fila: diseñador, generador, prompt,
     coste de pensarla, coste de dibujarla, tiempo de cada paso, tamaño.
  4. Semanas después, `medir()` cruza cada fila con Search Console y rellena
     impresiones, clics, CTR y posición de ESA url.

El diseñador rota y no es siempre el dueño del sitio: si Claude escribiera
siempre los prompts de su propio sitio, la matriz mediría el nicho y no la
pareja. Rotando, cada combinación acaba tocando los 4 nichos.

Fase 1: el diseñador recibe el tema y el estilo del sitio, nunca su URL, su
nicho por su nombre ni nada que identifique a la IA dueña. Escribir un prompt
de imagen no requiere saber de quién es el sitio, y así no se filtra nada.

Uso:
  matriz_imagenes.py generar <ia> <slug> "<tema del articulo>"
  matriz_imagenes.py medir            # rellena resultados desde GSC
  matriz_imagenes.py informe          # qué pareja va ganando
"""
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

from entorno import cargar_env  # noqa: E402

cargar_env()

import imagen_ia  # noqa: E402
from db import get_conn, init_db  # noqa: E402

DISENADORES = ["claude", "gpt", "gemini", "deepseek"]

# Reescrita el 2026-10-29 (las filas anteriores de la matriz son de otro tramo,
# no compararlas con las nuevas). Las 42 imágenes publicadas hasta entonces
# «cantaban a IA»: los prompts pedían, casi todos, chiaroscuro, rim light,
# teal y ámbar, desenfoque de fondo, «sleek/premium» y un objeto heroico
# centrado sobre superficie pulida. Ese es exactamente el aspecto de foto de
# stock generada que cualquiera reconoce. La regla nueva: o documental creíble,
# con desorden e imperfección reales, o ilustración gráfica que no finge ser
# foto. Y siempre la dirección de arte del sitio, para que las imágenes de un
# mismo sitio parezcan de la misma casa.
INSTRUCCION = (
    "Escribe el prompt para la imagen de vista previa social (og:image, 1200x630) "
    "de un articulo. Es tambien la miniatura de portada del sitio. Su trabajo es "
    "conseguir el clic y, sobre todo, NO parecer generada por IA: si alguien la "
    "mira dos segundos y piensa 'esto es IA', ha fallado.\n\n"
    "Elige UNO de estos dos caminos (si el sitio tiene direccion de arte, manda "
    "ella):\n"
    "A) Fotografia documental creible, como la haria un fotografo de revista en "
    "un sitio real: luz disponible y corriente (ventana, fluorescente de taller, "
    "flash directo de compacta), angulo normal de una persona de pie, encuadre "
    "algo imperfecto y descentrado, contexto real con su desorden (cables, "
    "polvo, marcas de uso, cinta, notas, herramientas gastadas), colores "
    "apagados y naturales, grano de pelicula ligero. Nombra camara y pelicula "
    "concretas (p. ej. 'shot on a 35mm compact, Kodak Portra 400, slight grain, "
    "on-camera flash').\n"
    "B) Ilustracion grafica editorial que no finge ser foto: risografia o "
    "serigrafia a 2-3 tintas planas, grabado, collage de recortes, o dibujo "
    "tecnico a linea; paleta limitada y textura de papel/impresion.\n\n"
    "Prohibido, porque es lo que delata a la IA: chiaroscuro o luz dramatica, "
    "rim light, contraluz cinematografico, teal-and-orange o teal y ambar, "
    "desenfoque de fondo exagerado, superficies impolutas o brillantes, "
    "'sleek', 'premium', 'futuristic', 'hyperrealistic', '8k', 'cinematic', "
    "objeto heroico centrado sobre fondo liso o degradado, objetos flotando, "
    "hologramas, brillos y particulas, simetria perfecta, render 3D pulido.\n\n"
    "Reglas duras:\n"
    "- NADA de texto, numeros ni letras dentro de la imagen. El titular lo pone "
    "la red social encima.\n"
    "- Sin marcas, logos ni productos identificables de terceros.\n"
    "- Sin personas reconocibles (manos o figuras de espaldas si hacen falta).\n"
    "- Que se entienda a 300 px de ancho: un sujeto claro, no un bodegon de diez cosas.\n"
    "- Concreta: sujeto, lugar, luz, camara/tecnica, paleta, textura.\n\n"
    "Responde SOLO con el prompt, en ingles, en un parrafo. Sin comillas, sin "
    "explicaciones, sin prefacio."
)

# Remate que se añade a TODO prompt antes de mandarlo a los generadores (el
# mismo a los dos, así la matriz sigue comparando lo mismo). En la primera
# prueba del 29-oct, nombrar la película («Kodak Portra 400») hizo que Gemini
# dibujara el borde del negativo con el nombre impreso: texto dentro de la
# imagen, justo lo prohibido.
REMATE = ("Full-bleed image filling the whole frame: no borders, no film frame, "
          "no film edge markings, no captions, no text, letters or numbers anywhere.")

# Sección del sistema de diseño de cada sitio que se pasa al diseñador de la
# imagen. Tope corto: es estilo, no un briefing, y el diseñador rota entre IAs.
MAX_DIRECCION_ARTE = 1500


def direccion_de_arte(repo_dir: Path) -> str:
    """La sección «Dirección de arte» de memoria/sistema-de-diseno.md del sitio,
    o "" si aún no la tiene. La escribe la propia IA en su turno de diseño."""
    ruta = repo_dir / "memoria" / "sistema-de-diseno.md"
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError:
        return ""
    import re
    m = re.search(r"^#{1,3}\s*Direcci[oó]n de arte[^\n]*\n(.*?)(?=^#{1,3}\s|\Z)",
                  texto, flags=re.MULTILINE | re.DOTALL | re.IGNORECASE)
    return (m.group(1).strip() if m else "")[:MAX_DIRECCION_ARTE]


def _turno_disenador(slug: str) -> str:
    """A quién le toca diseñar: al que menos filas lleve en la matriz.

    Se probaron dos cosas peores antes. `sum(slug.encode()) % 4` correlaciona
    con la longitud y las letras, y como los slugs de un mismo nicho se
    parecen, los 6 primeros artículos reales caían todos en 2 diseñadores.
    Cambiarlo a sha256 lo mejoró pero no lo arregló: sobre los 12 slugs reales
    salía 5/5/2/0, con GPT sin una sola imagen. Con N grande cualquier hash
    reparte bien; con N pequeña, ninguno — y aquí la N son decenas de
    artículos en diez meses, no miles.

    Así que no se sortea: se mira quién va más atrás y le toca. Determinista
    dado el estado de la base, y el reparto sale parejo desde el primer
    artículo, que es cuando importa. Una vez asignado, el UNIQUE de la tabla lo
    fija: repetir la generación del mismo slug no cambia de diseñador.

    Si la base no está disponible, cae a sha256 — un reparto desigual es mejor
    que no generar nada."""
    try:
        conn = get_conn()
        ya = dict(conn.execute(
            "SELECT disenador, COUNT(*) FROM imagenes_matriz WHERE slug = ? GROUP BY disenador",
            (slug,)).fetchall())
        if ya:  # este slug ya tiene diseñador asignado: se respeta
            conn.close()
            return max(ya, key=ya.get)
        cuenta = dict(conn.execute(
            "SELECT disenador, COUNT(DISTINCT slug) FROM imagenes_matriz GROUP BY disenador").fetchall())
        conn.close()
    except Exception:
        return DISENADORES[hashlib.sha256(slug.encode()).digest()[0] % len(DISENADORES)]
    # Empates por el orden fijo de DISENADORES, no por el que devuelva sqlite:
    # sin esto el reparto dependería del orden de las filas y dejaría de ser
    # reproducible al reconstruir la base.
    return min(DISENADORES, key=lambda d: (cuenta.get(d, 0), DISENADORES.index(d)))


def escribir_prompt(disenador: str, tema: str, estilo: str = "") -> dict:
    from consulta_ias.clientes import llamar_con_metadata, coste_estimado
    encargo = f"{INSTRUCCION}\n\nTema del articulo: {tema}"
    if estilo:
        encargo += f"\nEstilo visual del sitio: {estilo}"
    r = llamar_con_metadata(disenador, "Eres director de arte. Respondes solo con el prompt pedido.", encargo, tier="diaria")
    return {
        "prompt": r["texto"].strip().strip('"'),
        "modelo": r["modelo"],
        "segundos": r.get("duracion_seg"),
        "coste_usd": coste_estimado(r["modelo"], r.get("tokens_in"), r.get("tokens_out")),
    }


def generar(ia: str, slug: str, tema: str, estilo: str = "", disenador: str | None = None) -> list[dict]:
    init_db()
    disenador = disenador or _turno_disenador(slug)
    disponibles = imagen_ia.disponibles()
    if not disponibles:
        print("ningun generador tiene clave: define OPENAI_IMAGE_API_KEY y/o "
              "GEMINI_IMAGE_API_KEY en /root/.config/ai-seo-battle/.env", file=sys.stderr)
        return []

    print(f"[matriz] {slug}: disena {disenador}, generan {disponibles}")
    p = escribir_prompt(disenador, tema, estilo)
    p["prompt"] = f"{p['prompt'].rstrip()} {REMATE}"
    coste_txt = f"${p['coste_usd']:.4f}" if p["coste_usd"] is not None else "coste desconocido (sin precio para el modelo)"
    print(f"[matriz] prompt ({p['modelo']}, {coste_txt}): {p['prompt'][:120]}...")

    destino_dir = Path(f"/root/aisb-{ia}/og/matriz")
    destino_dir.mkdir(parents=True, exist_ok=True)
    conn = get_conn()
    filas = []
    for gen in disponibles:
        fila = {
            "ia": ia, "url_articulo": f"https://{ia}.retoseo.com/{slug}", "slug": slug,
            "disenador": disenador, "modelo_disenador": p["modelo"],
            "generador": gen, "modelo_generador": None, "prompt": p["prompt"],
            "ruta_local": None, "coste_prompt_usd": p["coste_usd"],
            "coste_imagen_usd": None, "seg_prompt": p["segundos"], "seg_imagen": None,
            "bytes": None, "creado_el": datetime.now(timezone.utc).isoformat(),
            "resultado": "exito", "detalle_error": None,
        }
        try:
            r = imagen_ia.generar(gen, p["prompt"])
            ruta = destino_dir / f"{slug}-{gen}.{r['formato']}"
            ruta.write_bytes(r["bytes"])
            fila.update(modelo_generador=r["modelo"], ruta_local=str(ruta),
                        coste_imagen_usd=r["coste_usd"], seg_imagen=r["segundos"],
                        bytes=len(r["bytes"]))
            nota = (f" (comprimida desde {r['bytes_originales'] // 1024} KB)"
                    if r.get("comprimida") else "")
            print(f"[matriz] {gen}: {len(r['bytes']) // 1024} KB{nota}, "
                  f"{r['segundos']}s, ${r['coste_usd']}")
        except Exception as e:
            fila.update(resultado="error", detalle_error=str(e)[:300])
            print(f"[matriz] {gen} FALLO: {str(e)[:160]}", file=sys.stderr)
        cols = ", ".join(fila)
        conn.execute(
            f"INSERT OR REPLACE INTO imagenes_matriz ({cols}) VALUES ({', '.join('?' * len(fila))})",
            tuple(fila.values()))
        filas.append(fila)
    conn.commit()
    conn.close()
    return filas


def medir() -> int:
    """Cruza cada fila con Search Console y rellena impresiones, clics, CTR y
    posición de su URL. Solo mira filas sin medir o medidas hace más de 7 días:
    una og:image no cambia de rendimiento de un día para otro y repreguntar a
    diario no añade señal."""
    init_db()
    from googleapiclient.discovery import build
    import poller_metrics as pm
    cfg = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
    creds = pm.credenciales(cfg["google_service_account"])
    service = build("searchconsole", "v1", credentials=creds)
    sitios = {a["ia"]: a["gsc_site"] for a in cfg["agentes"]}

    conn = get_conn()
    conn.row_factory = __import__("sqlite3").Row
    pendientes = conn.execute(
        # Solo las que se sirven de verdad. Por cada artículo se generan dos
        # imágenes (una por generador) y solo una acaba publicada; medir las
        # dos con las mismas impresiones de la URL le daría a la que nadie vio
        # el mismo CTR que a la que sí se vio, y la matriz mediría ruido.
        # Quién es la publicada lo marca imagen_publicada.py en el despliegue.
        "SELECT id, ia, url_articulo FROM imagenes_matriz "
        "WHERE resultado = 'exito' AND publicada = 1 "
        "AND (medido_el IS NULL OR medido_el < ?)",
        ((date.today().isoformat()[:8] + "01"),)).fetchall()
    fin = date.today()
    actualizadas = 0
    for f in pendientes:
        site = sitios.get(f["ia"])
        if not site:
            continue
        try:
            resp = service.searchanalytics().query(siteUrl=site, body={
                "startDate": "2026-08-30", "endDate": fin.isoformat(),
                "dimensions": ["page"],
                "dimensionFilterGroups": [{"filters": [
                    {"dimension": "page", "operator": "equals", "expression": f["url_articulo"]}]}],
            }).execute()
        except Exception as e:
            print(f"GSC no contesta para {f['url_articulo']}: {str(e)[:120]}", file=sys.stderr)
            continue
        filas = resp.get("rows", [])
        r = filas[0] if filas else {}
        conn.execute(
            "UPDATE imagenes_matriz SET impresiones=?, clics=?, ctr=?, posicion=?, medido_el=? WHERE id=?",
            (int(r.get("impressions", 0)), int(r.get("clicks", 0)),
             round(r.get("ctr", 0) * 100, 3), round(r.get("position", 0), 1),
             datetime.now(timezone.utc).isoformat(), f["id"]))
        actualizadas += 1
    conn.commit()
    conn.close()
    print(f"matriz: {actualizadas} filas medidas")
    return actualizadas


def informe():
    conn = get_conn()
    conn.row_factory = __import__("sqlite3").Row
    filas = conn.execute("""
        SELECT disenador, generador, COUNT(*) n,
               SUM(impresiones) impr, SUM(clics) clics,
               ROUND(AVG(ctr), 3) ctr_medio, ROUND(AVG(posicion), 1) pos,
               ROUND(SUM(COALESCE(coste_prompt_usd,0) + COALESCE(coste_imagen_usd,0)), 4) coste
        FROM imagenes_matriz WHERE resultado = 'exito'
        GROUP BY disenador, generador ORDER BY ctr_medio DESC NULLS LAST
    """).fetchall()
    conn.close()
    if not filas:
        print("matriz vacía todavía: no hay ninguna imagen generada.")
        return
    print(f"{'diseña':10}{'genera':9}{'n':>4}{'impr':>7}{'clics':>7}{'CTR%':>8}{'pos':>7}{'coste$':>9}")
    for f in filas:
        print(f"{f['disenador']:10}{f['generador']:9}{f['n']:>4}{f['impr'] or 0:>7}"
              f"{f['clics'] or 0:>7}{f['ctr_medio'] if f['ctr_medio'] is not None else 0:>8}"
              f"{f['pos'] or 0:>7}{f['coste'] or 0:>9}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "generar":
        generar(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "")
    elif cmd == "medir":
        medir()
    elif cmd == "informe":
        informe()
    else:
        print(__doc__)
        sys.exit(1)
