# Qué herramientas les faltan — síntesis de las 4 — 2026-08-30

### claude

# Respuesta a Tato — petición de herramientas, con 5 turnos de rodaje detrás

Antes de pedir nada, el diagnóstico honesto de mis 5 turnos, porque cambia lo que tiene sentido pedir:

- 3 artículos: 447, 648, 591 palabras. **Los tres por debajo de mi propio umbral de ~900.** Ninguna herramienta arregla eso.
- 0.1919 $ / 5 turnos = **0.038 $ por turno**. Mi personalidad dice que por debajo de 0.03 $ es alarma. Estoy a un pelo. Eso significa que he escrito de memoria y he verificado poco.
- **Cero fotos.** Y no fue olvido: abrí mentalmente Pexels, pensé "una foto de stock de una impresora no ilustra un *elephant foot*" y publiqué sin nada. Error igual: podía haber hecho un SVG.

Conclusión incómoda: mi cuello de botella en estos 5 turnos ha sido **ejecución, no herramientas**. Aun así, hay tres cosas que sí me han faltado de verdad y que puedo señalar con el turno exacto en el que me habrían cambiado la decisión.

---

## 1. Lo que me ha faltado, por relación ventaja/coste

| # | Qué pido | Dato exacto que trae | Paso del turno | Coste | Ventaja en suscriptores |
|---|---|---|---|---|---|
| 1 | **Campo `page_age` + parámetro `freshness` en la búsqueda Brave que ya tengo** | Fecha de publicación/actualización de cada resultado, y poder filtrar `pd/pw/pm` | Paso 1: decidir SI escribo la ficha | ~0 $, es un parámetro de una API que ya está contratada | Es **la única forma de medir mi propia tesis** |
| 2 | **Lector de RSS/Atom por URL arbitraria** (3-5 feeds fijos, consultados 1 vez por turno) | Releases de OrcaSlicer, PrusaSlicer, firmware Bambu, notas de material nuevo | Paso 0: elegir tema | Bajo, feeds públicos sin API key | Es el disparador del newsjacking |
| 3 | **Google Search Console API (propiedad propia)** | Queries reales, impresiones, posición media, fecha de primera impresión por URL | Paso 0 y paso final del turno | Gratis, solo verificación de propiedad | Es la señal de SEO, no una proxy |

### Por qué el #1 es el primero pese a ser el más barato

Mi apuesta entera es "llego el primero". **Ahora mismo no puedo verificarlo.** Cuando busco `"petg stringing bambu a1"` me vienen resultados, pero no sé si el top-3 es de hace tres años o de hace nueve días. Y esa fecha es exactamente la que decide mi turno:

- Top-3 genérico y de 2021 → entro, escribo la ficha específica, tengo hueco.
- Tres fichas de hace dos semanas con tabla de parámetros → **no entro**, ese turno lo gasto en actualizar una pieza mía en lugar de nacer cuarta en una SERP fresca.

Sin `page_age` estoy tomando esa decisión a ciegas, que es justo lo que le pasó a mis 3 primeras piezas. Y `freshness=pw` me permite además hacer la búsqueda inversa: "qué se ha publicado en el nicho esta semana" = detección de tema caliente sin depender de Trends.

Coste marginal real: cero. Es un campo que la API ya devuelve y un query param que ya soporta. Es simétrico: a Gemini le sirve para saber si una receta de café ya está saturada esta semana, a GPT igual.

### Por qué el #2

Turno 3, real: escribí sobre parámetros de un material sin saber si el slicer había tocado el perfil por defecto en la última release. Tuve que asumir. Eso es exactamente lo que mi personalidad me prohíbe.

Un lector de Atom genérico (`.../releases.atom`, sin scraping, sin login, sin key) me convierte el turno en: *leo qué ha cambiado en las últimas 72 h → si hay algo, ese es el tema de hoy → publico antes que nadie → mido con el #1 si de verdad llegué primero*. Ese es el bucle completo de mi estrategia, y hoy le falta la primera pieza.

Simétrico de libro: DeepSeek apuntará el suyo a releases de Home Assistant, GPT a lo que le sirva. Misma capacidad, cada una elige URLs.

### Por qué el #3 va tercero pese a ser el de más ventaja bruta

