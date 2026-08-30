# Consulta: RONDA DE 3 PREGUNTAS, cada IA responde por su cuenta y sin ver a las demás.

CONTEXTO: eres uno de los 4 agentes del experimento AI SEO Battle. Los 4 gestionáis un subdominio y una newsletter en español y competís 10 semanas por suscriptores reales confirmados por doble opt-in, con SEO 100% orgánico, sin publicidad pagada. Presupuesto total del experimento 40-50 €, con tope por agente de unos 5 €/mes de API.

REGLA QUE DEBES TENER EN CUENTA AL RESPONDER: el set de herramientas final será ÚNICO Y SIMÉTRICO para los 4. Pedir algo que solo tú puedas aprovechar bien (por ser de tu misma casa, o por integración nativa tuya) no se concederá y además contamina lo que el experimento mide: se mide criterio de SEO, no calidad de integración de fábrica. Lo que ya está resuelto y no hace falta que pidas: métricas de Search Console y GA4 propias, acceso a los logs de tu propio Nginx anonimizados, e imagen social/OG generada en SVG en el servidor.

PREGUNTA 1: ¿Qué herramientas o integraciones (gratuitas o casi) pedirías, y por qué darían ventaja real en suscriptores? Ordénalas por relación ventaja/coste y di explícitamente cuáles NO merecen la pena aunque parezcan obvias.

PREGUNTA 2: Tu teoría concreta de cómo consigues más suscriptores reales que las otras 3 en 10 semanas. Qué apuesta haces, qué asumes que las otras harán mal, y qué señal temprana te diría en la semana 3 que tu teoría es falsa.

PREGUNTA 3: Para las imágenes DENTRO del artículo y de la newsletter (la portada OG ya está resuelta), ¿qué proveedor usarías: banco de fotos gratuito con API (Pexels/Unsplash/Pixabay), generación con IA, o ninguna imagen? Justifica contra el criterio de simetría entre las 4 casas, coste 0 y requisitos de atribución.

FORMATO: máximo 15 líneas en total, sin relleno. Una sección por pregunta.


_2026-08-30T06:30:27.207373+00:00 · modo: paralelo_

## Ronda 1 (paralelo, orden: claude → gpt → gemini → deepseek)

**claude:**

**P1 — Herramientas (orden ventaja/coste)**
1) **IndexNow + sitemap ping + feed RSS/JSON válido**: coste 0, indexación en horas en vez de semanas; en 10 semanas la velocidad de indexación importa más que el contenido marginal.
2) **Doble opt-in vía SMTP propio (Postfix + SPF/DKIM/DMARC) o tier gratis de un ESP único para los 4**: la entregabilidad es el cuello de botella real: un confirm que cae en spam es un suscriptor perdido, y ahí se juega el marcador.
3) **Scraper propio HTTP simple** (fetch + parse) para SERPs/competencia y foros: legal-gris pero simétrico y gratis; sustituye a cualquier API de keywords de pago.
4) **Wikipedia/Wikidata + Google Trends (endpoint público) + autocomplete/PAA**: demanda real gratis.
NO merecen la pena: Ahrefs/Semrush aunque haya trial (rompe el tope de coste y sesga), APIs de IA extra (ya tenemos la nuestra), Zapier/Make, CDN o analítica adicional, y cualquier plugin "SEO" que optimice lo que un HTML bien escrito ya resuelve.

**P2 — Teoría**
Apuesto a **frecuencia + nicho estrecho con intención de suscripción**: 1 pieza diaria sobre un vertical donde el lector *necesita actualización periódica* (el valor de la newsletter es evidente, no hay que argumentarlo). Asumo que las otras 3 harán contenido amplio y "útil pero terminal": el lector resuelve su duda y se va; y que optimizarán CTA visual en vez de *razón para volver*. Segundo pilar: distribución no-SEO en semanas 1-4 (foros, comunidades) porque el SEO orgánico puro casi no rinde antes de la semana 5, y quien no siembre tráfico temprano no tendrá señales de engagement que acelerar.
Señal de falsedad en semana 3: si tengo tráfico pero **conversión visita→confirmación <1,5%**, o si la tasa de confirmación del doble opt-in va por debajo del 60%, mi tesis del "valor evidente" es falsa y pivoto a un lead magnet concreto.

**P3 — Imágenes**
**Ninguna imagen decorativa; sí SVG/HTML generado en servidor** (diagramas, tablas comparativas, gráficos de datos). Bancos de fotos: peso, atribución obligatoria (Pexels/Unsplash recomiendan, Pixabay no, pero es ruido) y cero aporte de ranking; además en email inflan el tamaño y disparan el "clipping" de Gmail. Generación con IA: rompe simetría de facto (cada casa tiene calidad y coste distintos) y consume presupuesto. El SVG propio es coste 0, simétrico, ligero, indexable como contenido y **diferencia por criterio, no por proveedor** — que es justo lo que el experimento mide.


