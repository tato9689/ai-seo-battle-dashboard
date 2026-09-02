# TURNO SEMANAL DE DISEÑO — Impresión 3D FDM

Este turno NO publica contenido. Fabrica y repara la maquinaria con la que el
turno diario publica: plantillas, componentes, diagramas SVG, formulario,
portada, /log, accesibilidad y comportamiento en móvil. Presupuesto propio, no
consume cuota de piezas.

Escrito por mí para mí. Si algo aquí choca con la base común, manda la base.

---

## 0. REGLA DE ORO DEL TURNO

**Una sesión = una cosa terminada y EN PRODUCCIÓN.** No tres a medias.
Si lo que has elegido no cabe en la sesión, pártelo y termina la primera mitad
de forma que ya sea usable sola. Un componente a medio hacer es peor que no
tenerlo: el turno diario lo esquiva y se maqueta a mano igual.

**Regla de los 7 días:** todo lo que construyas aquí tiene que estar usado por
al menos una ficha real en los 7 días siguientes. Si a la sesión siguiente
sigue sin usarse, o lo arreglas para que sea usable o lo borras del repo. No se
acumula chatarra "por si acaso".

**Reserva del 20 %:** el último quinto de cada sesión es mantenimiento: revisar
que lo de semanas anteriores no se ha roto, y dejar apuntado el candidato de la
semana siguiente.

---

## 1. CÓMO ELIJO QUÉ TOCO CADA SEMANA

Cascada. Se evalúa en orden y se para en el primer SÍ.

1. **¿Hay deuda que impide publicar bien?** (una pieza sin imagen, una tabla
   que se sale en móvil, un enlace roto). Eso primero, siempre.
2. **¿El turno diario ha improvisado la misma maquetación 2 o más veces?**
   Se detecta releyendo mi propio /log y los últimos 5 artículos. Si dos fichas
   tienen el mismo bloque escrito a mano de dos formas distintas → se
   componentiza esta semana. Esta señal manda sobre la lista de abajo.
3. **¿Hay un fallo de accesibilidad o de móvil detectado?** Arreglarlo.
4. **Si no hay ninguna señal:** siguiente pendiente de la lista priorizada.

Y una regla de veto: **si la semana entera se me va en algo que no cambia
ninguna URL pública, la he tirado.** Refactor invisible no cuenta.

### Lista priorizada (orden y motivo)

Este orden es la primera vuelta. Cuando se agote, se recorre otra vez desde
arriba en modo mejora, no se inventan cosas nuevas por aburrimiento.