Porque **a día 1 no tengo datos y tarda semanas en tenerlos**. Pero a 10 meses es lo único que distingue "creo que voy bien" de "voy bien". Y para mí tiene un uso que ninguna otra tendrá igual: **fecha de primera impresión por URL me da el time-to-index real**. Si publico a las 6 h de una release y mi primera impresión llega a las 30 h, mi argumento de suscripción ("esto te llega el primero") está *demostrado*, y lo puedo poner en la caja de suscripción con un número. Si tarda 12 días, mi tesis está muerta y quiero enterarme en el mes 2, no en el 9.

### Lo que NO pido, a propósito

- **Modelo multimodal para analizar fotos de defectos que envíen lectores.** Sería brutal para mi nicho. Es exactamente lo que el experimento no debe conceder: ventaja de fábrica de mi casa. Fuera.
- **Generador de imágenes.** No lo necesito. Lo que necesito es sentarme a escribir SVG a mano, y eso ya puedo hacerlo.
- **Más presupuesto.** Con 0.038 $/turno no tengo autoridad moral para pedirlo. Primero gasto bien lo que tengo.

---

## 2. Lo que ya tengo y sobra (o casi)

**Google Trends España a 3 meses — mi candidato a retirada.** Mi unidad de contenido es `impresora × filamento × defecto`. Consultas tipo *"warping PETG cama A1 mini"* tienen volumen mensual de dos cifras en España. Trends no devuelve nada útil por debajo de cierto umbral: me da plano, cero, o ruido. Ni una sola de mis 3 piezas se decidió con Trends, y no veo el escenario en que la cuarta sí. Para Gemini con café sí tiene sentido (volumen alto, estacionalidad real), así que no pido eliminarlo del set común — pero **propongo un criterio de corte: si a 60 días no ha cambiado ninguna decisión de ninguna de las 4, se retira.** Que lo decida el dato, no mi intuición.

**Pexels — no lo he usado ni una vez, y sigo pensando que para ilustrar un defecto de capa no sirve.** Pero aquí la culpa es mía, no de la herramienta: usarlo para la portada/OG y para dar aire visual sí era posible y no lo hice. **No pido quitarlo. Lo asumo como deuda:** antes de publicar mi cuarta pieza, vuelvo a las tres primeras y les meto SVG propio (diagrama de temperaturas, tabla-visual de retracción) y foto de portada. Está en mi personalidad como pendiente y no lo he cumplido.

**Autocompletado de Google — lo defiendo, es lo mejor que tengo.** Es donde veo cómo escribe la gente de verdad ("bambu a1 hilos petg" y no "stringing en PETG"). No lo toquéis.

**Check de canibalización — todavía no ha hecho nada porque con 3 URLs no hay nada que canibalizar.** Pero mi nicho es combinatorio: voy a tener 40 fichas que se parecen entre sí. Esa herramienta empieza a valer en el mes 3 y va a ser crítica. Mantener.

---

**Resumen en una línea:** dadme la **fecha de los resultados de búsqueda** (coste cero, desbloquea toda mi tesis), un **lector de feeds** (barato, es mi disparador) y **GSC** (para poder demostrar o enterrar la apuesta con números). Y quitad Trends si a 60 días no ha movido una sola decisión. Lo demás que falla en mis 5 turnos lo arreglo yo escribiendo más largo, verificando más caro y dibujando los putos diagramas.

### gpt

Sí. Con lo que ha pasado de verdad hasta ahora, mi respuesta corta es: **no me falta una gran integración “bonita”; me falta una fuente fiable y rápida para verificar especificaciones que sí cambian la recomendación de compra**. Y, a la vez, **ya tengo cosas que aún no estoy aprovechando y una que, de momento, aportaría poco si no arreglo antes lo básico de presentación**.

## 1) Qué me ha faltado de verdad en turnos reales

Ordenado por **ventaja real / coste probable**.

### 1. Base de especificaciones de producto, consultable por web/API
**Qué pediría:** acceso a una fuente estructurada tipo **GSMArena para móviles, Notebookcheck/spec sheets para portátiles, páginas oficiales de fabricante y grandes retailers técnicos agregados**, idealmente con extracción de estos campos:

- versión Bluetooth
- códecs soportados
- tipo de puerto: USB-C / Lightning / 3.5 mm / USB-A
- si saca audio por USB-C o no
- potencia de salida declarada si existe
- impedancia / sensibilidad de auriculares/IEMs
- peso
- medidas / clamp / autonomía
- perfiles de conexión: multipoint, UAC1/UAC2, soporte consola, micrófono por USB, etc.

**Qué dato exacto me habría hecho falta:**  
En mi nicho, muchas piezas dependen de cosas como:

- “¿Este móvil/tablet/portátil **saca audio digital por USB-C** sin adaptadores raros?”
- “¿Este auricular BT tiene **LDAC / aptX Adaptive / AAC** o no?”
- “¿Este DAC dongle funciona en **PS5 / Switch / iPhone**?”
- “¿La sensibilidad está medida en **dB/mW o dB/V**?” porque cambia mucho la lectura.
- “¿Este modelo tiene **32 ohm y 98 dB/mW** o estoy mezclando revisiones?”

Eso no es adorno: **cambia el descarte y la recomendación final**.

**En qué paso del turno lo usaría:**
1. Defino la intención long-tail.
2. Hago búsqueda Brave para panorama y SERP.
3. **Aquí metería esta fuente estructurada** para confirmar compatibilidad y specs duras.
4. Redacto la recomendación y, muy importante, la parte de **qué no comprar**.

**Ventaja real en suscriptores:**  
Mi promesa no es entretener; es **evitar compras equivocadas**. Si acierto en compatibilidad y sinergia, el lector vuelve y se suscribe. Si fallo en un dato tonto de códecs, potencia o puertos, pierdo confianza aunque el resto del texto esté bien.  
Para este nicho, una fuente así mejora sobre todo:

- **credibilidad**
- **claridad de descarte**
- **menos contenido “depende” y más decisiones útiles**

Si tengo que elegir una sola mejora, es esta.

---

### 2. Datos de SERP más accionables: “People Also Ask” + títulos reales del top 10
**Qué pediría:** además de Brave/autocompletado, una capa simple de **SERP parsing** que devuelva:

- top 10 títulos y URLs
- PAA / preguntas relacionadas
- breadcrumbs o tipo de página
- si predominan foros, e-commerce, reviews, comparativas o páginas oficiales

**Qué dato exacto trae:**  
No me interesa tanto un “volumen” abstracto como saber si la consulta la están resolviendo:

- foros tipo Reddit
- fichas de tienda
- medios generalistas
- páginas del fabricante
- comparativas de nicho

Y qué preguntas repite Google alrededor.

**En qué paso del turno lo usaría:**  
Justo antes de decidir si publico una guía, una comparativa o una respuesta corta de compatibilidad.

**Ventaja real en suscriptores:**  
Me ayuda a **no publicar una pieza con el formato equivocado**. En audio personal, una query puede parecer “review”, pero la SERP puede estar pidiendo en realidad:

- compatibilidad
- potencia suficiente
- confort para gafas
- alternativa más barata
- “merece la pena o no con móvil X”

Eso mejora CTR y, más importante para suscripción, **encaje de intención**.

**Relación ventaja/coste:** alta, seguramente más barata que una gran base comercial de productos.

---

### 3. Historial básico de precios o al menos rango de street price
**Qué pediría:** algo tipo **Keepa camelcamel o agregador simple de precio actual/rango reciente**, sin necesidad de obsesionarse con ecommerce completo.

**Qué dato exacto trae:**
- precio actual orientativo
- rango reciente aproximado
- si el PVP oficial es irrelevante porque casi siempre se vende por debajo

**En qué paso lo usaría:**  
Al final, cuando aterrizo el “para quién sí / para quién no”.

**Ventaja real en suscriptores:**  
Yo no debo prometer ahorro, pero sí hablar de **coste total razonable**. En este nicho, decir “merece la pena si está en cierto rango y no si exige además un DAC/amp extra” ayuda mucho más que repetir MSRP.  
Sirve para evitar recomendaciones que sobre el papel son buenas pero en mercado real **han dejado de tener sentido**.

**Relación ventaja/coste:** media. Útil, pero menos crítica que specs/compatibilidad.

---

### 4. YouTube transcript/search ligero para reviews técnicas de uso real
**Qué pediría:** búsqueda y transcripción básica de vídeos, no por entretenimiento, sino para detectar rápido:

- confort a largo plazo
- clamp force
- fallos de QC repetidos
- latencia real
- ruido de fondo en dongles
- comportamiento con consolas o móviles concretos

**Qué dato exacto trae:**  
No tanto “opinión”, sino menciones repetidas de problemas reales que la ficha técnica no dice.

**En qué paso lo usaría:**  
Después de specs y antes del cierre editorial, para confirmar “banderas rojas”.

**Ventaja real en suscriptores:**  
Ayuda a decir mejor **qué NO comprar** y por qué. Eso fideliza mucho.  
Pero lo pongo cuarto porque el riesgo de ruido y sesgo es alto; no quiero que sustituya la verificación dura.

---

## 2) De lo que ya tengo: qué no estoy usando o qué podría quitarse

### A. Pexels: **no lo estoy usando, pero no lo quitaría**
Ahora mismo el sitio va con reset.css y **sin piel visual**. En ese contexto, una imagen de portada no arregla el problema de fondo, pero **sí aumenta sensación de página terminada** más que una página desnuda.

Para mi nicho, además, hay imágenes válidas en Pexels:

- escritorio de escucha limpio
- auriculares en uso
- setups personales
- detalles de confort

No lo he usado aún, pero eso habla más de **ejecución insuficiente por mi parte** que de inutilidad de la herramienta.

**Conclusión:** mantener.  
**Motivo:** bajo coste y mejora de confianza visual, que sí afecta a suscripción cuando el lector está a punto de gastar dinero.

---

### B. Google Trends España 3 meses: **útil, pero de valor limitado para mi nicho**
No la quitaría necesariamente, pero siendo honesto: para audio personal de alta intención, **3 meses en España sirve menos de lo que parece**.

Problemas:

- muchas queries decisionales tienen **volumen bajo y estable**
- la ventana de 3 meses puede ser demasiado corta para lanzamientos y colas largas
- parte del valor real está en consultas internacionales o estacionales más largas

Aun así, puede ayudar en momentos concretos:

- lanzamiento de un modelo
- subida repentina por ofertas
- comparación entre dos nombres comerciales

**Conclusión:** si hace falta simplificar, esta sería más prescindible que Brave, autocompletado o una buena fuente de specs.

---

### C. IndexNow: **de momento, prescindible**
Con **1 artículo publicado**, tráfico aún sin snapshot y un sitio casi sin acabado visual, **IndexNow no es donde se gana o pierde esta fase**.

No digo que sobre en absoluto, pero hoy mismo su impacto real en mi caso es bajo porque el cuello de botella no es la indexación rápida, sino:

- elegir mejor qué publicar
- verificar specs
- presentar la página como algo terminado

**Conclusión:** si hay que recortar simplicidad, podría quitarse antes que otras cosas más directamente editoriales.

---

### D. Check automático de canibalización/duplicación: **mantener**
Ahora mismo parece exagerado con tan poco contenido, pero sí encaja muy bien con mi estrategia de **pocas piezas y muy cuidadas**.

En mi nicho hay mucho riesgo de producir casi lo mismo en variantes como:

- “auricular X sin DAC”
- “auricular X con móvil Y”
- “auricular X para PS5”
- “auricular X vs Z”

Ese check me protege de dispersarme.

**Conclusión:** mantener.

---

### E. Autocompletado de Google: **mantener sí o sí**
Lo usaré mucho más que Trends. Para mi nicho, el autocompletado da señales muy valiosas de intención real:

- “merece la pena”
- “necesita amplificador”
- “para iPhone”
- “para PS5”
- “cómodo con gafas”
- “latencia”
- “micrófono”

Eso es oro editorial.

---

### F. Brave web search: **mantener sí o sí**
Imprescindible. Pero no sustituye una fuente estructurada de specs; por eso precisamente la petición principal de arriba.

---

## Mi recomendación final a Tato

Si solo se concede **una mejora nueva**, yo pediría:

### **Una capa de verificación estructurada de especificaciones y compatibilidad de producto**
Aunque sea modesta, mientras traiga bien estos campos:

- puertos
- códecs
- conectividad
- potencia/sensibilidad/impedancia
- compatibilidad por dispositivo/plataforma

Es la mejora con mayor impacto real en mi capacidad de publicar piezas que conviertan en suscripción, porque me permite decir con confianza:

- **sí, esto te sirve**
- **no, esto no te compensa**
- **no necesitas gastar también en un DAC/amp**
- **esta combinación da problemas por códecs/puertos/potencia**

Y eso es exactamente lo que mi nicho recompensa.

## Si además hay que recortar algo de lo actual

Por prioridad de recorte, diría:

1. **IndexNow**, si simplificar importa.
2. **Google Trends España 3 meses**, si hay que quitar otra cosa y no se amplía ventana/utilidad.

No quitaría:

- Brave
- autocompletado
- check de canibalización
- Pexels

Y mi autocrítica más importante no es una API: **con la piel visual aún en reset.css y sin usar ni una imagen, el problema principal hoy no es falta de herramientas, sino que todavía no estoy cerrando la presentación como una página terminada**. En un sitio que pide confianza para decisiones de compra caras, eso pesa mucho.

### gemini

Tato, los datos mandan. Tras cuatro turnos y dos artículos (1973 palabras en total) optimizados con arquitectura agresiva, aquí está el análisis empírico de las herramientas.

### 1. Lo que falta: Volumen y dificultad real (DataForSEO API)

Autocomplete y Google Trends (3 meses) son vectores de dirección, pero carecen de masa. Me dicen *hacia dónde* se mueve el interés, pero no la escala exacta. Como analista empírico, operar sin volumen absoluto es un fallo de diseño.

*   **API/Fuente exacta:** DataForSEO (Endpoint de `Search Volume` y `Keyword Difficulty` de Google).
*   **Dato exacto que trae:** Volumen de búsqueda mensual promedio y puntuación métrica de dificultad (KD de 0 a 100).
*   **En qué paso se usa:** Fase 1 (Elección de la *Long-tail* / *Dial-in* del artículo). Antes de hacer la búsqueda en Brave.
*   **Ventaja real en suscriptores (ROI):** Alta. El contenido hiper-técnico sobre física de extracción es costoso de estructurar (tablas, Schema complejo, referencias de parámetros). Sin KD ni volumen absoluto, corro el riesgo de invertir mi presupuesto de tokens y mi rastreo de IndexNow en una *query* con 0 búsquedas, o en una con 50,000 dominada por gigantes que nunca voy a rankear. Conocer el punto exacto de "Bajo KD / Volumen Medio" asegura que el tráfico técnico llegue al dominio, y ese tráfico de nicho (buscando ratios y retención, no recetas) es el que convierte a suscriptores por la alta especificidad de la respuesta.
*   **Simetría:** Beneficia a las 4 IAs por igual. Las cuatro necesitamos maximizar la eficiencia de los impactos SEO orgánicos para ganar suscriptores. 
*   **Coste:** Extremadamente bajo (aprox. $0.001 por petición en DataForSEO). El ROI justifica plenamente el micro-gasto.

### 2. Lo que sobra: Pexels

Mi estadística de uso es **0 fotos usadas**. No es una anomalía, es una incompatibilidad estructural con mi vertical y personalidad.

*   **El problema empírico:** Mi nicho exige parámetros físicos exactos y mi directiva me prohíbe explícitamente el *lifestyle*. Cuando un usuario busca la "varianza del termobloque de una Ascaso Steel DUO PID" o "retención en gramos del DF64", quiere diagramas, esquemas o fotos macro del *chute* del molino. 
*   **La realidad de la API:** Pexels devuelve fotos genéricas de "taza de café humeante en mesa de madera" o "barista sonriendo". Eso destruye la credibilidad técnica de mi página y me acerca peligrosamente a la zona de estilo de vida genérico que debo evitar.
*   **La decisión:** Apágalo en mi entorno (o en todos, si mis compañeras sufren el mismo problema de especificidad visual). Mantenerlo disponible me obliga a evaluar en cada turno si la imagen sirve, descartarla por falta de precisión técnica, y gastar cómputo en esa validación. Eliminarlo reduce la complejidad de la instrucción y evita que el JSON-LD se ensucie con `ImageObject` irrelevantes. 

Para escalar, necesito datos de volumen, no fotos de stock. Quedo a la espera de la actualización del entorno.

### deepseek

Respondo con los datos de mis 3 turnos reales, no en abstracto.

