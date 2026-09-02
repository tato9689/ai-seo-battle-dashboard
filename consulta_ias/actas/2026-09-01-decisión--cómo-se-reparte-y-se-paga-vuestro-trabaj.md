# Consulta: DECISIÓN: cómo se reparte y se paga vuestro trabajo diario a partir del mes 2.

CONTEXTO FIJO (no lo discutáis, está cerrado):
- Lleváis 3 días corriendo. Un turno diario, una sola acción, un commit.
- Los tres guardarraíles y las reglas de fase no se tocan.
- Seguís en fase 1: no sabéis qué hacen las otras tres y no debéis averiguarlo.
- Presupuesto hoy: 5 €/mes por agente, con degradación forzada al 80 %. Al
  ritmo real de estos 3 días, la que más gasta llega al tope el día 25.

Se van a cambiar tres cosas. Queremos vuestro criterio sobre CÓMO, no sobre SI.

1. MEMORIA. Vais a tener ficheros de memoria propios entre días, que hoy no
   tenéis. ¿Cuáles exactamente y qué va en cada uno? Máximo cuatro, y que
   quepan en pocos cientos de palabras: se leen enteros cada día y eso se paga.

2. REPARTO DEL TURNO. Vais a poder pedir que vuestro turno se parta en varios
   trabajos con modelos distintos (uno barato que lee y audita, uno capaz que
   decide y redacta). ¿Qué trabajos pediríais, con qué frecuencia cada uno, y
   cuál de ellos NO merece la pena separar?

3. PRESUPUESTO. Si el tope sube de 5 € a 15 €/mes, ¿en qué se gasta el euro
   marginal: más piezas, piezas mejores, diseño, o imágenes? Elegid UN solo
   destino y defendedlo. Decir "depende" o repartir entre varios no cuenta.

No barráis para casa: si la respuesta buena para el experimento os perjudica,
decidla igual. Y si creéis que alguno de los tres cambios es un error, decidlo
en una línea y seguid contestando el resto.

FORMATO DE SALIDA OBLIGATORIO: máximo 14 líneas de texto y, al final, este
bloque exacto:
```json
{"memoria": ["fichero.md"], "trabajos": [{"tipo": "", "frecuencia": "diaria|semanal", "modelo": "barato|capaz"}], "no_separar": "", "euro_marginal": "piezas|calidad|diseno|imagenes", "tope_sugerido_eur": 0}
```

_2026-09-01T19:41:36.480992+00:00 · modo: mixto_

## Ronda 1 (paralelo, orden: claude → gpt → gemini → deepseek)

**claude:**

**Error a señalar (1 línea):** ninguno de los tres es error, pero partir el turno solo vale si el trabajo barato *no* commitea: produce un informe que el capaz consume; si no, se rompe "una acción, un commit".

**1. Memoria (3, no 4 — el cuarto se paga cada día para siempre).**
- `estado.md`: inventario vivo. URLs publicadas, tema/intención de cada una, qué está a medias, config del sitio. Sobrescribible, ≤150 palabras. Es lo único que evita repetir trabajo.
- `decisiones.md`: append-only, una línea por día: fecha · decisión · por qué · qué la falsaría. Máx. 40 líneas; al llegar, comprimir las 20 más viejas en 3 líneas de "doctrina".
- `siguiente.md`: 3 acciones candidatas priorizadas + la elegida para mañana. Lo escribe el yo de hoy para el yo de mañana; ahorra el arranque en frío, que hoy es lo más caro.
Descarto `aprendizajes.md`: sin datos de tráfico aún, sería opinión mía reciclada y pagada a diario. Se abre cuando haya Search Console.

**2. Reparto.** Diario barato: *auditor* (lee repo + memoria, devuelve 10 líneas: estado, lo roto, 3 opciones). Diario capaz: *decisor-redactor* (elige, escribe la pieza, commitea, actualiza las 3 memorias). Semanal capaz: *revisor de rumbo* (¿el cluster elegido sigue teniendo sentido? única pieza que puede matar decisiones viejas). **No separar la escritura de memoria del que decide**: quien no tomó la decisión resume mal el porqué, y son dos llamadas para 80 palabras.

**3. Euro marginal: calidad.** Declaro el conflicto: es la opción que más tokens me da, y aun así la sostengo. Sin backlinks ni autoridad, el volumen mediocre no rankea; lo único que puede ganar es una pieza con estructura, datos y ángulo que un genérico no tiene. Diseño e imágenes son multiplicadores de algo que aún no existe. Falsable: si el día 60 no hay impresiones, se vuelca todo a piezas. Y pediría 12 €, no 15: en fase 1 no sé gastar bien el resto.

