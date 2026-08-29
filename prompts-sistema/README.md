# Prompts de sistema — cómo se combinan

El system prompt real que recibe cada IA en su llamada diaria es la
concatenación de dos archivos:

```
base_comun.md + personalidad_<ia>.md
```

`base_comun.md` es idéntica para las 4 — ahí viven los 3 guardarraíles, las
reglas de fase 1/2 y el formato de salida obligatorio. Nunca dupliques esas
reglas dentro de un bloque de personalidad; si hace falta cambiar una regla
de seguridad, se cambia una vez en `base_comun.md` y afecta a las 4 IAs a
la vez.

`personalidad_<ia>.md` es el único bloque que varía — define el estilo,
prioridades y tono de cada agente, ya asignados: Claude (a saco/clickbait),
GPT (premium/minimalista), Gemini (data-driven/SEO técnico), DeepSeek (el
retador transparente).

Cada carpeta `/root/aisb-<ia>/` referenciará estos dos ficheros desde su
script de cron cuando se escriba (pendiente, ver su README) — no se copian
sueltos a cada repo para evitar que una de las 4 quede con una versión
vieja de `base_comun.md` tras un cambio de guardarraíles.

## Tiering de modelo por tipo de tarea (decisión ya tomada, pendiente de aplicar en el script)

El prompt de sistema es el mismo independientemente de qué variante del
modelo se invoque. La variante sí cambia según la tarea, decidido por el
script de cron, no por el propio prompt:

- Tarea diaria rutinaria (el cambio de copy/SEO de cada día): variante
  rápida/económica de la familia de cada IA.
- Tarea semanal (redactar y enviar la newsletter, lo único que lee una
  persona real de verdad): variante flagship de cada familia.

Motivo: la tarea diaria ocurre ~7 veces más que la semanal, así que el
ahorro de usar la variante barata ahí pesa mucho más en el presupuesto
total que usarla también en la newsletter — y es precisamente la
newsletter donde más importa la calidad del resultado.

## Pendiente antes de que esto se use de verdad

- Script de cron por agente que arme el prompt final (base + personalidad +
  contexto del día), llame a la API con el modelo correcto según tiering,
  parsee el bloque JSON de salida, escriba los archivos, commitee, y añada
  el evento al `/log.json` de ese agente.
- El filtro automático posterior (ver diseño de guardarraíles en dos capas
  en la memoria del proyecto) que revisa el output antes de publicarlo.
- Plantilla legal real del texto de consentimiento GDPR, que sustituye el
  placeholder `[PENDIENTE]` del formulario en el esqueleto — sigue siendo
  bloqueante antes del primer email real.
