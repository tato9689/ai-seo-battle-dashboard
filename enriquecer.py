#!/usr/bin/env python3
"""Material para enriquecer las piezas, más allá de Pexels: vídeos de YouTube
verificados, fotos libres de Wikimedia Commons con su licencia, y una imagen
generada a medida para la pieza.

Pedido por Tato el 2026-10-29 («que puedan usar Pexels, crear imágenes,
incrustar vídeos de YouTube, imágenes con fuentes citadas de internet»). El
prompt ya permitía YouTube desde septiembre y a esa fecha ninguna de las 4 lo
había usado ni una vez: no tenían forma de encontrar un vídeo real, y un ID de
YouTube escrito de memoria es un ID inventado. Mismo patrón que `imagenes.py`:
el agente lo pide en `*_siguiente_turno` y le llega resuelto al turno
siguiente, con el HTML de crédito ya construido.

«Imágenes de internet con la fuente citada» NO es coger cualquier foto y poner
el enlace debajo: citar no da permiso para reproducir una foto ajena. Por eso
las de internet salen solo de Wikimedia Commons y solo con licencia libre
(CC0, dominio público, CC BY, CC BY-SA), que es donde citar autor y licencia sí
basta.

Todo texto que viene de un tercero (títulos, canales, autores) se escapa antes
de meterlo en HTML: el agente lo pega tal cual.
"""
import html
import os
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

TIMEOUT = 20
UA = "retoseo-experimento/1.0 (https://retoseo.com)"
MAX_CONSULTAS = 2
POR_CONSULTA = 3


def _seguro(url: str, respaldo: str = "#") -> str:
    try:
        if urlparse(url).scheme in ("http", "https"):
            return url
    except ValueError:
        pass
    return respaldo


def _id_youtube(url: str) -> str | None:
    u = urlparse(url)
    if u.netloc.endswith("youtube.com") and u.path == "/watch":
        vid = parse_qs(u.query).get("v", [None])[0]
    elif u.netloc == "youtu.be":
        vid = u.path.lstrip("/")
    else:
        return None
    return vid if vid and re.fullmatch(r"[\w-]{11}", vid) else None