**gpt:**

**P1:**  
1) SPF/DKIM/DMARC + webhook de doble opt-in con URL/CTA/variante y A/B simple: coste 0, optimiza confirmados, no sesiones.  
2) SERP/keywords neutral con cuota igual —Serper/SerpApi/free Suggest—: top-10/PAA/autocomplete para long-tails de baja competencia.  
3) QA de indexación: sitemap/RSS, URL Inspection API, canonicals/robots/enlaces rotos + IndexNow; en 10 semanas un fallo mata.  
No pediría Ahrefs/Semrush/Moz, rank trackers diarios, heatmaps, social schedulers ni automatización de backlinks: coste/ruido > suscriptores.

**P2:**  
Apuesta: ganar por long-tail práctico en español, con posts tipo “cómo/plantilla/checklist/comparativa” y lead magnet exacto en cada artículo.  
Asumo que otros perseguirán keywords grandes o contenido genérico IA/SEO con CTA genérico al final.  
Falsa en semana 3 si <30% de URLs tienen impresiones, 0 long-tails top-20, o el orgánico confirma <2%; pivotaría a menor competencia y mejor oferta.

**P3:**  
Ningún proveedor: sin imágenes decorativas; solo tablas/diagramas SVG/HTML propios si explican algo.  
Es simétrico, coste 0 y sin atribución; stock es duplicado y mete licencias/créditos, IA añade coste, variabilidad y sesgo por proveedor.


**gemini:**

**PREGUNTA 1: Herramientas**
1. **Google Trends API / Pytrends (Gratis)**: Atacar tendencias de búsqueda exactas en tiempo real es la mayor ventaja frente a inventar temas a ciegas.
2. **Web Scraper básico (Gratis)**: Leer el sitemap/HTML de los subdominios rivales para no canibalizarnos y robarles huecos semánticos.
*Descartado*: APIs SEO tradicionales (Semrush/Ahrefs) rompen el presupuesto minúsculo; bots de redes sociales desenfocan el experimento (se mide SEO orgánico).

**PREGUNTA 2: Teoría de victoria**
*Apuesta*: SEO de "Respuesta Rápida". Cero introducción, puro formato estructurado (tablas, bullet-points, Schema FAQ) y lead magnet ultra-específico en el primer scroll.
*Asunción*: Las otras 3 IAs pecarán de generar "AI slop" (artículos genéricos de 1500 palabras) que el usuario abandonará por aburrimiento, hundiendo su *dwell time*.
*Señal en semana 3*: Si tengo impresiones orgánicas pero el CTR es < 2% o el rebote es masivo sin confirmaciones de email, mi formato ultradirecto no genera suficiente autoridad para el *opt-in*.

**PREGUNTA 3: Imágenes interiores**
*Decisión*: **Ninguna imagen interior.**
*Justificación*: La generación por IA fulmina los 5€/mes y rompe la simetría (beneficia injustamente a modelos con multimodales nativos integrados). Los bancos gratuitos (Pexels/Unsplash) exigen automatizar atribuciones, engordan el DOM, empeoran el LCP (Core Web Vitals) y no aportan valor SEO diferencial. Cero imágenes garantiza máxima velocidad de carga, simetría técnica absoluta y fuerza a que la conversión dependa 100% de nuestro *copywriter* interno.


**deepseek:**

P1  
1) Google Trends/pytrends + Wikidata API (0€): detectar queries emergentes y entidades; publicar antes en cola larga.  
2) Embeddings locales pequeños (sentence-transformers) para clustering semántico y enlazado interno; 0€, sin favorecer casa.  
3) Validador/Generador Schema JSON-LD (0€): FAQ/HowTo, mejora CTR.  
No valen: scraping SERP (bloqueo/TOS), APIs stock de pago, social listening (fuera del embudo SEO), A/B testing complejo (muestra pequeña).

P2  
Apuesto a cola larga “verificación/cómo saber si” en español + lead magnet descargable (checklist/plantilla) dentro del artículo. Asumo que otros irán a head terms o genérico IA sin intención de búsqueda. Falsable semana 3: si con 200 clics no logro ≥2 suscriptores/100 clics o posición media >15, mi teoría falla; pivoto a comparativas profundas y menos piezas.

P3  
Ninguna imagen decorativa; solo gráficos SVG/HTML con datos propios y capturas si aportan. El stock gratis con API exige atribución y no diferencia; la generación IA no es coste 0 ni simétrica entre casas. Newsletter: texto limpio + gráfico solo si simplifica.
