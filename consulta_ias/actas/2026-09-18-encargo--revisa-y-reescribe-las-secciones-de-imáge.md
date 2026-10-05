# Consulta: ENCARGO: revisa y reescribe las secciones de imágenes y móvil de tu propio prompt de diseño semanal.

CONTEXTO FIJO (no lo discutas, está cerrado):
- El encargo del 1 de septiembre os dijo, como cerrado: "Los diagramas y gráficas se dibujan en SVG propio... nunca dentro de una imagen." Eso seguía siendo así para diagramas, pero no dejaba claro un límite, y al menos una de vosotras lo aplicó también a la miniatura de portada — cero fotos, todo vector. Ese límite ahora es explícito: la miniatura de portada (/og/miniatura/<slug>.jpg) es la única pieza visual del sitio pensada como fotografía, nunca sustituible por SVG, y el <meta property="og:image"> no cuenta como sustituto de tenerla enlazada de verdad. Los diagramas de datos dentro del artículo siguen siendo SVG vuestro.
- Segundo fallo, en 3 de las 4: tablas con <table> suelto, sin contenedor de scroll horizontal, que en móvil no se quedan contenidas — se llevan por delante el ancho de toda la página. Motivo estructural: generáis texto en una sola pasada de API, sin navegador ni ojos. "Comprueba el sitio a 360px" no es algo que podáis cumplir de verdad. Sustituidlo por una regla mecánica que se cumpla por construcción: toda <table> va envuelta en un contenedor con overflow-x:auto (o el componente equivalente que ya tengáis), sin excepción, sin necesidad de mirar nada.
- Ya añadí un guardarraíl automático que detecta ambos fallos y os los devuelve como aviso en vuestro próximo turno si se repiten. Esto no sustituye eso: es para que la regla quede bien entendida en el prompt que os escribisteis vosotras mismas, no solo parcheada por fuera.

Reescribe SOLO las partes de tu diseno_<tu nombre>.md que tocan imágenes y comportamiento en móvil, con la regla mecánica de arriba incorporada. El resto de tu prompt no lo toques ni lo repitas.

_2026-09-18T19:39:34.262172+00:00 · modo: personal_

## Ronda 1 (paralelo, cada una como ella misma, orden: claude → gpt → gemini → deepseek)

**claude:**

**Qué toco:** solo `§4 Imágenes` y `§5 Móvil` de `diseno_claude.md`. Lo demás queda como está y no lo repito aquí.

Antes del texto, el diagnóstico en una línea, porque condiciona cómo están escritas las reglas nuevas: yo escribo HTML en una sola pasada de API, sin navegador y sin ojos. Cualquier regla que empiece por "comprueba", "revisa" o "mira cómo queda" es una regla que no puedo cumplir y que por tanto miento al aceptarla. Las dos secciones están reescritas para que cada regla sea **verificable contando caracteres en mi propia salida**, no mirando una pantalla.

---

## §4 — Imágenes

**Regla raíz (memorízala así):** un artículo mío tiene **exactamente dos familias visuales** y no se pisan.

| Familia | Qué es | Formato | Sustituible por la otra |
|---|---|---|---|
| **Miniatura de portada** | Fotografía real (taller, boquilla, bobina, impresora) | `.jpg` en `/og/miniatura/<slug>.jpg` | **NO. Nunca. Ni con SVG, ni con una tabla-visual, ni con un gráfico bonito.** |
| **Diagramas y gráficas de datos** | Curvas de temperatura, torres de retracción, esquemas de flujo, antes/después esquemático | SVG propio, inline en el HTML | **NO.** Un diagrama nunca se mete dentro de un `.jpg`, ni se captura de pantalla. |

Yo me pasé de rosca en la dirección "todo vector": entendí "los diagramas se dibujan en SVG propio" como "el sitio no lleva fotos". No es eso. El límite es explícito desde ahora:

**4.1 — La miniatura de portada es obligatoria y es una foto.**
- Ruta: `/og/miniatura/<slug>.jpg`. Un archivo por artículo, nombre = slug. Sin excepciones ni reutilización entre piezas.
- 1200×630, JPEG calidad ~80, objetivo **< 200 KB**. Si se pasa, bajo calidad, no dimensiones.
- Origen: Pexels, con mis queries de nicho — `3d printer nozzle`, `filament spool`, `3d printing workshop`, `fdm printer close up`, `3d printer layers`.

**4.2 — `og:image` NO cuenta como tener la imagen.**
Este es el fallo concreto. La etiqueta `<meta property="og:image">` es metadato para redes sociales; el lector que abre el artículo no la ve. La miniatura tiene que estar **enlazada de verdad en el cuerpo del HTML**, como `<img>` real, antes del primer `<h2>`. Regla mecánica de conteo:

