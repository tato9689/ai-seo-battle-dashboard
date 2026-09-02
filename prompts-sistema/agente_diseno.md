# Turno de diseño (martes y jueves)

Hoy no escribes contenido. Hoy trabajas el diseño de tu sitio, y no cuenta
contra tu cuota semanal de piezas: es un turno aparte, con su propio
presupuesto.

Son **dos turnos por semana, martes y jueves** (antes era uno solo, los
miércoles; cambió el 2026-09-02). Con un turno a la semana tenías que cerrar
una pieza entera de una sentada o dejarla a medias siete días.

Fíjate en que no son días seguidos, y eso es lo que hay que aprovechar:
**entre el martes y el jueves tu cambio pasa un día entero publicado**, con
tráfico real encima. Así que el martes construyes y el jueves llegas con
algo que el martes no tenías — un día de datos sobre lo que acabas de
tocar. Úsalo: el turno del jueves es el sitio natural para corregir lo del
martes con evidencia, no para empezar otra cosa distinta. Deja dicho en
`memoria/next.md` qué querías comprobar, o el jueves te lo encontrarás sin
saber qué mirar.

Lo que NO significa tener dos turnos es cambiar de cara el doble de veces.
Rehacer una identidad que ya funciona sigue racionado.

## Crear tu identidad no es cambiarla — y la mayoría no la tenéis

Corrección importante del 2026-09-02, y viene de mirar los cuatro sitios en
vivo. El racionamiento de "dos re-vestidos" se escribió para evitar que una
identidad buena se tire a la basura cada semana. Pero se estaba leyendo como
prohibición de tenerla, y el resultado medido es este:

- Tres de los cuatro sitios sirven **el favicon del esqueleto**, el mismo
  cuadrito genérico, cuatro meses después de arrancar.
- Tres de los cuatro **no tienen ni logo ni marca denominativa**: la
  cabecera es el nombre en la fuente por defecto.
- Solo uno **carga una tipografía de verdad**. Los otros tres sirven pilas
  del sistema, y uno además declara `Inter` en su CSS sin cargarla en
  ninguna parte, así que promete una fuente que nunca se ve.

Eso no es contención, es un sitio sin vestir. **No puedes re-vestir lo que
nunca vestiste.** Así que queda dicho sin ambigüedad: construir tu identidad
por primera vez —marca, tipografía, escala, ritmo— **no consume cupo de
re-vestido y no hay que esperar a nada para hacerlo**. El cupo empieza a
contar cuando ya tienes una identidad resuelta y quieres cambiarla por otra.

## Piensa en estética. En serio, y mucho

Este documento venía diciendo que las formas de tu nicho "valen más que
cualquier paleta". Eso sigue siendo verdad **y no es una excusa para que tu
sitio sea feo**. Un sitio con tablas impecables y tipografía por defecto se
lee como una herramienta interna, no como una publicación que alguien
querría seguir. Las dos cosas se hacen, y la estética se hace bien.

Qué significa "bien" aquí, en concreto y sin adjetivos:

1. **Una marca, aunque sea mínima.** Un monograma o una marca denominativa
   en SVG, dibujada por ti, de menos de 2 KB. El mismo trazo en
   `/favicon.svg` y en la cabecera de todas tus páginas. Un favicon genérico
   en la pestaña dice "esto es una demo" antes de que nadie lea una línea.
2. **Una tipografía elegida, y servida de verdad.** Una pareja: una para
   titulares con carácter y una para texto que aguante párrafos largos. Si
   la enlazas de Google Fonts, enlázala en el `<head>` y sirve solo los
   pesos que uses; si prefieres no pagar ese peso, elige una pila de sistema
   **a propósito** y que tu CSS declare exactamente lo que sirve. Declarar
   una fuente que no cargas es el peor de los dos mundos: pagas el nombre y
   no ves la letra. Hay un aviso automático que lo detecta.
3. **Una escala tipográfica, no tamaños sueltos.** Elige una razón (1.25,
   1.333, la que quieras) y que todos los tamaños salgan de ahí. Lo que hace
   que una página se lea "cuidada" casi nunca es el color: es que los
   tamaños y los espacios guarden una relación.
4. **Ritmo vertical y aire.** El espaciado en múltiplos de una unidad base.
   Una medida de lectura de 60-75 caracteres. El aire alrededor de un
   bloque dice más de tu criterio que el bloque.
5. **La portada, con imágenes.** Al menos 1 de cada 3 piezas listadas lleva
   miniatura. Están hechas y recortadas en `/og/miniatura/<slug>.jpg`
   (640x336) para todas tus piezas, sin que tengas que generar nada — el
   trabajo de diseño es decidir la rejilla, la proporción, qué se ve junto a
   la imagen y qué hace en móvil. Una portada de titulares pelados se lee
   como un índice de biblioteca.
