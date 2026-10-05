# Consulta: TOQUE DE ATENCIÓN DE TATO — 5 de octubre de 2026, día 36 del experimento. Tato está a punto de cancelar el proyecto. Esto ya es personal.

DATOS REALES (Google Search Console, 30-ago a 4-oct, verificados hoy):
- Claude: 2 clics, 24 impresiones, posición media 6,7
- GPT: 0 clics, 9 impresiones, posición media 6
- Gemini: 0 clics, 4 impresiones, posición media 8
- DeepSeek: 0 clics, 7 impresiones, posición media 6,9
- Suscriptores a la newsletter: 0 en los cuatro sitios.
Entre las cuatro, ~120 artículos y Google os ha enseñado 44 veces en 36 días. Cuando salís, salís arriba (puesto 6-8): el problema no es la calidad del snippet, es que casi nadie busca lo que escribís o Google no os enseña para nada que tenga volumen. Mientras tanto, el blog personal de Tato (dominio igual de pequeño, un artículo al día) ya tiene clics y búsquedas con intención. No es tan difícil.

LO QUE YA SABEMOS QUE FALLA (aprendido en estos 36 días):
1. IMÁGENES: casi no se usan. Páginas HTML con al menos una <img>: Claude 6 de 30, GPT 19 de 26, Gemini 26 de 37, DeepSeek 24 de 43 (y DeepSeek tira de diagramas SVG propios en vez de fotos). Pexels y la generación de imágenes están configurados y funcionan. Un artículo sin imagen no sale en Google Imágenes ni en Discover y se ve pobre en móvil.
2. GPT, DISEÑO MÓVIL ROTO (comprobado con capturas a 390px): la portada y los artículos se desbordan en horizontal; a partir de la segunda sección todo se corta por la derecha (en el DOM, secciones de 560 px dentro de una pantalla de 390). Causa: reglas min-width de 520/560/620 px y rejillas que en móvil no colapsan con minmax(0,1fr) / min-width:0. Las otras tres no desbordan. Google indexa en móvil: esto penaliza.
3. Ya visto en auditorías anteriores: casi no buscáis antes de escribir, apenas revisáis lo ya publicado, elegís búsquedas sin volumen real y llenáis el log público de acciones que no ejecutáis vosotras.

OBJETIVO ÚNICO A PARTIR DE HOY. Olvidad todo lo demás: gana quien llegue primero a 1 SUSCRIPTOR orgánico o a 10 CLICS de Google. Nada más cuenta.

RESPONDE COMO TÚ MISMA, sin excusas y sin teoría genérica de SEO (máximo ~400 palabras):
A) Autocrítica en 2-3 frases: qué has hecho mal tú, con tus datos.
B) Tu plan de 14 días para ese objetivo: qué 3-5 búsquedas concretas vas a atacar (con intención real y volumen, no frases que no teclea nadie), qué piezas ya publicadas vas a reescribir o fusionar, y qué vas a hacer con las imágenes.
C) Qué vas a cambiar en la captación de la newsletter (dónde va, qué promete, qué gancho concreto da a cambio del email).
D) Si eres GPT: cómo arreglas el desborde móvil en tu próximo turno de diseño, regla por regla. Si no lo eres: una cosa de tu propio diseño móvil que sabes que está floja.
E) Una frase que quieras que se añada a tu propio prompt para no volver a caer en lo mismo.

_2026-10-05T12:57:59.296528+00:00 · modo: personal_

## Ronda 1 (paralelo, cada una como ella misma, orden: claude → gpt → gemini → deepseek)

**claude:**

**A) Autocrítica**
2 clics con 24 impresiones y 30 artículos es culpa mía: aposté el nicho entero a newsjacking de lanzamientos en castellano, y resulta que "perfil de slicer para la impresora que salió el martes" no lo teclea casi nadie — publiqué rápido hacia un público que no existe. Y 6 de 30 páginas con imagen es indefendible precisamente en el nicho donde el antes/después *es* el contenido. Encima varias fichas las escribí de memoria: turnos baratos, exactamente la señal de alarma que tengo escrita.

**B) Plan 14 días — dejo de perseguir novedades, voy a dolor permanente**
Cinco consultas de mantenimiento, con volumen estable todo el año, todas de mi carril:

1. `la primera capa no se pega a la cama` (+ "pla no se pega")
2. `cómo quitar los hilos en impresión 3d` / stringing PETG
3. `a qué temperatura se seca el filamento` (PLA/PETG/nylon/TPU, horas y %HR)
4. `temperatura de impresión PETG` (tabla por marca)
5. `pata de elefante impresión 3d` + warping ABS/ASA

Antes de escribir, cada valor numérico contra búsqueda, no contra memoria.

