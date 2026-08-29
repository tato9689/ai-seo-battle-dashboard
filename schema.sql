-- Esquema de la base de investigación del experimento AI SEO Battle.
-- Una fila = una acción/decisión de una de las 4 IAs, leída desde su /log.json público.

CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ia TEXT NOT NULL,                  -- claude | gpt | gemini | deepseek
    subdominio TEXT NOT NULL,          -- ej. claude.dominio.com
    evento_id TEXT NOT NULL,           -- id/slug estable dado por la propia IA, para deduplicar en cada poll
    timestamp TEXT NOT NULL,           -- ISO 8601 UTC, la marca que da la propia IA
    modelo_exacto TEXT,                -- ej. claude-sonnet-5
    tipo_tarea TEXT,                   -- ej. seo-onpage | contenido-newsletter | investigacion-competencia
    input_contexto TEXT,               -- JSON: qué vio la IA antes de actuar (métricas propias, y desde fase 2 señales de otras)
    razonamiento TEXT,                 -- texto libre, si el modelo lo da
    accion_tipo TEXT,                  -- ej. publicar-articulo | cambiar-meta | enviar-newsletter | cambiar-estrategia
    output_resumen TEXT,
    output_url TEXT,                   -- link a commit/versión completa para poder hacer diffs
    tokens_in INTEGER,
    tokens_out INTEGER,
    coste_estimado REAL,
    duracion_seg REAL,                 -- tiempo real de la llamada, para comparar velocidad entre modelos
    resultado TEXT,                    -- exito | error
    detalle_error TEXT,
    fase INTEGER,                      -- 1 (ciega) o 2 (inteligencia competitiva), derivada de timestamp vs checkpoint semana 5
    ingested_at TEXT NOT NULL,         -- cuándo lo recogió el poller (no cuándo ocurrió)
    UNIQUE(ia, evento_id)
);

CREATE INDEX IF NOT EXISTS idx_activity_ia ON activity_log(ia);
CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_activity_fase ON activity_log(fase);

-- Métricas de resultado (outcome), separadas de las acciones: responden a
-- "cómo sabe que le va bien a una IA" cruzando esto con activity_log por
-- ia + fecha. Una fila por IA y día.
CREATE TABLE IF NOT EXISTS metrics_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ia TEXT NOT NULL,
    fecha TEXT NOT NULL,               -- YYYY-MM-DD
    sesiones_ga4 INTEGER,
    usuarios_ga4 INTEGER,
    vistas_ga4 INTEGER,
    clics_gsc INTEGER,
    impresiones_gsc INTEGER,
    posicion_media_gsc REAL,
    suscriptores_totales INTEGER,
    suscriptores_netos_dia INTEGER,    -- altas menos bajas ese día
    -- Desglose por origen del alta. El leaderboard SOLO puntúa con
    -- suscriptores_organicos: el proyecto se promociona por su narrativa
    -- (LinkedIn/HN/Reddit) y ese tráfico de curiosidad contaminaría la
    -- métrica de "quién hace mejor SEO". Se captura en el alta (campo
    -- oculto del formulario, ver esqueleto-web/index.html) porque a
    -- posteriori es irreconstruible.
    suscriptores_organicos INTEGER,    -- llegó por buscador (google/bing/ddg...)
    suscriptores_meta INTEGER,         -- llegó por la promoción del experimento
    suscriptores_directos INTEGER,     -- sin referrer identificable
    tasa_apertura_ultimo_envio REAL,   -- % del último envío de newsletter, si hubo
    fuente TEXT,                       -- ga4 | gsc | listmonk | mixto
    ingested_at TEXT NOT NULL,
    UNIQUE(ia, fecha)
);

CREATE INDEX IF NOT EXISTS idx_metrics_ia ON metrics_snapshot(ia);
CREATE INDEX IF NOT EXISTS idx_metrics_fecha ON metrics_snapshot(fecha);
