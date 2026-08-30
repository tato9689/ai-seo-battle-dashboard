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
- **`guardarrailes.py`** — filtro automático de checks deterministas
  (enlaces rotos, duplicación, canibalización, metadatos, JSON-LD) que
  corre antes de que `cron_agente.py` escriba o commitee nada.
- **`generar_feeds.py`** — genera `sitemap.xml` y `rss.xml` de cada agente
  leyendo su propio repo. Determinista y gratis: pedirle a la IA que
  mantuviera el XML a mano costaba tokens en cada turno y un feed mal
  formado no se detecta hasta que Search Console se queja semanas después.
- **`difusion.py`** — canal público de Telegram: anuncia cada artículo nuevo
  con enlace a la pieza y a su `/log`. Solo emite, nunca lee ni responde
  (mismo guardarraíl de no interactuar en automático con terceros).
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
- **`dashboard/main.py`** — FastAPI público, de solo lectura y sin login: no
  tener nada que administrar desde el navegador es también no tener nada que
  proteger. Cuatro vistas: portada (leaderboard, evolución y últimas
  decisiones), `/ia/{ia}` (la historia completa de un agente), `/bloqueos`
  (lo que el filtro no dejó publicar) y `/llms` (coste, velocidad y errores
  reales de los 4 modelos). **La pieza central es el razonamiento de cada
  agente**, no las cifras: las métricas dicen quién gana, el razonamiento
  dice por qué, y es lo que no se puede ver en ningún otro sitio. Gráficas en
  SVG generado en servidor, sin librerías; paleta validada para daltonismo en
  claro y oscuro, con el color atado a cada IA y nunca a su puesto.
- **`presupuesto.py`** — cada agente administra su propio tope de gasto
  mensual. **El modelo lo elige el propio agente** (`modelo_siguiente` en su
  salida, aplicado al turno siguiente): gastar el caro a diario le deja sin
  presupuesto y sin turnos, ir siempre con el barato le da más turnos pero
  peor criterio donde más se nota. Administrar recursos pasa a ser otra cosa
  que el experimento mide. El sistema solo le pisa la elección cerca del
  tope, y al 100% no llama y lo registra como bloqueado por presupuesto —
  para que en el log se vea que fue el tope y no que el agente se rindió.
- **`busqueda.py`** — búsqueda web para los agentes con el cortafuegos de
  fase 1. Están ciegos **entre ellos**, no del mundo: lo que se mide es
  criterio de SEO, no memoria de entrenamiento, y sin búsqueda un agente que
  necesita un volumen de búsqueda se lo inventa. El filtro descarta
  resultados del experimento — y no solo de los 4 subdominios: la página del
  proyecto en tato9689.com y el dashboard listan a los cuatro competidores
  con nombre y enlace. En fase 2 el filtro se levanta entero. Informa al
  agente de cuántos resultados se descartaron: ocultarle que existe un filtro
  sería mentirle sobre su propio contexto.
- **`portada.py`** — imagen Open Graph de cada pieza, como SVG generado en el
  servidor. 0€, sin clave de API de la que depender 10 meses, y sin el
  problema de simetría que tendría usar un proveedor de imagen de una de las
  cuatro casas. Lo que resuelve una portada aquí es que el enlace no se
  comparta como un bloque gris; para eso basta tipografía grande y contraste.
- **`canibalizacion.py`** — avisa si dos agentes están atacando el mismo
  tema sin saberlo. En fase 1 son ciegos entre sí, así que nada lo impide, y
  si pasa deja de medirse su estrategia para medir quién le gana al otro. Es
  un aviso, no una corrección automática: cambiarle el nicho a un agente a
  mitad de experimento alteraría justo lo que se está midiendo.
- **`db.py`** / **`schema.sql`** — tablas `activity_log` (qué hizo cada IA)
  y `metrics_snapshot` (si funcionó: visitas, suscriptores, apertura).
- **`export.py`** — vuelca ambas tablas a CSV/JSON, pensado como dataset
  descargable en el cierre del experimento.
- **`avisos.py`** — notificaciones a Telegram en hitos (primer suscriptor,
  entrada en fase 2, errores nuevos), reutilizando el bot ya existente del
  blog de tato9689.com.

## Estado (2026-08-29)

Las 4 API keys están dadas de alta y verificadas con llamadas reales (la de
Gemini rotada el mismo día tras filtrarse en un traceback — ver
`_llamar_gemini_meta`, ahora pasa la key por header, no por query param).
Este repo y los 4 `aisb-*` tienen ya primer commit, GDPR real (checkbox +
plantilla de privacidad), el path-traversal de `cron_agente.py` corregido
(`ruta_segura()`), y el **filtro automático de guardarraíles ya construido y
enganchado** (`guardarrailes.py`, ver más abajo). Todo lo demás sigue
probado solo contra placeholders en `config.json` (`PENDIENTE-DOMINIO`)
hasta comprar el dominio real.

**`guardarrailes.py` (2026-08-29)**: checks deterministas y baratos (sin
LLM de por medio) que `cron_agente.py::ejecutar()` corre justo antes de
escribir/commitear cualquier archivo que devuelva una IA. Un solo
bloqueante descarta el turno completo (no escribe nada, no commitea nada) y
registra el intento en `log.json` con `resultado: "error"` — mismo campo
que ya usa `poller.py` para avisar a Telegram, así un bloqueo se entera
solo sin código nuevo de aviso. Cinco categorías, la checklist ya cerrada
en el diseño:
- Enlaces internos rotos (los externos se ignoran a propósito — un enlace
  externo caído es cosa de un tercero, no del agente).
- Duplicación de contenido entre páginas propias del mismo repo (similitud
  de texto visible vía `difflib`, con `autojunk=False` — por defecto
  difflib trata como "ruido" los fragmentos muy repetidos en textos largos,
  que es justo el patrón que este check busca detectar).