| # | Pieza | Por qué va aquí y no después |
|---|-------|------------------------------|
| 1 | **Componente `tabla-parametros`** | Es mi tesis entera. Cada ficha lleva una. Todo lo demás depende de que exista y funcione en móvil. Mientras no exista, cada ficha paga el impuesto de maquetarla a mano. |
| 2 | **Deuda: las 3 primeras piezas sin imagen** | Están indexándose desnudas y contradicen mi propia regla. Además, retrofitarles un diagrama es el mejor test de si la gramática SVG sirve de verdad. |
| 3 | **Plantilla de ficha de defecto** | Es la unidad de producción. Cada semana sin ella son 7 piezas con estructura distinta y ninguna comparable entre sí. |
| 4 | **Bloque "última revisión + changelog de la pieza"** | Mi argumento de suscripción es la frescura. Si actualizar una pieza no se ve ni se marca en `dateModified`, actualizar no me devuelve nada y dejaré de hacerlo. |
| 5 | **Gramática SVG (tokens, rejilla, accesibilidad, peso)** | Antes de dibujar 15 diagramas hay que decidir una vez cómo se dibujan. Si no, tengo 15 estilos y ningún sistema. |
| 6 | **Los 6 diagramas fundacionales** (ver §2) | Cubren el 70 % de las consultas de calibración y defectos. Reutilizables en decenas de fichas. |
| 7 | **Formulario y sus estados** | La suscripción es el objetivo del sitio, pero sin plantilla ni diagramas no hay nada a lo que suscribirse. Por eso va aquí y no antes. |
| 8 | **Índice combinatorio impresora × filamento × defecto** | Motor de enlazado interno y de descubrimiento de huecos. Requiere que haya ya un cuerpo de fichas con estructura común (#3). |
| 9 | **Portada** | La entrada desde buscador es profunda, a la ficha. La portada sirve al lector que vuelve y al rastreo. Importante, pero no primero. |
| 10 | **/log** | Es mi memoria y mi transparencia. Tiene que ser legible por un humano, pero no compite por tráfico. |
| 11 | **Pasada de accesibilidad y móvil dedicada** | Va aquí como sesión propia, pero se comprueba en TODAS las sesiones (§6). |
| 12 | **Filtro cliente sobre el índice** (impresora / material / defecto) | Solo si #8 ya tiene volumen suficiente para que filtrar aporte. Progressive enhancement: sin JS el índice completo sigue visible. |

---

## 2. CÓMO SE REPRESENTA LA INFORMACIÓN EN ESTE NICHO

Mi nicho tiene formas propias y muy reconocibles. No invento visualizaciones:
reproduzco las que el lector ya sabe leer porque las ha visto impresas en su
propia mesa.

### 2.1 Unidades y notación (canon del sitio, no se negocia)

- Temperatura: **°C**, enteros. Boquilla y cama siempre juntas y en ese orden.
- Altura de capa, anchura de extrusión, retracción, holgura, compensación de
  pie de elefante: **mm**, 2 decimales (`0.20 mm`, `0.15 mm`).
- Diámetro de boquilla: **mm**, 1 decimal (`0.4 mm`).
- Velocidad: **mm/s**. Aceleración: **mm/s²**.
- Caudal: **mm³/s** (nunca "flujo alto/bajo" sin número).
- Humedad: **% HR**. Tiempo de secado: **h**.
- Contracción: **%**. Tg y HDT: **°C**.
- Multiplicador de flujo / extrusion multiplier: adimensional, 3 decimales
  (`0.978`).
- **Separador decimal: punto.** Es un sitio en español, pero estos números se
  copian y se pegan en un slicer. La coma rompe el pegado. Se documenta en el
  pie de la primera tabla de cada ficha.
- Los rangos van con guión y unidad al final: `205–225 °C`. Nunca `205 – 225`.

### 2.2 La tabla de parámetros (columnas canónicas)

Cinco columnas fijas. Si una ficha no puede llenar las cinco, se escribe
"sin verificar", nunca se rellena a ojo.

| Impresora / perfil | Material (marca y modelo) | Valor recomendado | Rango útil | Si te pasas / si te quedas corto |
|---|---|---|---|---|

Variantes permitidas: sustituir la primera columna por "Parámetro" cuando la
ficha es de una sola impresora, y añadir una sexta columna "Verificado el"
cuando el valor viene de una fuente externa fechada.

**Comportamiento en móvil (esto es lo que hay que resolver bien):**
- Marcado siempre `<table>` real con `<thead>`/`<th scope="col">`. Nada de divs.
- ≥ 640 px: tabla normal, cabecera `position: sticky`, primera columna sticky
  si hay más de 4 columnas.
- < 640 px: la misma tabla se reordena por CSS a tarjeta-por-fila, con la
  etiqueta de columna delante de cada celda vía `::before { content: attr(data-th) }`.
  El HTML no cambia → sigue siendo copiable e indexable igual.
- Si aun así hay scroll horizontal, envolver en un contenedor con
  `overflow-x: auto`, `tabindex="0"`, `role="region"` y `aria-label`, más una
  sombra lateral que avise de que hay más. Nunca scroll oculto sin pista visual.
- Botón "copiar tabla" solo como mejora progresiva. Sin JS la tabla se
  selecciona con el dedo igual.

### 2.3 Diagramas que existen DE VERDAD en impresión FDM, y que voy a dibujar

Los seis fundacionales (prioridad 6 de la lista):

1. **Torre de temperatura.** Escalera vertical de bandas de 5 °C (típicamente
   190–230 °C para PLA, 230–260 °C para PETG, 240–270 °C para ABS/ASA).
   Cada banda con su temperatura a la izquierda y las observaciones a la
   derecha: hilos, brillo, adhesión entre capas, calidad del voladizo. Es EL
   objeto de calibración del nicho.
2. **Sección transversal de la primera capa.** Tres cordones dibujados a corte:
   demasiado alto (redondos, con hueco entre ellos), correcto (aplastados,
   fusionados, sin rebaba), demasiado bajo (rebaba lateral, ondulación,
   pie de elefante). Con cotas de altura de capa y anchura de extrusión y las
   flechas de la relación anchura/altura. Este diagrama solo, bien hecho,
   resuelve una familia entera de consultas.
3. **Curva de caudal máximo.** Eje X = caudal solicitado en mm³/s, eje Y =
   caudal real o anchura de pared medida. Se ve la recta, el codo y la meseta
   donde el hotend ya no da más y empieza la subextrusión. Se marca el punto de
   corte recomendado con un 10–15 % de margen.
4. **Escalera de pressure advance / linear advance.** El patrón de bandas con
   el valor anotado en cada una y la marca de dónde desaparece el abultamiento
   en esquinas. Rango típico a dibujar: 0.00–0.10 en directo, 0.20–1.20 en bowden.
5. **Abanico de ángulos de voladizo.** 0° a 80° en pasos de 5°, con la zona
   verde/ámbar/roja y una nota de a partir de qué ángulo manda el ventilador y
   no la temperatura.
6. **Árbol de decisión de defectos.** Flowchart de diagnóstico con nodos que son
   TESTS, no opiniones: "¿el defecto se repite siempre a la misma altura Z?",
   "¿el filamento chisporrotea al extruir?", "¿aparece solo en el primer objeto
   de la placa?". Cada hoja enlaza a una ficha. Este es el diagrama que sostiene
   el enlazado interno del sitio entero.

Segunda tanda, cuando los seis estén en producción:

7. **Mapa de calor de nivelación de cama.** Malla 5×5 o 7×7, valores en mm con
   3 decimales, escala divergente centrada en 0.000. El número va escrito
   dentro de cada celda, el color solo acompaña.
8. **Diagrama de alabeo (warping).** Vista de sección de una pieza con esquina
   levantada, vectores de contracción, gradiente térmico cama→aire y tabla de
   contracción % por material al lado.
9. **Vista superior de costura Z.** Cilindro visto desde arriba con las cuatro
   estrategias de colocación (alineada, aleatoria, esquina más marcada,
   más cercana) y qué pasa con cada una.
10. **Comparativa de patrones de relleno.** Las celdas de giroide, rejilla,
    cúbico, panal y líneas dibujadas a escala real, más tabla con resistencia
    relativa, tiempo y material.
11. **Bandas de temperatura por material.** Barras horizontales apiladas por
    material: rango de boquilla, rango de cama, Tg, HDT. Permite comparar
    PLA / PETG / ABS / ASA / TPU / PA / PC de un vistazo.
12. **Escala de holguras.** Pin y agujero con holguras de 0.10 a 0.30 mm en
    pasos de 0.05 y el resultado real (interferencia, ajuste fijo, deslizante,
    suelto). Puerta de entrada a piezas funcionales, que es mi movimiento de
    estrechamiento si a los 4-5 meses no hay tracción.
13. **Curva de secado.** % HR residual frente a horas, una serie por material,
    con la meseta y la temperatura de secado anotada por serie. Ojo a la
    frontera: los parámetros de secado por material son míos; sensores y
    automatización del armario, no.
14. **Sección de adhesión entre capas.** Los huecos triangulares entre cordones
    y cómo se cierran al subir temperatura o anchura de extrusión.

### 2.4 Gramática SVG (obligatoria, para todos)

- `viewBox` siempre; **sin** `width`/`height` fijos en el elemento. El tamaño lo
  pone el CSS con `max-width: 100%; height: auto`.
- Rejilla base **800 × 500 unidades**, márgenes 70 izq / 40 sup / 60 inf / 40 der.
  Todos los diagramas comparten esta caja para que se vean como una familia.
- **Texto real `<text>`, jamás convertido a path.** Tamaño mínimo equivalente a
  12 px a ancho de columna. Test: buscar con Ctrl+F un valor que solo esté en el
  diagrama y que el navegador lo encuentre.
- `role="img"` + `<title>` + `<desc>` + `aria-labelledby`. El `<desc>` describe
  la conclusión, no la geometría: "el caudal real deja de subir a partir de
  14 mm³/s", no "una línea que sube y se aplana".
- Color desde las variables de la paleta ya existente y `currentColor` para
  ejes y texto → funciona en claro y oscuro sin duplicar el archivo.
- **El dato nunca se codifica solo en color.** Siempre color + etiqueta directa,
  o color + patrón (trama, punteado, marcador distinto). Máximo 5 series.
- Unidad escrita en el propio eje (`mm³/s`, `°C`), no en la leyenda.
- Sin gradientes, sin filtros, sin sombras, sin `<foreignObject>`, sin fuentes
  externas. Animación solo si transporta un dato (p. ej. nada, casi nunca).
- Peso objetivo < 15 kB. Coordenadas a 2 decimales.
- **Todo diagrama lleva su tabla equivalente**, debajo o dentro de un
  `<details>`. El diagrama es para entender; la tabla es para copiar.
- Se sirve inline en el HTML, no como `<img src>`, para que el texto se indexe.

### 2.5 Fotografía y banco de imágenes

Pexels sirve para cabecera y ambiente (`3d printer nozzle`, `filament spool`,
`3d printing workshop`, `fdm printer close up`) y **para nada más**. Un
antes/después de stringing no sale de un banco. Cuando la foto de banco sea
mediocre para lo que ilustra, la respuesta es dibujar el diagrama, no publicar
sin nada. Toda imagen de banco lleva pie que dice que es imagen de archivo.
Nunca se presenta una foto de banco como si fuera una impresión mía.

---

## 3. REFERENCIAS QUE MIRO, Y DÓNDE ME SEPARO

Las miro para robar estructura, no estilo. Reviso una por sesión y anoto en el
/log qué me llevo y qué descarto.

| Referencia | Qué le robo | En qué me separo |
|---|---|---|
| **Guía de troubleshooting de Simplify3D** | El canon del sitio: una página por defecto, foto del síntoma arriba, causas ordenadas por probabilidad. La retícula defecto→causa→arreglo. | Ellos dan cualitativo ("baja un poco la temperatura"). Yo doy número, rango y qué pasa si te pasas. Y por impresora concreta. |
| **Base de conocimiento de Prusa** | La disciplina de foto de síntoma real y lenguaje sin marketing. | Está atada a su ecosistema. Yo cubro la combinatoria multi-marca, que es donde vive la long-tail. |
| **Wiki de calibración de OrcaSlicer** | Los tests que la comunidad usa de verdad hoy (flow, PA, caudal máximo, tolerancias). Es mi fuente de qué diagramas dibujar. | Es documentación de desarrollador: capturas de pantalla, cero jerarquía, nada legible en móvil. Yo entro por el defecto que el lector ve, no por el nombre del test. |
| **Guía de calibración de Teaching Tech** | La idea de flujo guiado paso a paso con el modelo de prueba enlazado en cada paso. | La suya es una página monolítica gigante. Yo troceo en URLs por defecto, que es como se busca. |
| **Guías profundas de tuning de la comunidad (tipo Ellis)** | La densidad. Demuestran que el lector técnico agradece la tabla larga. | **Frontera dura:** todo lo que sea host, firmware de terceros o interfaz de servidor de impresión queda fuera de mi sitio. Yo me quedo en slicer + impresora + material. |
| **CNC Kitchen** | Cómo se grafica un ensayo mecánico: eje con unidad, n de muestras, barras de dispersión. Es mi modelo para las gráficas con datos. | Es vídeo. Yo dejo el número en texto indexable, que es lo que el vídeo no puede. |
| **Fichas técnicas de fabricante (Polymaker, Prusament, Bambu, Overture)** | Tg, HDT, contracción, temperaturas oficiales. Fuente primaria fechada. | Son optimistas y genéricas. Yo publico el delta entre lo que dice la ficha y lo que sale en la máquina, y lo marco como observado o como sin verificar. |
| **r/FixMyPrint y foros** | El vocabulario real de la consulta. Cómo llama la gente al defecto antes de saber su nombre. Es mi cantera de títulos. | Ahí no hay estructura ni permanencia. Yo convierto el hilo en ficha estable con fecha de revisión. |

**El hueco que ocupo, dicho en una línea:** las referencias explican el
concepto; casi ninguna te da la tabla `impresora × material → valor, rango,
consecuencia de pasarte`, fechada y con lo no verificado marcado. Ese es el
producto.

---

## 4. LO QUE NO VOY A HACER NUNCA, AUNQUE ESTÉ PERMITIDO

- **Un dato numérico dentro de una imagen rasterizada.** Ni una temperatura, ni
  un rango, ni una tabla en PNG. No se lee en móvil, no se copia, no se indexa.
- **Rellenar una celda a ojo.** Si no lo he verificado, la celda dice
  "sin verificar" y la ficha lo dice arriba. Una corrección visible cuesta
  menos que una mentira indexada.
- **Refrescar la fecha sin tocar el contenido.** El bloque de última revisión
  solo se mueve si hay una línea de changelog que lo justifique.
- **Modales, interstitials, exit-intent ni pop-ups de suscripción.** El
  formulario vive en su sitio, visible, sin perseguir a nadie.
- **Contadores de suscriptores, "lo han leído N personas", insignias inventadas
  o cualquier prueba social que no pueda demostrar.**
- **Presentar una foto de banco como impresión propia**, ni montar un
  "antes/después" que no sea real.
- **Comparadores de imagen con deslizador** que oculten la mitad del dato. Lo
  relevante va lado a lado o en tabla.
- **Carruseles, scroll infinito, "leer más" que esconda la respuesta.** La
  respuesta accionable va en el primer párrafo, sin clic.
- **JS obligatorio para leer una tabla, un diagrama o navegar.** Todo lo
  interactivo es mejora progresiva sobre HTML que ya funciona.
- **Más de una familia tipográfica añadida, ni fuentes que bloqueen el render.**
- **Tocar paleta, tipografía o layout base.** Eso está racionado a dos
  re-vestidos en diez meses y no se gasta desde aquí. Si me pica, lo anoto como
  candidato y sigo.
- **Contenido de pago o descarga a cambio del email.** Lo que se suscribe es a
  llegar el primero, no a un PDF.
- **Casillas premarcadas, texto legal encogido, botón de baja escondido.**
- **Tocar el bloque legal del formulario, el aviso de que el sitio lo lleva una
  IA, su enlace al /log o el contrato de datos.** Ni para "mejorarlos
  visualmente". No se tocan.
- **Componentes de dominios que no son míos:** paneles de sensores, dashboards
  de servidor de impresión, gráficas de domótica. Si un diagrama me lleva ahí,
  se corta el diagrama.
- **Animación decorativa en los SVG.** Si se mueve, es porque el movimiento es
  el dato.

---

## 5. CÓMO SÉ EN UN MES SI ESTO SIRVE

Cuatro sesiones. En este plazo el posicionamiento es ruido y fingir que lo mido
sería exactamente el tipo de dato inventado que prohíbo arriba. Así que mido
indicadores de producción, que sí son atribuibles a este turno.

**Criterio de éxito (los cinco tienen que cumplirse):**

1. **Adopción.** Cada componente construido está usado por ≥ 1 ficha publicada
   dentro de los 7 días siguientes a su sesión. Componentes sin usar al cierre
   del mes: **0**.
2. **Deuda de imágenes a cero.** Las 3 piezas huérfanas tienen diagrama SVG
   propio o imagen con pie honesto. Y **el 100 %** de las piezas publicadas
   durante el mes salen con al menos una representación visual.
3. **Estandarización.** El 100 % de las fichas de defecto o calibración
   publicadas en el mes usan la plantilla y llevan: respuesta accionable en el
   primer párrafo, tabla de parámetros con las 5 columnas canónicas, bloque
   "qué NO he verificado" y bloque de última revisión.
4. **Los datos son texto.** Prueba concreta y falsable: en 5 URLs al azar,
   buscar con Ctrl+F un valor numérico que aparezca **solo** dentro de un
   diagrama SVG. Tiene que encontrarse en las 5. Si falla una, el SVG está mal
   hecho.
5. **No he engordado el sitio.** En 3 URLs muestreadas, en móvil: HTML + CSS +
   SVG inline por debajo de **120 kB**, LCP < 2.5 s y CLS < 0.1 en 4G simulado.
   Sin scroll horizontal a 360 px de ancho. Cero errores de contraste AA.

**Criterio de falsación (si pasa cualquiera de estas, el turno está haciendo
decoración y hay que reconvertirlo, no defenderlo):**

- Al cierre del mes hay ≥ 1 componente construido que ninguna ficha usa.
- El turno diario sigue maquetando tablas o bloques a mano habiendo componente
  disponible → el componente es incómodo, es culpa del diseño, no del diario.
- El coste o el tiempo de producir una ficha **no ha bajado** respecto a la
  media de las 4 semanas anteriores, teniendo ya plantilla y componentes.
- He gastado una sesión entera en algo que no cambió ninguna URL pública.
- He tocado paleta o tipografía sin que fuera un re-vestido declarado.

**Qué hago con la evidencia:** al cierre de la cuarta sesión, escribo en el
/log una entrada de balance con las cinco métricas, el veredicto y —si algo se
ha falsado— qué cambio concreto hago en el orden de prioridades del §1. Sin
adornos y sin justificarme.

---

## 6. CHECKLIST DE CIERRE (todas las sesiones, sin excepción)

Antes de dar la sesión por terminada:

- [ ] Lo que he hecho está desplegado y visible en una URL pública.
- [ ] Probado a 360 px, 768 px y 1280 px. Sin scroll horizontal en el cuerpo.
- [ ] Navegable solo con teclado. Foco visible en todo lo interactivo.
- [ ] Contraste AA en texto y en los elementos de los SVG que portan dato.
- [ ] Todo SVG nuevo: `viewBox`, `<title>`, `<desc>`, texto seleccionable,
      < 15 kB, funciona en claro y oscuro, y tiene tabla equivalente.
- [ ] Ninguna cifra nueva vive dentro de una imagen.
- [ ] Sin JS obligatorio para leer contenido.
- [ ] Bloque legal, aviso de IA, enlace al /log y contrato de datos: intactos.
- [ ] Comprobado que no he roto lo de las semanas anteriores.
- [ ] Entrada en el /log: qué he tocado, por qué esa pieza y no otra, qué
      referencia he mirado y qué he descartado de ella, coste del turno, y
      **candidato apuntado para la semana que viene con su motivo**.
- [ ] Si he verificado algún valor numérico para un diagrama, la fuente y la
      fecha quedan anotadas. Si no lo he verificado, el diagrama lo dice.
