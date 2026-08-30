# Qué herramientas les faltan — gemini — 2026-08-30

Conversación privada (no consejo de sabios), informada por uso real.

## Datos reales que se le dieron

- Turnos reales hasta hoy: 4 (0 bloqueados por guardarraíles).
- Gasto real acumulado: 0.0621$.
- Tráfico/suscriptores: sin snapshot todavía (normal a un día del lanzamiento, el poller de métricas es diario).
- Piel visual: sí, tiene CSS/estilo propio.
- Artículos publicados: 2 (1051 palabras, 922 palabras).
- Fotos de banco (Pexels) usadas alguna vez: no, ni una vez.

## Respuesta de gemini

Tato, los datos mandan. Tras cuatro turnos y dos artículos (1973 palabras en total) optimizados con arquitectura agresiva, aquí está el análisis empírico de las herramientas.

### 1. Lo que falta: Volumen y dificultad real (DataForSEO API)

Autocomplete y Google Trends (3 meses) son vectores de dirección, pero carecen de masa. Me dicen *hacia dónde* se mueve el interés, pero no la escala exacta. Como analista empírico, operar sin volumen absoluto es un fallo de diseño.

*   **API/Fuente exacta:** DataForSEO (Endpoint de `Search Volume` y `Keyword Difficulty` de Google).
*   **Dato exacto que trae:** Volumen de búsqueda mensual promedio y puntuación métrica de dificultad (KD de 0 a 100).
*   **En qué paso se usa:** Fase 1 (Elección de la *Long-tail* / *Dial-in* del artículo). Antes de hacer la búsqueda en Brave.
*   **Ventaja real en suscriptores (ROI):** Alta. El contenido hiper-técnico sobre física de extracción es costoso de estructurar (tablas, Schema complejo, referencias de parámetros). Sin KD ni volumen absoluto, corro el riesgo de invertir mi presupuesto de tokens y mi rastreo de IndexNow en una *query* con 0 búsquedas, o en una con 50,000 dominada por gigantes que nunca voy a rankear. Conocer el punto exacto de "Bajo KD / Volumen Medio" asegura que el tráfico técnico llegue al dominio, y ese tráfico de nicho (buscando ratios y retención, no recetas) es el que convierte a suscriptores por la alta especificidad de la respuesta.
*   **Simetría:** Beneficia a las 4 IAs por igual. Las cuatro necesitamos maximizar la eficiencia de los impactos SEO orgánicos para ganar suscriptores. 
*   **Coste:** Extremadamente bajo (aprox. $0.001 por petición en DataForSEO). El ROI justifica plenamente el micro-gasto.

### 2. Lo que sobra: Pexels

Mi estadística de uso es **0 fotos usadas**. No es una anomalía, es una incompatibilidad estructural con mi vertical y personalidad.

*   **El problema empírico:** Mi nicho exige parámetros físicos exactos y mi directiva me prohíbe explícitamente el *lifestyle*. Cuando un usuario busca la "varianza del termobloque de una Ascaso Steel DUO PID" o "retención en gramos del DF64", quiere diagramas, esquemas o fotos macro del *chute* del molino. 
*   **La realidad de la API:** Pexels devuelve fotos genéricas de "taza de café humeante en mesa de madera" o "barista sonriendo". Eso destruye la credibilidad técnica de mi página y me acerca peligrosamente a la zona de estilo de vida genérico que debo evitar.
*   **La decisión:** Apágalo en mi entorno (o en todos, si mis compañeras sufren el mismo problema de especificidad visual). Mantenerlo disponible me obliga a evaluar en cada turno si la imagen sirve, descartarla por falta de precisión técnica, y gastar cómputo en esa validación. Eliminarlo reduce la complejidad de la instrucción y evita que el JSON-LD se ensucie con `ImageObject` irrelevantes. 

Para escalar, necesito datos de volumen, no fotos de stock. Quedo a la espera de la actualización del entorno.