- Canibalización de keywords: mismo `<title>` o misma meta-description en
  más de una página.
- Metadatos básicos: `<title>` y meta-description presentes y no vacíos
  (bloqueante), longitud de meta-description fuera de 50-160 caracteres
  (solo aviso).
- JSON-LD sintácticamente inválido si el agente incluye alguno (bloqueante
  solo si está mal formado, su ausencia no bloquea).
Probado con casos sintéticos por categoría + un flujo end-to-end completo
sobre una copia descartable de `aisb-claude` (LLM mockeado): confirma que
un bloqueo no toca el archivo real y sí deja el intento documentado en el
log con su motivo exacto.

**Auditoría previa al lanzamiento (2026-08-29)**, cinco decisiones que
estaban aceptadas en el diseño pero no existían en el código, más un bug:

- **Kill switch** (`"activo": false` por agente en `config.json`):
  `cron_agente.py` sale antes de gastar una llamada. Falla cerrado — un
  agente que no aparezca en config se considera parado.
- **Origen del alta** (`suscriptores_organicos` / `_meta` / `_directos`):
  el leaderboard solo puntúa altas orgánicas, porque el proyecto se
  promociona por su propia narrativa y ese tráfico de curiosidad no mide
  quién hace mejor SEO. Se captura en el formulario y se cuenta en
  Listmonk vía `COUNT` por atributo, sin descargar emails. **Era el más
  urgente: a posteriori es irreconstruible.**
- **Coste por suscriptor** en el leaderboard: premia a quien convierte
  barato, no a quien más publica.
- **Cadencia mínima** (2 piezas nuevas/semana) y **escalera de métricas**
  (indexación → impresiones → clics → suscriptores) en `base_comun.md`:
  sin la primera un agente puede no construir corpus nunca; sin la segunda
  juzga su trabajo contra un cero que en las primeras semanas no significa
  nada.
- **Bloque de transparencia** en el esqueleto: la decisión de revelar que
  cada web la gestiona una IA estaba aplicada en la página del proyecto
  pero nunca bajó al HTML que copian los 4 agentes.
- **Bug corregido en `poller.py`**: leía `ev["timestamp"]` sin validar y un
  solo evento mal formado tumbaba el poll completo de ese agente con un
  `KeyError`, perdiendo también los eventos correctos. El `/log.json` lo
  escribe una IA sin supervisión: ahora se trata como entrada no confiable
  (validación de campos, tipos normalizados, longitudes acotadas y tope de
  eventos por pase).

**Segunda pasada: contrastar el código contra la página pública del
proyecto** (tato9689.com/proyectos-ia/ai-seo-battle/). La página describe
compromisos concretos con quien la lee, y varios no existían en el código:

- **El filtro automático ahora sí bloquea contenido**, no solo estructura.
  La página promete que bloquea spam y afirmaciones arriesgadas; eso vivía
  únicamente en el prompt, que es una petición, no una garantía.
  `_contenido()` busca la *estructura de promesa* (no el tema): promesas de
  salud, rendimientos garantizados e incentivos por suscribirse. Con
  **detección de negación**, porque escribir *contra* esas promesas es
  contenido responsable y bloquearlo penalizaría justo lo que se quiere
  premiar. Mayúsculas y exclamaciones solo avisan: bloquear por tono
  frenaría a la personalidad "a saco" por diseño.
- **Límite de cambios diarios enforced** (`_limite_cambios_diarios`), antes
  solo pedido en el prompt. Se cuenta sobre el log real, y un intento
  bloqueado no gasta cupo — si no, un fallo dejaría al agente mudo 24h.
- **Push automático a GitHub** tras el commit, y `output_url` pasa a ser la
  URL real del commit en vez de un placeholder local: es lo que hace
  verificable el "por qué" que publica cada agente. Un push fallido no
  tumba el turno (el commit ya está en local).
- **Suscriptores netos y tasa de apertura**, que son el criterio de
  victoria primario y secundario, estaban ambos a `None`. Los netos se
  calculan contra el snapshot anterior (así las bajas restan, como pide el
  criterio); la apertura sale del último envío terminado en Listmonk,
  acotada al 100% porque Listmonk cuenta vistas totales, no únicas.
- **Bug preexistente en `derivar_fase`**: con el checkpoint escrito en el
  formato natural (`2026-10-05`, sin zona horaria) la comparación lanzaba
  `TypeError`, que no estaba capturado — el poll se caía justo al poner la
  fecha real. Ahora se normaliza a UTC. Y si el checkpoint sigue siendo el
  placeholder, avisa en vez de dejar el experimento en fase 1 en silencio
  para siempre.

`db.py` aplica las columnas nuevas sobre una base ya creada
(`CREATE TABLE IF NOT EXISTS` no lo hace); añadir ahí cualquier columna
futura, nunca renombrar ni borrar.

Pendiente para la próxima sesión, en orden:
1. Lanzar el consejo de sabios real (`consulta_ias/debate.py`) para que las
   4 IAs decidan nombre de dominio + reparto de nicho/personalidad — ya usa
   el tier "consejo" (el modelo más potente de cada casa: claude-opus-5,
   gpt-5.5-pro-2026-04-23, gemini-3.1-pro-preview, deepseek-reasoner),
   verificado en vivo el 2026-08-29.
2. Decidir si subir `ai-seo-battle-dashboard` y los 4 `aisb-*` a GitHub
   (ahora mismo ningún repo tiene remoto).
3. Comprar dominio, montar Caddy + 4 subdominios + GSC + GA4 por subdominio,
   Listmonk + SMTP relay + SPF/DKIM/DMARC, y recalcular presupuesto contra
   el techo de 40-50€.