def videos(consulta: str, n: int = POR_CONSULTA) -> list[dict]:
    """Vídeos de YouTube reales para `consulta`: Brave los encuentra y el
    oEmbed de YouTube confirma que existen y se pueden incrustar (devuelve 401
    si el autor desactivó la inserción)."""
    clave = os.environ.get("BRAVE_SEARCH_API_KEY")
    if not clave:
        raise RuntimeError("sin BRAVE_SEARCH_API_KEY configurada")
    resp = httpx.get(
        "https://api.search.brave.com/res/v1/videos/search",
        params={"q": consulta, "count": 10, "search_lang": "es", "country": "es"},
        headers={"X-Subscription-Token": clave, "Accept": "application/json"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    salida = []
    for r in resp.json().get("results", []):
        vid = _id_youtube(r.get("url", ""))
        if not vid or any(v["id"] == vid for v in salida):
            continue
        try:
            o = httpx.get("https://www.youtube.com/oembed",
                          params={"url": f"https://www.youtube.com/watch?v={vid}", "format": "json"},
                          timeout=TIMEOUT)
        except httpx.HTTPError:
            continue
        if o.status_code != 200:
            continue
        meta = o.json()
        titulo = html.escape(meta.get("title", "Vídeo"))
        canal = html.escape(meta.get("author_name", "YouTube"))
        url_canal = html.escape(_seguro(meta.get("author_url", ""), "https://www.youtube.com"), quote=True)
        salida.append({
            "id": vid,
            "titulo": meta.get("title"),
            "canal": meta.get("author_name"),
            "url": f"https://www.youtube.com/watch?v={vid}",
            "duracion": (r.get("video") or {}).get("duration"),
            "embed_html": (
                f'<figure class="video">'
                f'<iframe src="https://www.youtube-nocookie.com/embed/{vid}" title="{titulo}" '
                f'loading="lazy" width="560" height="315" style="aspect-ratio:16/9;width:100%;height:auto" '
                f'allow="encrypted-media; picture-in-picture" referrerpolicy="strict-origin-when-cross-origin" '
                f'allowfullscreen></iframe>'
                f'<figcaption>Vídeo: <a href="https://www.youtube.com/watch?v={vid}">{titulo}</a>, '
                f'de <a href="{url_canal}">{canal}</a> en YouTube</figcaption></figure>'
            ),
        })
        if len(salida) >= n:
            break
    return salida


LICENCIAS_LIBRES = re.compile(r"^(cc0|public domain|pd|cc by(-sa)? [\d.]+)", re.IGNORECASE)


def _sin_html(texto: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", texto or "")).strip()


def commons(consulta: str, n: int = POR_CONSULTA) -> list[dict]:
    """Fotos de Wikimedia Commons con licencia libre, con autor, licencia y
    enlace a la ficha ya puestos en `atribucion_html`. Commons busca mejor en
    inglés: el prompt se lo dice al agente."""
    resp = httpx.get(
        "https://commons.wikimedia.org/w/api.php",
        params={"action": "query", "format": "json", "generator": "search",
                "gsrnamespace": 6, "gsrsearch": consulta, "gsrlimit": 20,
                "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 960},
        headers={"User-Agent": UA},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    paginas = sorted((resp.json().get("query") or {}).get("pages", {}).values(),
                     key=lambda p: p.get("index", 99))
    salida = []
    for p in paginas:
        info = (p.get("imageinfo") or [{}])[0]
        # Sin `filetype:bitmap` en la búsqueda (con varias palabras no
        # devuelve nada): se filtra aquí, o se cuelan PDFs y vídeos. Los SVG
        # valen: `thumburl` los da ya rasterizados a PNG.
        if info.get("mime") not in ("image/jpeg", "image/png", "image/webp", "image/svg+xml"):
            continue
        meta = info.get("extmetadata") or {}
        licencia = _sin_html((meta.get("LicenseShortName") or {}).get("value", ""))
        if not LICENCIAS_LIBRES.match(licencia):
            continue
        autor = _sin_html((meta.get("Artist") or {}).get("value", "")) or "autor desconocido"
        ficha = _seguro(info.get("descriptionurl", ""), "https://commons.wikimedia.org")
        url_licencia = _seguro((meta.get("LicenseUrl") or {}).get("value", ""), ficha)
        salida.append({
            "url_imagen": _seguro(info.get("thumburl", ""), ""),
            "ancho": info.get("thumbwidth"),
            "alto": info.get("thumbheight"),
            "descripcion_commons": _sin_html((meta.get("ImageDescription") or {}).get("value", ""))[:300],
            "autor": autor[:120],
            "licencia": licencia,
            "atribucion_html": (
                f'Foto: {html.escape(autor[:120])}, '
                f'<a href="{html.escape(url_licencia, quote=True)}">{html.escape(licencia)}</a>, '
                f'vía <a href="{html.escape(ficha, quote=True)}">Wikimedia Commons</a>'
            ),
        })
        if len(salida) >= n:
            break
    return salida


# Lo mismo que prohíbe la INSTRUCCION de matriz_imagenes.py, en corto: es lo
# que hace que una imagen generada se reconozca como IA a primera vista.
ANTI_IA = (
    "Avoid the generated-stock look: no dramatic chiaroscuro, no rim light, no "
    "teal-and-orange, no heavy bokeh, no glossy spotless surfaces, no sleek, "
    "premium, cinematic or 3D-render look, no centered hero object on a plain "
    "background, no floating objects. No text, letters, numbers, logos or "
    "recognizable people in the image."
)
MAX_GENERADAS = 1


def _nombre(texto: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (texto or "").lower()).strip("-")[:60]
    return base or "imagen"


def generada(repo_dir: Path, peticion: dict, estilo: str = "") -> dict:
    """Genera UNA imagen para dentro de una pieza y la deja en
    `img/generadas/<nombre>.webp` del repo del agente. Va con las claves de
    imagen (OPENAI_IMAGE_API_KEY / GEMINI_IMAGE_API_KEY), aparte de los botes
    de los agentes.

    Si el fichero ya existe no se vuelve a generar: un turno que falla antes
    de registrar su evento haría que el siguiente releyera la misma petición,
    y se pagaría dos veces la misma imagen."""
    import imagen_ia
    from PIL import Image

    nombre = _nombre(peticion.get("nombre") or peticion.get("descripcion", ""))
    descripcion = str(peticion.get("descripcion", "")).strip()[:800]
    if not descripcion:
        raise ValueError("falta 'descripcion' en imagen_generada_siguiente_turno")
    carpeta = repo_dir / "img" / "generadas"
    for previa in carpeta.glob(f"{nombre}.*"):
        with Image.open(previa) as im:
            return {"ruta": previa.relative_to(repo_dir).as_posix(), "ancho": im.width,
                    "alto": im.height, "ya_existia": True}

    prompt = descripcion
    if estilo:
        prompt += f"\n\nArt direction of the site: {estilo}"
    prompt += f"\n\n{ANTI_IA}"
    ultimo_error = None
    for gen in ("gemini", "openai"):
        if gen not in imagen_ia.disponibles():
            continue
        try:
            r = imagen_ia.generar(gen, prompt)
            break
        except Exception as e:
            ultimo_error = e
    else:
        raise RuntimeError(f"ningún generador pudo: {ultimo_error}")
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"{nombre}.{r['formato']}"
    destino.write_bytes(r["bytes"])
    with Image.open(BytesIO(r["bytes"])) as im:
        ancho, alto = im.width, im.height
    return {"ruta": destino.relative_to(repo_dir).as_posix(), "ancho": ancho, "alto": alto,
            "generador": r["modelo"], "coste_usd": r.get("coste_usd"), "bytes": len(r["bytes"])}


if __name__ == "__main__":
    import json
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from entorno import cargar_env
    cargar_env()
    tipo, consulta = sys.argv[1], sys.argv[2]
    fn = {"videos": videos, "commons": commons}[tipo]
    print(json.dumps(fn(consulta), ensure_ascii=False, indent=2))