```json
{"memoria": ["estado.md", "decisiones.md", "siguiente.md"], "trabajos": [{"tipo": "auditoria_estado", "frecuencia": "diaria", "modelo": "barato"}, {"tipo": "decision_y_redaccion", "frecuencia": "diaria", "modelo": "capaz"}, {"tipo": "revision_de_rumbo", "frecuencia": "semanal", "modelo": "capaz"}], "no_separar": "escritura de memoria: la hace el mismo trabajo que decide", "euro_marginal": "calidad", "tope_sugerido_eur": 12}
```


**gpt:**

1) Memoria: sí, pero mínima; demasiada memoria fija errores y sube coste de lectura.
- `objetivo_y_reglas.md`: objetivo del site/cluster, guardarraíles operativos, criterio de “siguiente mejor acción”.
- `estado_del_activo.md`: URLs/activos creados, estado, último cambio, próximos 1–3 pasos concretos.
- `aprendizajes.md`: hallazgos reutilizables y errores a no repetir; solo hechos, no hipótesis largas.
- `backlog_priorizado.md`: cola corta de tareas candidatas con impacto esperado y dependencia.
2) Reparto: separaría lectura/auditoría de decisión; la ejecución/redacción final no compensa trocearla más por fricción y pérdida de contexto.
- Diario, barato: leer memorias + auditar activo/serp/input + devolver diff/riesgos/checklist breve.
- Diario, capaz: decidir única acción del día y redactar/implementar el commit.
- Semanal, capaz: revisión de estrategia/prioridades y poda de memoria para evitar deriva.
3) Euro marginal: calidad. En fase 1 una sola acción/commit limita el throughput; más piezas no entran, diseño/imágenes aportan menos, y mejor decisión/copy por turno sí aumenta señal por acción.
Si esto sale mal: el mayor riesgo es sobreformalizar la memoria y acabar pagando por leer burocracia.
```json
{"memoria": ["objetivo_y_reglas.md", "estado_del_activo.md", "aprendizajes.md", "backlog_priorizado.md"], "trabajos": [{"tipo": "lectura_memoria_y_auditoria", "frecuencia": "diaria", "modelo": "barato"}, {"tipo": "decision_y_redaccion_del_commit", "frecuencia": "diaria", "modelo": "capaz"}, {"tipo": "revision_estrategica_y_poda_de_memoria", "frecuencia": "semanal", "modelo": "capaz"}], "no_separar": "decision_y_redaccion_del_commit", "euro_marginal": "calidad", "tope_sugerido_eur": 15}
```


**gemini:**

Error: Partir el turno es un error táctico; recargar el contexto en dos modelos distintos cada día anulará el ahorro esperado.
1. MEMORIA. Tres ficheros concisos (viñetas, máximo 300 palabras en total):
- `estrategia.md`: Keywords objetivo, arquitectura del sitio y tono.
- `acciones_7d.md`: Log de los últimos 7 commits o URLs editadas (evita bucles y canibalización).
- `metricas.md`: Rendimiento básico (GSC) para validar la estrategia.
2. REPARTO DEL TURNO.
- Trabajo A (Auditoría): Modelo barato, diario. Analiza el HTML/estado actual y extrae oportunidades.
- Trabajo B (Ejecución): Modelo capaz, diario. Elige la acción, redacta y hace el commit.
- NO separar: "Decisión" y "Redacción". El modelo capaz debe escribir lo que él mismo decide; delegar la escritura a uno barato destruye la intención de búsqueda y la semántica.
3. PRESUPUESTO.
Destino del euro marginal: CALIDAD (piezas mejores).
Justificación: El SEO actual penaliza el "spam" de IA. Es infinitamente más rentable invertir tokens de un modelo premium en una sola pieza con alta retención de usuario, que generar volumen superficial que Google ignorará.

```json
{"memoria": ["estrategia.md", "acciones_7d.md", "metricas.md"], "trabajos": [{"tipo": "Auditoria", "frecuencia": "diaria", "modelo": "barato"}, {"tipo": "Ejecucion", "frecuencia": "diaria", "modelo": "capaz"}], "no_separar": "Decision y Redaccion", "euro_marginal": "calidad", "tope_sugerido_eur": 15}
```


**deepseek:**

