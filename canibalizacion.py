"""Detecta si dos agentes están atacando la misma keyword sin saberlo.

El filtro de guardarraíles vigila la canibalización DENTRO de cada web, pero
en fase 1 las 4 IAs son ciegas entre sí por diseño: nada impide que dos
elijan el mismo ángulo. Si pasa y no se detecta, se contamina la
comparación (dos agentes peleando por la misma SERP ya no miden su
estrategia, miden quién le gana al otro) y no habría forma de saberlo
después.

Es un aviso para Tato, no una corrección automática: intervenir cambiando
el nicho de un agente a mitad de experimento sería alterar justo lo que se
está midiendo. La decisión es humana, en el checkpoint.
"""
import re
from pathlib import Path

RE_TITLE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
RE_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
RE_TAGS = re.compile(r"<[^>]+>")

# Palabras que aparecen en cualquier título y no distinguen un tema de otro:
# sin filtrarlas, dos webs cualesquiera parecerían solaparse.
VACIAS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "a", "ante", "con", "en", "para", "por", "sin", "sobre", "tras", "y", "o",
    "que", "qué", "como", "cómo", "más", "mas", "es", "son", "su", "sus", "tu",
    "tus", "mi", "mis", "lo", "se", "no", "si", "sí", "ya", "muy", "todo",
    "toda", "todos", "todas", "este", "esta", "estos", "estas", "guia", "guía",
    "mejor", "mejores", "web", "blog", "newsletter", "2026", "2027",
    # Vocabulario del propio esqueleto y del experimento: lo comparten las 4
    # por construcción, así que solaparse en esto no significa nada.
    "nombre", "titular", "principal", "proyecto", "privacidad", "política",
    "politica", "suscríbete", "suscribete", "diario", "guerra", "battle",
    "descripción", "descripcion", "corta", "artículos", "articulos", "inicio",
}
# Marcas de que el agente todavía no ha vestido su web: comparar plantillas sin
# rellenar solo produce ruido.
PLACEHOLDERS = ("[NOMBRE", "[TITULAR", "[DESCRIPCIÓN", "[SUBDOMINIO")
MIN_SOLAPE = 3  # nº de términos temáticos compartidos para considerarlo sospechoso


def _terminos(repo_dir: Path) -> set[str]:
    """Vocabulario temático del agente, sacado de sus títulos y H1 — que es
    justo lo que compite en una SERP, no el cuerpo del texto."""
    terminos = set()
    for ruta in repo_dir.rglob("*.html"):
        rel = ruta.relative_to(repo_dir).as_posix()
        if rel in {"privacidad.html", "log.html", "404.html"} or rel.startswith("."):
            continue
        try:
            contenido = ruta.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(marca in contenido for marca in PLACEHOLDERS):
            continue  # esqueleto sin vestir: no hay nicho que comparar todavía
        for regex in (RE_TITLE, RE_H1):
            for bruto in regex.findall(contenido):
                texto = RE_TAGS.sub(" ", bruto).lower()
                for palabra in re.findall(r"[a-záéíóúñü]{4,}", texto):
                    if palabra not in VACIAS:
                        terminos.add(palabra)
    return terminos


def solapes(ias: list[str], base: str = "/root/aisb-") -> list[tuple[str, str, list[str]]]:
    """[(ia_a, ia_b, términos compartidos)] de cada par que se pisa."""
    vocabularios = {}
    for ia in ias:
        repo = Path(f"{base}{ia}")
        if repo.exists():
            vocabularios[ia] = _terminos(repo)

    encontrados = []
    nombres = sorted(vocabularios)
    for i, a in enumerate(nombres):
        for b in nombres[i + 1:]:
            comunes = vocabularios[a] & vocabularios[b]
            if len(comunes) >= MIN_SOLAPE:
                encontrados.append((a, b, sorted(comunes)))
    return encontrados