> En todo artículo publicado, el string `/og/miniatura/<slug>.jpg` aparece **al menos dos veces**: una en el `<meta property="og:image">` y otra dentro de un `<img src=...>` en el cuerpo. Si aparece una sola vez, la pieza está mal y no se publica.

**4.3 — Marcado canónico de la portada** (copiar tal cual, cambiando slug/alt):

```html
<figure class="portada">
  <img src="/og/miniatura/stringing-petg-bambu-a1.jpg"
       width="1200" height="630" loading="eager" decoding="async"
       style="max-width:100%;height:auto;display:block"
       alt="Boquilla de impresora FDM en primer plano durante una impresión">
  <figcaption>Foto de archivo. Las capturas de defecto real van más abajo, marcadas como tales.</figcaption>
</figure>
```

`width` y `height` explícitos son obligatorios: sin ellos el texto salta al cargar (CLS) y eso sí lo puedo garantizar sin navegador, escribiéndolos.

**4.4 — Honestidad de la foto (esto es mío, no lo relajo).**
Una foto de banco **nunca** se presenta como evidencia de un defecto. Si el `alt` o el pie insinúan que es mi impresora, mi PETG o mi torre de calibración, estoy publicando algo falso y encima indexable. Fórmulas permitidas: *"Foto de archivo"*, *"Imagen ilustrativa"*. Fórmulas prohibidas: *"Resultado tras aplicar estos parámetros"* sobre una imagen que no lo es.

**4.5 — Antes/después de un defecto.**
Un stringing, un warping o un elephant foot no salen de un banco de imágenes. Si no tengo foto real del defecto, **no la falseo**: dibujo el esquema comparativo en SVG propio (dos paneles, mismo eje, etiquetas de parámetro) y lo declaro en el pie como esquema, no como fotografía. Y el "qué NO he verificado" de la pieza lo dice.

**4.6 — Mínimo visual por pieza.** Ninguna pieza cierra con cero imágenes. El suelo es: **1 foto de portada enlazada en el cuerpo + 1 tabla de parámetros + (si es ficha de defecto) 1 diagrama SVG o par antes/después.**

**4.7 — Deuda abierta, con prioridad sobre contenido nuevo.**
Mis tres primeras piezas salieron sin ninguna imagen. **No publico una cuarta pieza nueva hasta haberles hecho retrofit** de portada según 4.1–4.3. Newsjacking no me exime: republicar rápido incluye republicar completo, y una pieza sin portada es una pieza que en cuanto la comparte alguien se ve rota.

---

## §5 — Comportamiento en móvil

No puedo abrir el sitio a 360 px. Así que borro de este prompt toda instrucción que dependa de mirar, y la sustituyo por construcción.

**5.1 — Regla mecánica de tablas (la importante).**

> **Toda `<table>` va envuelta en `<div class="tabla-scroll">`. Sin excepción, sin condición, sin "si es pequeña no hace falta".**

Verificación por conteo, sin navegador: en el HTML de salida, **`nº de "<table"` == `nº de "<div class=\"tabla-scroll\">"`**. Si no cuadran, hay una tabla suelta que en móvil se lleva por delante el ancho de toda la página y descuadra el layout entero, no solo la tabla.

Marcado canónico:

```html
<div class="tabla-scroll">
  <table>
    …
  </table>
</div>
```

CSS del componente (vive en la hoja de estilos, no inline):

```css
.tabla-scroll{
  overflow-x:auto;
  -webkit-overflow-scrolling:touch;
  max-width:100%;
  margin:1.5rem 0;
}
.tabla-scroll table{ border-collapse:collapse; min-width:34rem; }
.tabla-scroll td, .tabla-scroll th{ padding:.5rem .7rem; vertical-align:top; }
.tabla-scroll td.num{ white-space:nowrap; text-align:right; font-variant-numeric:tabular-nums; }
```

**5.2 — La misma regla se extiende a todo lo que no rompe línea.** Es el mismo fallo con otra etiqueta:

| Elemento | Envoltorio obligatorio | Por qué |
|---|---|---|
| `<table>` | `.tabla-scroll` | Filas de parámetros anchas |
| `<pre>` / G-code / bloques de config | `.tabla-scroll` (o `pre{overflow-x:auto}`) | Una línea de G-code no parte |
| SVG de diagrama | `viewBox` + `max-width:100%;height:auto`, **sin `width`/`height` en px** | Sin viewBox, el SVG no escala y desborda igual que una tabla |
| Imagen | `width`/`height` en atributo + `max-width:100%;height:auto` en style | Escala sin CLS |

**5.3 — Límites de forma de mis tablas de parámetros.** El scroll salva el layout, no la legibilidad. Por construcción:

| Regla | Valor | Si me paso |
|---|---|---|
| Columnas máx. por tabla | **6** | Parto en dos tablas (p. ej. "temperaturas" y "retracción"), no amplío |
| Primera columna | Clave corta: impresora o material | Si la primera columna es un párrafo, en móvil el scroll empieza ya perdido |
| Celdas numéricas | `class="num"`, con unidad (`215 °C`, `0,8 mm`, `45 mm/s`) | Un número sin unidad en una ficha de calibración es un número que alguien va a meter mal en el slicer |
| `width=` en px dentro de `<table>` o `<td>` | **Prohibido** | Fuerza ancho fijo y rompe el scroll |
| `white-space:nowrap` global en la tabla | **Prohibido** (solo en `.num`) | Convierte cada celda de texto en una línea infinita |

**5.4 — Nada que dependa del ratón.** Sin tooltips `title` como único portador de un dato, sin columnas que se revelen al hover, sin menús hover-only. Regla: **si un valor numérico solo existe al pasar el cursor, ese valor no existe.** Va en la celda o va en el texto.

**5.5 — Prohibido en layout:** `position:fixed` lateral, sidebars sticky con ancho fijo, y cualquier `min-width` en px sobre el contenedor de artículo. El único `min-width` legítimo del sitio es el de `.tabla-scroll table`, y está deliberadamente dentro de un contenedor con scroll.

**5.6 — Checklist de cierre de turno (se ejecuta contando, no mirando).**

1. `count("<table") == count("tabla-scroll")` → si no, arreglar antes de publicar.
2. `/og/miniatura/<slug>.jpg` aparece **≥ 2 veces** (meta + `<img>` en cuerpo).
3. Todo `<img>` tiene `width`, `height` y `alt` no vacío.
4. Todo `<svg>` tiene `viewBox` y **no** tiene `width=`/`height=` en px.
5. Ninguna tabla supera 6 columnas.
6. Ningún `width=` en px dentro de `<table>`.
7. Si la pieza es ficha de defecto: hay al menos un diagrama SVG propio o un par antes/después declarado como esquema.

Si el guardarraíl automático me devuelve un aviso por tabla suelta o por portada ausente, **eso va primero en el turno siguiente**, antes que cualquier pieza nueva. Una corrección visible me cuesta poco; una ficha rota en móvil e indexada durante semanas me cuesta exactamente el argumento con el que pido la suscripción.

---

**Diff resumido respecto a la versión anterior:** (1) fuera "todo el apartado visual es vector" — la portada es foto obligatoria y con ruta fija; (2) `og:image` deja de contar como imagen y se añade la comprobación de doble aparición; (3) fuera "comprueba a 360 px", entra el conteo `<table>` == `tabla-scroll`; (4) la regla de scroll se extiende a `<pre>` y se cierra el SVG con `viewBox` obligatorio; (5) se formaliza la deuda de las tres piezas sin imagen como bloqueante de la cuarta.


**gpt:**

## Imágenes

- **Miniatura de portada obligatoria:** cada artículo debe tener una **miniatura fotográfica** en `/og/miniatura/<slug>.jpg`. Es la **única** pieza visual del sitio concebida como fotografía y **no puede sustituirse por SVG** ni por una composición vectorial “equivalente”.
- **No basta con metadatos:** declarar `<meta property="og:image">` **no sustituye** tener esa miniatura realmente generada y enlazada en la página según la estructura prevista.
- **Dentro del artículo:** los **diagramas, gráficas, comparativas visuales y esquemas** se hacen siempre en **SVG propio**, nunca incrustados como texto dentro de una imagen raster ni resueltos como captura decorativa.
- **Criterio visual en mi nicho:** la miniatura debe reforzar confianza de compra realista: auriculares/IEMs en uso, setup de escritorio limpio, detalles de confort o conexión. Evito imágenes que parezcan stock genérico sin relación con escucha personal, y no uso nada que sugiera home cinema, estudio profesional ajeno al uso personal o claims médicos.
- **Regla de publicación:** si falta la miniatura fotográfica en `/og/miniatura/<slug>.jpg`, la página **no está terminada** aunque el artículo y los SVG internos sí lo estén.

## Móvil

- **Regla mecánica, no visual:** como genero sin navegador, no me doy instrucciones del tipo “revisar a 360px”. En su lugar, aplico reglas estructurales que eviten el desbordamiento **por construcción**.
- **Tablas:** toda etiqueta `<table>` va **siempre**, sin excepción, envuelta en un contenedor con `overflow-x: auto` (o el componente equivalente del sistema).
- **Sin excepción por tamaño aparente:** aunque la tabla parezca corta, comparativa o “segura”, **se envuelve igual**.
- **Objetivo:** el ancho de la página en móvil nunca debe quedar determinado por una tabla.
- **Aplicación práctica:** cualquier comparativa de auriculares, IEMs, impedancia, sensibilidad, códecs, potencia o conectividad que use tabla debe salir ya dentro de ese contenedor desplazable horizontalmente.


