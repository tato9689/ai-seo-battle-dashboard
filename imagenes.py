"""Banco de fotos gratuito para las 4 IAs, mismo patrón que `busqueda.py`.

Decisión del propio consejo de las 4 (acta "ronda de 3 preguntas",
2026-08-30): ninguna quiso fotos de banco por peso en el DOM/LCP y falta de
señal de ranking, y todas coincidieron en descartar generación por IA por
romper la simetría (cada casa tiene su propio modelo de imagen, con coste y
calidad distintos). Pedido por Tato el mismo día: que puedan probarlo de
verdad en vez de decidir sin haberlo tenido nunca disponible — así que se
construye la capacidad iguales para las 4, y sigue siendo su decisión usarla
o no en cada pieza.

Un único proveedor (Pexels) por lo mismo que `busqueda.py` usa un único
proveedor de búsqueda: si cada IA pudiera elegir proveedor de imagen, dejaría
de ser una comparación limpia. Pexels y no Unsplash/Pixabay: licencia sin
atribución obligatoria (la pides igual como buena práctica, pero un fallo en
el HTML de crédito no es un problema legal), límite gratuito generoso
(200 peticiones/hora) y respuesta directa en JSON sin pasos extra.

La clave sale del entorno, nunca del disco. Sin clave, falla limpio: un turno
sin imágenes es peor que uno bloqueado, así que quien llama a `buscar()` debe
tratar la excepción igual que hace `contexto_busqueda()` con las búsquedas.
"""
import os

import httpx

TIMEOUT = 20


def buscar(consulta: str, n: int = 3) -> list[dict]:
    """Hasta `n` fotos candidatas para `consulta`. Cada una trae ya
    construido el HTML de atribución (autor + enlace a Pexels), para que
    usarla bien sea copiar y pegar, no que el agente tenga que acordarse del
    formato exacto que exige la licencia."""
    clave = os.environ.get("PEXELS_API_KEY")
    if not clave:
        raise RuntimeError("sin PEXELS_API_KEY configurada")
    resp = httpx.get(
        "https://api.pexels.com/v1/search",
        params={"query": consulta, "per_page": n, "locale": "es-ES"},
        headers={"Authorization": clave},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    salida = []
    for foto in resp.json().get("photos", []):
        autor = foto.get("photographer", "desconocido")
        url_autor = foto.get("photographer_url", "https://www.pexels.com")
        url_foto = foto.get("url", "https://www.pexels.com")
        salida.append({
            "url_imagen": (foto.get("src") or {}).get("large", ""),
            "ancho": foto.get("width"),
            "alto": foto.get("height"),
            "descripcion_pexels": foto.get("alt", ""),
            "autor": autor,
            "atribucion_html": (
                f'Foto de <a href="{url_autor}">{autor}</a> en '
                f'<a href="{url_foto}">Pexels</a>'
            ),
        })
    return salida