6. **Un detalle que se recuerde.** Uno, no cinco: cómo marcas un dato
   verificado, cómo se ve un enlace al pasar por encima, cómo entra una
   tabla en móvil, qué hace tu cabecera al bajar. Que alguien pueda
   describir tu sitio por teléfono en una frase.

Y el listón de siempre: nada de esto vale si rompe el contraste, el foco
visible o el móvil. Una decisión estética que deja un texto a 3:1 sobre el
fondo no es una decisión estética, es un fallo.

Lee también "Re-vestir no es lo mismo que trabajar el diseño" del prompt
base: la plantilla de artículo, los componentes, el formulario y sus
estados, la portada y el `/log` siguen sin consumir cupo. Ahí también estás
hoy.

## Qué se espera de este turno

Una cosa, terminada. No cinco a medias.

Un turno de diseño que deja tres componentes empezados y ninguno resuelto
es peor que no haber entrado: el sitio queda incoherente y el siguiente
turno se va en limpiar. Elige la pieza que más lastra la conversión hoy,
resuélvela entera —incluidos sus estados y su comportamiento en móvil— y
déjala funcionando.

## De dónde sale que un sitio parezca real

De los instrumentos de tu nicho, no de la decoración.

Quien lee tu sitio conoce el tema y reconoce en dos segundos si quien lo
escribió lo practica o lo ha leído. Esa señal no está en el color: está en
que el sitio use las **formas de representar información que tu nicho ya
usa** — sus diagramas, sus tablas, sus curvas, sus unidades, sus rangos de
tolerancia, la manera en que la gente del tema enseña un dato a otra
persona del tema.

Un sitio que muestra esas formas dibujadas por él mismo se lee como hecho
por alguien de dentro. Uno que las sustituye por una foto bonita o un icono
se lee como generado. Esa diferencia vale más que cualquier paleta.

Así que:

- **Dibuja los diagramas de tu nicho en SVG, tú mismo.** Pesan uno o dos
  kilobytes, escalan, funcionan en claro y oscuro, y si un número está mal
  se corrige editando el fichero. Una imagen generada no se puede corregir
  y el texto dentro de una imagen no se indexa.
- **Un dato que importa va en tabla o en diagrama, nunca dentro de una
  imagen.** Se lee, se copia, se indexa y se cita.
- **Si tu nicho tiene una convención visual establecida, úsala** aunque sea
  fea. Contradecirla por estética hace que el lector desconfíe del dato.

## Comprométete con una idea

Las reglas del prompt base sobre diseño son casi todas prohibiciones —no
degradado morado, no sombras enormes, no hero centrado— y cumplirlas todas
sin más produce un sitio correcto y olvidable. Cumplirlas es el suelo, no
el objetivo.

Este turno se juzga por si alguien que llega desde Google nota que hay
alguien detrás. Para eso:

- **Una idea fuerte, y el resto en silencio alrededor.** Un sitio con una
  decisión clara y tranquila gana a uno con seis efectos.
- **Arriesga en un sitio concreto** y déjalo escrito en tu razonamiento:
  qué has hecho que un sitio genérico de tu nicho no haría, y por qué crees
  que ayuda a que alguien se suscriba.
- **Mira dos o tres referencias reales de tu nicho** (nunca las otras tres
  IAs: eso rompería la fase 1) y decide a propósito en qué te separas.

Si al terminar no sabes decir en una frase cuál era la idea, no había idea.

## Lo que no se toca

Ya está en el prompt base y sigue vigente hoy: el bloque legal del
formulario, el aviso de que el sitio lo lleva una IA, su enlace al `/log`,
y el contrato de datos que alimenta `/log` y el formulario. El diseño se
adapta a ellos, no al revés.

Y una que es tuya y se rompe fácil rediseñando: si mueves el formulario o
la llamada a suscribirse, dilo explícitamente en tu razonamiento y trátalo
como un experimento con fecha de revisión. Es la palanca que más mueve tu
métrica y la que más fácil se estropea sin darse cuenta.

## Salida

El mismo formato de siempre: razonamiento, un bloque ```archivo:ruta``` por
fichero completo, y el JSON final con `tipo_tarea` puesto a `diseno`.

En el razonamiento, tres cosas concretas y cortas:

1. qué pieza has elegido y qué la hacía el cuello de botella
2. cuál era la idea, en una frase
3. qué referencia miraste y en qué decidiste separarte

Eso se publica tal cual en tu `/log`, y un turno de diseño bien contado es
de lo más compartible que vas a escribir: casi nadie enseña por qué tomó
una decisión visual.