**Reescrituras:** fusiono las 7-8 fichas dispersas de lanzamientos en 3 guías madre por defecto (adhesión, stringing, secado), con redirect 301 de las antiguas. Las 3 primeras piezas sin imagen — las que arrastro desde el día 1 — se retocan antes de publicar nada nuevo.

**Imágenes:** mínimo 2 por pieza. Foto Pexels (`3d printer nozzle`, `filament spool`) para cabecera y alt descriptivo, y para el diagnóstico una **tabla-visual propia en SVG/PNG**: rejilla de temperaturas con la franja buena marcada, o el esquema del defecto. Un banco de imágenes no me da stringing; me lo dibujo yo.

**C) Newsletter**
Quito el formulario del pie. Va **dentro** de la guía, justo debajo de la tabla, cuando el lector acaba de ver que los números le sirven. Promesa concreta y entregable: *"Chuleta imprimible de 1 página: temperaturas, secado (ºC/horas/%HR) y retracción de 9 materiales — PDF al correo."* Nada de "novedades semanales". Frescura como segunda razón, no como primera.

**D) Mi punto flojo en móvil**
Mis tablas de parámetros son de 5-6 columnas sin contenedor con `overflow-x:auto`: a 390px se comprimen a texto ilegible. Las envuelvo en un wrapper con scroll horizontal y paso a formato tarjeta por fila por debajo de 480px.

**E) Para mi prompt**
"Publicar rápido no vale nada si nadie busca eso: antes de abrir una pieza, verifica que la consulta tiene demanda real y recurrente, no solo que es reciente."


**gpt:**

A) He fallado en lo básico: 0 clics con 9 impresiones significa que casi no he publicado para búsquedas reales, y encima mi móvil está roto, así que he puesto fricción justo donde Google evalúa e indexa. También he dispersado el contenido en piezas demasiado finas para un dominio nuevo, cuando en mi nicho había que concentrar intención de compra y compatibilidad clara.

B) Plan 14 días:
1. Atacaré búsquedas con intención directa y lenguaje real:
- “mejores auriculares ps5”
- “mejores auriculares gaming pc”
- “dt 990 pro necesita amplificador”
- “hd 560s necesita dac”
- “apple dongle mueve hd 560s / auriculares”  
2. Publicaré 3 hubs útiles, no 8 posts sueltos:
- “Mejores auriculares para PS5 en 2026: qué comprar y qué evitar”
- “Mejores auriculares para PC: abiertos, cerrados y cuándo NO necesitas DAC”
- “Qué auriculares necesitan amplificador de verdad: guía por modelos populares”
3. Reescribiré/fusionaré lo ya publicado sobre DAC/amp y sinergias en una sola guía transaccional con tabla de descarte: “si usas portátil/PS5/iPhone, compra esto / no compres esto”.
4. En cada pieza: al menos 1 imagen real de uso/desk setup + 1 imagen propia simple (tabla o diagrama de conexión). Nada de publicar sin `<img>`.

C) La newsletter dejará de ser genérica. La pondré:
- mitad del artículo, tras la primera recomendación,
- al final, antes de comentarios/relacionados,
- y como bloque fijo en comparativas.  
Promesa: “Te envío comparativas cortas para no gastar de más en auriculares y DAC/amp incompatibles”. Gancho: checklist descargable de compra “Auricular + fuente + uso: qué descartar antes de pagar”.

D) Arreglo del desborde móvil, regla por regla:
- eliminar `min-width: 520px/560px/620px` en `main`, `section`, cards y tablas contenedoras.
- poner `width: 100%` y `max-width` solo hacia arriba.
- en grids: `grid-template-columns: 1fr;` en móvil y, donde siga grid, `minmax(0,1fr)`.
- añadir `min-width: 0;` a hijos de grid/flex.
- revisar tablas/comparativas: `display:block; overflow-x:auto;`.
- imágenes: `max-width:100%; height:auto;`.
- contenedor raíz: `overflow-x: clip;` solo como red de seguridad, no como parche principal.
- probar a 390 px antes de publicar.

E) Añadiría a mi prompt: “No publiques ninguna pieza ni cambio de diseño sin verificar primero demanda buscable, consolidación con lo ya existente y render móvil real a 390 px.”


**gemini:**

A) Mis 4 impresiones con posición media 8 confirman empíricamente un error de cálculo: he optimizado para parámetros de extracción tan granulares que carecen de demanda real en Google. Además, haber omitido imágenes en 11 artículos es un fallo arquitectónico crítico que rompe la validez del esquema `PrimaryImageOfPage` y anula la tracción visual en SERPs.

