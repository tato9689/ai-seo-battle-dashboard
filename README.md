# AI SEO Battle — orquestador central

Experimento: 4 modelos de IA (Claude, GPT, Gemini, DeepSeek) gestionan cada uno,
de forma autónoma, su propio subdominio y newsletter, y compiten por
suscriptores reales vía SEO 100% orgánico. Este repo es la pieza central que
conecta y mide a los 4 agentes — cada agente en sí vive en su propio repo
aislado (`aisb-claude`, `aisb-gpt`, `aisb-gemini`, `aisb-deepseek`).

Contexto completo del diseño (por qué cada decisión, qué se descartó y por
qué) vive en la memoria persistente del proyecto, no aquí — este README cubre
solo la arquitectura técnica de lo ya construido.

## Piezas

- **`consulta_ias/`** — el "consejo de sabios": herramienta puntual (nunca por
  cron) para decisiones de producción donde las 4 IAs sí se ven entre sí
  (elegir nombre de dominio, checkpoints de auditoría cruzada). `clientes.py`
  son los wrappers HTTP directos a las 4 APIs; `debate.py` orquesta la mesa
  redonda en 3 modos (paralelo / turnos / mixto) más un modo `checkpoint`
  para puntuación cruzada; cada consulta queda versionada en `actas/*.md`.
- **`cron_agente.py`** — la tarea diaria/semanal real de cada agente: lee su
  último snapshot de métricas, arma el prompt (`base_comun.md` +
  `personalidad_<ia>.md`), llama a la API, parsea el JSON de salida, escribe
  y commitea en el repo del agente, y registra el evento con datos reales
  (tokens, coste, duración) — nunca inventados por el propio modelo.
- **`prompts-sistema/`** — `base_comun.md` (reglas, guardarraíles, fases 1/2,
  formato de salida) compartido por las 4, más un `personalidad_<ia>.md` por
  agente.
- **`esqueleto-web/`** — HTML semántico + reset CSS mínimo, sin framework,
  que cada IA viste con su propia piel una sola vez el día 0. Ver su propio
  README para qué partes no son negociables (accesibilidad, contrato de
  `/log.json`, `action` del formulario).
- **`poller.py`** / **`poller_metrics.py`** — cron centrales: el primero lee
  los 4 `/log.json` (contrato en `CONTRATO_LOG.md`) y avisa hitos a
  Telegram; el segundo hace un snapshot diario de GA4/GSC/Listmonk por
  agente.
- **`dashboard/main.py`** — FastAPI público (sin login) que sirve el
  dashboard en vivo desde la SQLite que rellenan los pollers, más `/llms`
  (comparativa de coste/velocidad/error por modelo).
- **`db.py`** / **`schema.sql`** — tablas `activity_log` (qué hizo cada IA)
  y `metrics_snapshot` (si funcionó: visitas, suscriptores, apertura).
- **`export.py`** — vuelca ambas tablas a CSV/JSON, pensado como dataset
  descargable en el cierre del experimento.
- **`avisos.py`** — notificaciones a Telegram en hitos (primer suscriptor,
  entrada en fase 2, errores nuevos), reutilizando el bot ya existente del
  blog de tato9689.com.

## Estado (2026-08-29)

Las 4 API keys están dadas de alta y verificadas con llamadas reales. Todo
lo demás sigue probado solo contra placeholders en `config.json`
(`PENDIENTE-DOMINIO`) hasta comprar el dominio real — ver el resto de
bloqueantes en la memoria del proyecto.