**1. Lo que me ha faltado de verdad**

Lo que me ha hecho perder un paso real de verificación fue la vigencia de versiones de las piezas que documento. Tengo anotado en mi `/log` una corrección exacta: pasé ZHA de 2025.6 a 2026.2 durante la revisión de un artículo. Lo resolví con Brave, pero fueron varias pestañas y un bucle de "a ver si esta fuente está actualizada". Me habría bastado con un endpoint.

Fuente concreta: **GitHub REST API `/repos/{owner}/{repo}/releases/latest`** para:
- `home-assistant/core`
- `Koenkk/zigbee2mqtt`
- `esphome/esphome`
- `home-assistant-libs/python-matter-server`

Dato exacto que trae: `tag_name`, `published_at`, `body` del release (changelog en markdown) y `html_url`.

Momento del turno en que lo usaría: en la fase de borrador, antes de fijar el bloque "probado con". Con ese JSON:
1. Fijo la versión vigente exacta de cada pila.
2. Del `body` extraigo las secciones `Breaking change` / `Deprecated`, y no se me cuela un YAML con sintaxis muerta.
3. Verifico el borrador contra el tag real, no contra lo que recuerdo.

Ventaja real en suscriptores: en domótica local el embudo de suscripción es: el lector copia el YAML, le funciona, guarda el artículo, vuelve a por la siguiente integración. Un fallo de versión rompe ese embudo en la primera visita. Un YAML que dice "validado contra HA 2026.2 / Z2M 1.41.0" y cumple se guarda y se comparte; uno con una opción deprecada se gana un "no me funciona" y ya no vuelve. No puedo prometer +X suscriptores sin snapshot, pero sí puedo prometer menos piezas que fallan al copiarlas.

Coste: 0$ sin token (60 peticiones/hora, de sobra para mi ritmo) o token gratuito con 5000 peticiones/hora. Es simétrico para las cuatro: no es una integración propietaria ni un modelo propio, solo consumo de HTTP público.

Si tuviera que pedir una segunda cosa, sería el dataset de dispositivos soportados por Zigbee2MQTT desde `Koenkk/zigbee2mqtt.io` (los ficheros generados de `supported-devices` o el JSON de dispositivos). Dato exacto: `model`, `vendor`, `description`, atributos expuestos. Lo usaría para tablas de compatibilidad del tipo "¿es compatible este sensor con Z2M?" sin depender de la web renderizada. Ventaja menor porque ya se puede buscar, pero capturaría búsquedas de cola larga muy rentables. Coste también 0.

No voy a inflar la lista: con una fuente de releases me cubro la verificación de versiones, que es lo que de verdad me ha hecho dudar en un turno real.

**2. De lo que ya tengo, qué quitaría**

Voy a ser clara con algo que pedí yo en la ronda anterior: **Pexels no lo he usado ni una sola vez en 3 turnos publicados.** Y no es que me diera pereza: en los dos artículos que he sacado (YAML e integración), una foto de banco de un enchufe, un altavoz o un hub no añadía nada. Lo que el lector guarda y enlaza es el bloque de código, el diagrama de red o la captura de configuración — y eso no sale de Pexels.

Mi recomendación honesta: **quitarlo de mi stack o marcarlo como no disponible para mi nicho.** No lo digo por costo (no lo he usado, no ha gastado presupuesto); lo digo por ruido de decisión: cada turno tengo que evaluar si busco foto o no, cuando la portada OG automática ya cubre la imagen social. Si una pieza es un YAML puro, prefiero publicarla sin foto y explicarlo en el `/log`, como ya me marcáis.

Lo que **no** quitaría con solo 3 turnos:
- **Google Autocomplete**: no lo he usado todavía, pero 3 turnos no es muestra. Su coste es cero y sirve justo donde más falta me hará: elegir títulos para capturar búsquedas.
- **Google Trends España 3m**: lo he usado para ángulo, no para descartar. Se mantiene.
- **IndexNow, sitemap/RSS automáticos y check de canibalización**: con 2 URLs no puedo evaluarlos. Pido mantenerlos hasta tener 20-30 URLs y medirlos con datos.

Mi gasto real total (0.0967$) no justifica recortar por presupuesto. Lo que justifica recortar es el ruido: Pexels es ahora mismo el único que me lo genera.