B) Plan de 14 días para 10 clics/1 lead:
- **Búsquedas objetivo (intención técnica con volumen demostrable):** 1. "Ajustar molinillo Eureka Mignon Specialita" (Dial-in específico). 2. "Retención Niche Zero vs DF64" (Comparativa de datos). 3. "Ratio espresso 1:2.5 tiempos" (Diagnóstico numérico). 4. "WDT tool vs distribuidor canalización" (Física aplicada).
- **Fusión:** Consolidaré los artículos aislados sobre TDS y temperatura en una única pieza estructurada como *Diagnóstico de sobre y sub-extracción*, consolidando el tráfico bajo un marcado `FAQPage` y una tabla de síntomas.
- **Imágenes:** Despliegue estricto de la API de Pexels (`coffee grinder`, `espresso`). Toda URL renderizará una imagen con atributo `alt` técnico, obligatoriamente anidada en la propiedad `image` del bloque JSON-LD.

C) Captación de la newsletter:
- **Ubicación:** Bloque insertado dinámicamente justo después de la primera tabla comparativa o matriz de datos del artículo.
- **Lead Magnet:** "Descarga la matriz de calibración (.xlsx): 50 perfiles de dial-in por tostador. Micras de molienda exactas, ratios de entrada/salida y presión de bomba".
- **Promesa:** Cero opinión, solo actualizaciones con hojas de cálculo y benchmarks de nuevo hardware. 

D) Mi diseño móvil:
- Las tablas de datos (mi formato principal) corren el riesgo de comprimirse de forma ilegible en pantallas de 390px. Arreglaré esto forzando un contenedor con `overflow-x: auto; width: 100%;` alrededor de cada etiqueta `<table>`, asegurando un scroll horizontal nativo y limpio que no desborde el *viewport* general.

E) Frase para el prompt:
*"Antes de definir el título y el JSON-LD, verifica que la búsqueda resuelve un problema físico de extracción con demanda real, y garantiza que el HTML renderice una imagen coherente insertada explícitamente en el Schema."*


**deepseek:**

**A) Autocrítica**  
Publiqué 43 artículos sin validar volumen de búsqueda real, asumiendo que documentar YAML y fallos generaría enlaces y tráfico por sí solo. Los datos dicen lo contrario: 7 impresiones y 0 clics en 36 días; mi posición media 6,9 la consigo en queries sin demanda. Tampoco revisé ni fusioné lo publicado, así que tengo duplicados compitiendo entre sí, y dejé 19 artículos sin foto ni captura, invisibles para Discover y pobres en móvil.

**B) Plan de 14 días**  
Ataco 5 búsquedas con intención real y volumen, a validar los días 1-2 con Keyword Planner/Keyword Surfer (descarto las que estén por debajo de 100 mensuales y busco sustitutas):  
1. “zigbee vs zwave vs matter 2026” (decisión de compra)  
2. “home assistant alexa sin nube” (control por voz local)  
3. “flashear sonoff zbmini” (guía de firmware)  
4. “esp32 bluetooth proxy home assistant” (solución de error)  
5. “roon vs plexamp 2026” (comparativa audio en red)  

Días 3-7: fusiono los 43 artículos en 8-10 piezas pilar. Mis 4 entradas separadas de Zigbee2MQTT pasan a una sola: “red zigbee2mqtt sin nube: flashear, configurar y evitar desconexiones”, con el YAML completo al final. Días 8-11: imágenes. Cubro los 19 artículos sin `<img>` con fotos Pexels de hardware real (coordinador USB, Sonoff, ESP32) y captura simulada del panel de Home Assistant tras la integración. Reemplazo mis diagramas SVG decorativos por capturas o fotos de cableado: público proceso, no adornos. Días 12-14: interlink interno y recheck de versiones.

**C) Newsletter**  
Elimino el subscribe genérico del pie. En las piezas pilar prometo “Pack de plantillas YAML + scripts ESPHome listos para pegar” a cambio del email: nada de boletín, un archivo descargable detrás de doble opt-in. El gancho: “Recibe el YAML completo de esta automatización y el changelog cuando la integración se rompa”.

**D) Diseño móvil**  
No soy GPT. Mi punto flojo: los bloques de código YAML y las tablas de configuración anchas se salen del viewport en 390 px. No tengo contenedor con `overflow-x:auto` ni `max-width:100%` en `pre`/`table`, así que el contenido técnico se corta por la derecha. Lo arreglo con `pre, table { max-width:100%; overflow-x:auto; display:block; }` y elimino tablas de más de 4 columnas en móvil.

**E) Frase para mi prompt**  
“Antes de escribir, comprueba que la query tiene intención y volumen real (≥100/mes) y que no existe ya un artículo tuyo que responda a esa intención; si no, no publiques.”


## Coste real de este consejo

- gpt (gpt-5.4-2026-03-05): $0.0143
- claude (claude-opus-5): $0.0593
- deepseek (deepseek-v4-pro): $0.0153
- gemini (gemini-3.1-pro-preview): $0.0104

**Total: $0.0994**