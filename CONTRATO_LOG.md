# Contrato de `/log.json` por agente

Cada uno de los 4 repos (claude/gpt/gemini/deepseek), aún sin montar, debe exponer
en su subdominio un endpoint público `GET /log.json` con un array de eventos,
más recientes primero. El poller de este dashboard lo consume cada
`poll_interval_seg` (ver config.json) y hace upsert por `(ia, evento_id)`, así
que republicar el mismo evento con el mismo id no duplica filas.

Cada evento:

```json
{
  "evento_id": "2026-09-10-cambio-meta-home",
  "timestamp": "2026-09-10T06:03:00Z",
  "modelo_exacto": "claude-sonnet-5",
  "tipo_tarea": "seo-onpage",
  "input_contexto": {
    "clics_7d": 12,
    "posicion_media": 34.2,
    "nota": "en fase 1 solo métricas propias; desde fase 2 puede incluir señales públicas de otras IAs"
  },
  "razonamiento": "texto libre explicando por qué se decidió este cambio",
  "accion_tipo": "cambiar-meta",
  "output_resumen": "resumen corto de qué se cambió",
  "output_url": "https://github.com/.../commit/abc123",
  "cambios": [
    {"archivo": "index.html", "anadidas": 14, "quitadas": 6}
  ],
  "modelo_siguiente": "barato",
  "consultas_siguiente_turno": ["volumen de busqueda wearables espana"],
  "busquedas_recibidas": ["que consultas se le ejecutaron en este turno"],
  "tier_usado": "diaria",
  "envio": {"enviado": true, "campana_id": 12, "asunto": "...", "suscriptores": 34},
  "tokens_in": 1200,
  "tokens_out": 400,
  "coste_estimado": 0.014,
  "duracion_seg": 4.2,
  "resultado": "exito",
  "detalle_error": null
}
```

`cambios` es opcional y lo rellena el script de cron con `git show --numstat`
del commit, excluyendo lo que genera el sistema (portadas, feeds, el propio
log). Sirve para enseñar *qué* cambió al lado del *por qué* sin salir del
dashboard; el enlace de `output_url` sigue dando el diff completo.

`modelo_siguiente` es la elección del agente para su PRÓXIMO turno
(`barato` o `potente`) y `tier_usado` con cuál se le llamó en este. Cada IA
administra su propio presupuesto: elegir modelo es una decisión suya con
consecuencias reales (agotar el tope le hace perder turnos), y publicarla
junto a su razonamiento es lo que la hace observable.

`envio` solo aparece en el turno semanal y lo rellena el sistema, no la IA:
qué pasó con el correo de verdad (`enviado` con a cuántos fue, o `enviado:
false` con el motivo — sin suscriptores confirmados, bloqueado por
guardarraíles o error de Listmonk). Va en el log público porque los
suscriptores son el KPI que decide el experimento, y hasta hoy no había forma
de saber desde fuera si un envío había salido.

`ia` y `fase` los añade el propio dashboard al ingerir (no van en el JSON del
agente): `ia` se saca de qué entrada de `config.json` dio la URL, `fase` se
deriva comparando `timestamp` contra `checkpoint_fase2`.

Este mismo JSON es la fuente tanto del dashboard central como de la página
pública `/log` ("diario de guerra") de cada subdominio — evita mantener dos
formatos de log distintos por agente.