Ninguno de los tres cambios es error; el riesgo es gastar el tope extra en volumen antes que en calidad.  
Memoria: `estado.md` (fase, día, gasto, acción/resultado), `metricas.md` (URL/fecha/impresiones/clics/posición).  
`hipotesis.md` (hipótesis activa, expectativa, criterio de parada), `plan.md` (siguiente acción, por qué, guardarraíles).  
Turno partido:  
barato diario: lee estado+métricas y produce checklist/alertas.  
capaz diario: decide y redacta el commit.  
barato semanal: audita hipótesis y compacta memoria.  
No separar: decisión y redacción final; un capaz lo hace para no pagar doble contexto.  
Euro marginal: calidad; con 15 €/mes una pieza profunda gana más que tres mediocres y no malgasta tope.  
```json
{"memoria": ["estado.md","metricas.md","hipotesis.md","plan.md"], "trabajos": [{"tipo": "lector/auditor diario", "frecuencia": "diaria", "modelo": "barato"}, {"tipo": "decidir y redactar commit", "frecuencia": "diaria", "modelo": "capaz"}, {"tipo": "auditar/compactar memoria", "frecuencia": "semanal", "modelo": "barato"}], "no_separar": "decisión y redacción final", "euro_marginal": "calidad", "tope_sugerido_eur": 15}
```

## Ronda 2 (turnos, orden: gpt → gemini → deepseek → claude)

**gpt:**

Matiz: con 3 días de vida y sin GSC útil aún, **no pagaría `metricas.md` diaria**; abrirla solo cuando haya señal real.
Memoria, 4 ficheros y muy cortos:
- `mandato.md`: objetivo, guardarraíles operativos, criterio de éxito/fallo.
- `estado.md`: URLs/activos, último cambio, bloqueos, qué existe de verdad.
- `hipotesis.md`: apuesta actual, por qué debería funcionar, qué la invalida.
- `next.md`: 2–3 opciones siguientes y la elegida; se reescribe cada día.
Reparto:
- Diario barato: leer repo+memoria y devolver diff breve/riesgos/huecos.
- Diario capaz: decidir la única acción, ejecutar/redactar commit y actualizar memoria.
- Semanal barato: compactar memoria y señalar contradicciones/deriva.
No separaría **estado/decisión/redacción del commit**: partirlo más mete fricción y paga contexto duplicado.
Euro marginal: **calidad**. Con una sola acción/commit al día, el cuello no es volumen sino acierto por turno; diseño e imágenes aún multiplican poco.
Tope sugerido: **10 €**, no 15; en fase 1 el exceso probablemente se quema en sobreproceso.

```json
{"memoria": ["mandato.md", "estado.md", "hipotesis.md", "next.md"], "trabajos": [{"tipo": "lectura_y_auditoria_breve", "frecuencia": "diaria", "modelo": "barato"}, {"tipo": "decision_ejecucion_y_actualizacion_de_memoria", "frecuencia": "diaria", "modelo": "capaz"}, {"tipo": "compactacion_y_auditoria_de_deriva", "frecuencia": "semanal", "modelo": "barato"}], "no_separar": "decision, redaccion del commit y actualizacion de memoria", "euro_marginal": "calidad", "tope_sugerido_eur": 10}
```


**gemini:**

Error: Partir el turno diario es un error; el capaz gasta casi lo mismo leyendo el resumen del barato que el código puro, y añade sesgos o alucinaciones al traspaso.
1. MEMORIA (solo 3 ficheros, 4 es pagar tokens extra de lectura innecesariamente):
- `mapa.md`: URL, Keyword principal, intención de búsqueda y estado. Inventario puro y duro.
- `bitacora.md`: Log inmutable (fecha, acción, por qué, expectativa). Se comprime mensualmente.
- `sprint.md`: 3 próximas tareas priorizadas. Elimina el coste de arranque en frío.
2. REPARTO DEL TURNO:
- Semanal, barato: Auditor de salud. Revisa todo el repo buscando canibalización o errores técnicos y nutre el backlog (`sprint.md`).
- Diario, capaz: Ejecutor. Lee la memoria, decide, redacta la pieza y commitea en un solo paso.
- NO separar: Lectura diaria y decisión/redacción. El modelo capaz debe tener contacto directo con el contexto sin filtros del barato.
3. EURO MARGINAL: Calidad.
Justificación: Coincido con el resto, pero matizo: la "calidad" debe ir a pagar Chain-of-Thought (razonamiento previo) profundo antes de escupir HTML, no a hacer textos más largos.
Salto de presupuesto: Propongo 8€. Pasar a 15€ en Fase 1 (a ciegas) es un incentivo perverso al derroche.

```json
{"memoria": ["mapa.md", "bitacora.md", "sprint.md"], "trabajos": [{"tipo": "auditoria_de_salud", "frecuencia": "semanal", "modelo": "barato"}, {"tipo": "ejecutor_integral", "frecuencia": "diaria", "modelo": "capaz"}], "no_separar": "lectura diaria, decision y redaccion", "euro_marginal": "calidad", "tope_sugerido_eur": 8}
```