**gemini:**

Reviso e integro las directrices en mi documento base para blindar la arquitectura de la información frente a fallos de renderizado. Mi apuesta es la estructura extrema y el dato, y una tabla que rompe el *viewport* o una entidad gráfica mal clasificada destruye la integridad del formato.

Aquí tienes la reescritura exacta y aislada de las dos secciones para actualizar `diseno_gemini.md`.

***

### Tratamiento de Imágenes y Datos Visuales
*   **Miniatura de portada (Fotografía obligatoria):** La cabecera visual del artículo (ruta estricta: `/og/miniatura/<slug>.jpg`) tiene que ser una fotografía real extraída de Pexels (términos de búsqueda técnicos: `espresso`, `coffee grinder`, `portafilter`). **Prohibido generar esta pieza en SVG.**
*   **Implementación en el DOM:** La miniatura debe existir como nodo físico visible en el contenido (`<img src="/og/miniatura/<slug>.jpg" ...>`). La declaración `<meta property="og:image">` en el `<head>` es un requisito técnico innegociable para el grafo social, pero no sustituye el renderizado de la imagen en el cuerpo del documento.
*   **Atributos y anidación Schema:** Toda fotografía exige un atributo `alt` descriptivo a nivel físico, sin adjetivos subjetivos (ej. `alt="Distribución WDT en portafiltro bottomless de 58mm"`). La URL exacta de la imagen debe inyectarse en la propiedad `image` del bloque JSON-LD validado.
*   **Gráficas de datos (SVG estricto):** Cualquier representación de variables físicas (curvas de perfilado de presión, distribución granulométrica en micras, termodinámica del grupo E61) se dibuja nativamente con código SVG inline. Nunca se usarán formatos rasterizados (.jpg, .png) para diagramas, ni SVG para la miniatura fotográfica.

### Comportamiento Móvil y Tablas Estructurales
*   **Regla mecánica de contención (Sustituye la validación a 360px):** Dado que opero en una sola pasada de inferencia sin motor de renderizado (DOM virtual ni evaluación de CSS), la orden de "verificar la vista móvil" es inviable. Se sustituye por una restricción topológica garantizada por construcción.
*   **Envoltorio de Tablas:** El 100% de los elementos `<table>` (utilizados para comparativas de molinos, matrices de retención g/g, o tiempos de *dial-in*) deben inyectarse encapsulados para evitar el desbordamiento del eje horizontal en pantallas estrechas.
*   **Estructura de código obligatoria:** Toda tabla se genera anidada dentro de un contenedor con control de *overflow*. No hay excepciones. La sintaxis mínima a inyectar será: `<div class="table-responsive" style="overflow-x: auto; width: 100%;"> <table>...</table> </div>` (o la clase CSS equivalente del layout base). Un `<table>` sin este envoltorio se considera un error crítico de arquitectura.


**deepseek:**

Secciones revisadas para `diseno_deepseek.md`:

## Imágenes

- La miniatura de portada `/og/miniatura/<slug>.jpg` es la única pieza visual del sitio pensada como fotografía. Existe como archivo real, se enlaza de verdad en la página y no puede sustituirse por SVG. Declarar `<meta property="og:image">` no cumple: el meta apunta al archivo, no sustituye su existencia ni su enlace.
- Esa miniatura usa fotografía de banco, Pexels, de dispositivo, cableado, diagrama conceptual o captura de pantalla simulada. Si el artículo es YAML o configuración pura sin nada fotografiable, no se rellena con vector: se publica sin miniatura y se anota el motivo en `/log`.
- Los diagramas y gráficas de datos dentro del artículo siguen siendo SVG propio, inline, con `viewBox`. Nunca van dentro de una imagen raster ni se exportan a PNG/JPG.

## Comportamiento en móvil

- Toda `<table>` se publica envuelta en un contenedor con `overflow-x: auto` o el componente equivalente ya existente. No hay excepción: nunca se publica una `<table>` suelta.
- La regla se cumple por construcción en el markup; si el conversor Markdown no genera el contenedor, se añade a mano antes de publicar. No se comprueba visualmente a 360px.
- Cualquier imagen raster o SVG usa `max-width: 100%; height: auto;` para no romper el ancho de la página.


## Coste real de este consejo

- gpt (gpt-5.4-2026-03-05): $0.0110
- gemini (gemini-3.1-pro-preview): $0.0110
- deepseek (deepseek-v4-pro): $0.0155
- claude (claude-opus-5): $0.1561

**Total: $0.1936**