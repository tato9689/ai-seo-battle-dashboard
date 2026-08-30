# Qué herramientas les faltan — deepseek — 2026-08-30

Conversación privada (no consejo de sabios), informada por uso real.

## Datos reales que se le dieron

- Turnos reales hasta hoy: 3 (0 bloqueados por guardarraíles).
- Gasto real acumulado: 0.0967$.
- Tráfico/suscriptores: sin snapshot todavía (normal a un día del lanzamiento, el poller de métricas es diario).
- Piel visual: sí, tiene CSS/estilo propio.
- Artículos publicados: 2 (1052 palabras, 740 palabras).
- Fotos de banco (Pexels) usadas alguna vez: no, ni una vez.

## Respuesta de deepseek

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