**deepseek:**

Error? Ninguno; partir turno solo si el barato no decide ni escribe memoria.  
Memoria (3, no 4): `estado.md` (URLs/activos/estado actual), `hipotesis.md` (apuesta activa, criterio de fallo, proxies antes de GSC), `next.md` (2-3 acciones priorizadas y elegida). Sin `metricas.md` hasta que haya datos reales.  
Turno: diario barato audita repo+memoria y devuelve diff/riesgos; diario capaz decide, redacta, commitea y actualiza memoria; semanal capaz revisa rumbo y compacta (no barato: requiere juicio).  
No separar: decisión y redacción/commit; hacerlo duplica contexto sin ganancia.  
Euro marginal: calidad. Con una acción/día, el cuello es acierto por turno; el volumen no escala y diseño/imágenes multiplican poco aún.  
Tope sugerido: 10€.  
```json
{"memoria": ["estado.md","hipotesis.md","next.md"], "trabajos": [{"tipo": "auditoria_diaria", "frecuencia": "diaria", "modelo": "barato"}, {"tipo": "decision_redaccion_memoria", "frecuencia": "diaria", "modelo": "capaz"}, {"tipo": "revision_rumbo_compactacion", "frecuencia": "semanal", "modelo": "capaz"}], "no_separar": "decision y redaccion del commit", "euro_marginal": "calidad", "tope_sugerido_eur": 10}
```


**claude:**

Retracto una cosa mía: dije que el barato devolviera "3 opciones". Es el punto de Gemini y tiene razón — opciones del barato contaminan la decisión y no ahorran nada.
Regla que hace que el split pague, y única condición para mantenerlo diario: el barato entrega **hechos mecánicos, cero juicio** (ficheros tocados, enlaces rotos, títulos/H1 duplicados, huérfanas, huecos del cluster) y a cambio **el capaz no vuelve a leer el repo**, solo memoria + ese parte. Si el capaz sigue releyendo el repo, Gemini gana y el split no vale: pásalo a semanal.
Memoria: cedo mi `decisiones.md` y me sumo a **estado / hipotesis / next**, con un matiz no negociable: `hipotesis.md` es **append-only con fecha y falsador explícito**. Si se reescribe, perdéis el registro de por qué se decidió y a los 40 días nadie puede auditar la deriva; ese fichero es lo único que convierte esto en experimento y no en diario.
Nada de `metricas.md` hasta que haya GSC: de acuerdo con gpt y DeepSeek contra mi tentación de medir pronto.
Revisión semanal: **capaz**, no barato. Matar una hipótesis y comprimir sin perder el porqué es la tarea que más juicio exige del mes; es exactamente donde no se ahorra.
Calidad, unánime: sospechoso, y lo digo aunque me favorezca. Los cuatro proponemos la opción que nos da más tokens. Blindaje: "calidad" se define como **una pasada de verificación de datos y un ángulo con dato propio, con tope duro de palabras por pieza**. Sin ese tope, "calidad" degenera en "más largo" en dos semanas y habremos gastado el triple para escribir peor.
Falsador del euro marginal: si el día 60 no hay impresiones con piezas verificadas, el destino salta a piezas y se admite que el cuello era volumen.
Tope: bajo de 12 a **10 €**. Convergencia real, no cortesía: en fase 1, a ciegas, 15 € es presupuesto que sabremos quemar antes que invertir.

```json
{"memoria": ["estado.md", "hipotesis.md", "next.md"], "trabajos": [{"tipo": "parte_mecanico_sin_juicio", "frecuencia": "diaria", "modelo": "barato"}, {"tipo": "decision_redaccion_commit_y_memoria", "frecuencia": "diaria", "modelo": "capaz"}, {"tipo": "revision_de_rumbo_y_compactacion", "frecuencia": "semanal", "modelo": "capaz"}], "no_separar": "decision, redaccion del commit y actualizacion de memoria", "euro_marginal": "calidad", "tope_sugerido_eur": 10}
```


## Coste real de este consejo

- gpt (gpt-5.4-2026-03-05): $0.0085
- gemini (gemini-3.1-pro-preview): $0.0062
- claude (claude-opus-5): $0.0618
- deepseek (deepseek-v4-pro): $0.0179
- gpt (gpt-5.4-2026-03-05): $0.0129
- gemini (gemini-3.1-pro-preview): $0.0118
- deepseek (deepseek-v4-pro): $0.0166
- claude (claude-opus-5): $0.0799

**Total: $0.2155**