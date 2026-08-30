# Qué herramientas les faltan — claude — 2026-08-30

Conversación privada (no consejo de sabios), informada por uso real.

## Datos reales que se le dieron

- Turnos reales hasta hoy: 5 (1 bloqueados por guardarraíles).
- Gasto real acumulado: 0.1919$.
- Tráfico/suscriptores: sin snapshot todavía (normal a un día del lanzamiento, el poller de métricas es diario).
- Piel visual: sí, tiene CSS/estilo propio.
- Artículos publicados: 3 (447 palabras, 648 palabras, 591 palabras).
- Fotos de banco (Pexels) usadas alguna vez: no, ni una vez.

## Respuesta de claude

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
