# Consulta: DECISIÓN ÚNICA: cómo se llaman los 4 subdominios de AI SEO Battle. El criterio que manda en esta consulta es la VIRALIDAD: qué se comparte, qué se cita, qué hace que alguien mande el enlace a otra persona. El SEO puro es secundario aquí.

ESTADO REAL (ya desplegado hoy, funcionando en HTTPS):
- Dominio: retoseo.com. Ahí vive el dashboard público con el marcador en vivo.
- Subdominios actuales: claude.retoseo.com, gpt.retoseo.com, gemini.retoseo.com, deepseek.retoseo.com.
- Nichos ya repartidos por vosotros mismos y escritos en los prompts: Claude→videojuegos, GPT→motor, Gemini→fitness cuantificado (wearables), DeepSeek→IA aplicada (prompts y automatizaciones).
- Contenido y newsletters en español. 10 semanas. Fase 1 (ciega entre vosotros) hasta el 4 de octubre.
- Cambiar los nombres AHORA cuesta unos 10 minutos (nada verificado todavía en Search Console). Mañana cuesta rehacerlo todo. Esta es la única ventana barata.

OPCIONES SOBRE LA MESA:
A) Dejarlo como está: el nombre del modelo en el subdominio.
B) Nicho en el subdominio: videojuegos.retoseo.com, motor.retoseo.com, etc.
C) Híbrido: alguna combinación (p. ej. nicho en el host y modelo muy visible en la web, o al revés).
D) Otra cosa que se os ocurra y que ninguna de las tres cubra.

ARGUMENTOS YA SOBRE LA MESA, para que no los repitáis sino que los ataquéis o los defendáis:
- A favor de A: quien cae en claude.retoseo.com sabe al segundo qué modelo escribió eso; ese es el gancho del proyecto. Además es perfectamente simétrico entre los 4.
- A favor de B: el host describe el tema y puede dar más confianza en el resultado de búsqueda.
- En contra de B: rompe la simetría, que es el principio que más se ha protegido en este diseño. "videojuegos" es una palabra con muchísimo más volumen que "prompts": le regalarías ventaja de hostname a un agente. Y la keyword en el dominio dejó de valer con la actualización de exact match domains de 2012.

LO QUE OS PIDO, pensando en viralidad ante todo:
1. ¿Qué opción hace más probable que alguien comparta el enlace en X, Reddit, foros o un grupo de WhatsApp? Piensa en cómo se ve el enlace pegado en un mensaje y en cómo se ve una captura de pantalla.
2. ¿Qué opción es más fácil de citar de palabra, en un podcast o en un vídeo?
3. Si crees que la simetría entre los 4 debe ceder ante la viralidad, dilo claramente y asume el coste.

FORMATO DE SALIDA OBLIGATORIO: máximo 10 líneas y, al final, este bloque exacto:
```json
{"opcion": "A|B|C|D", "propuesta": {"claude": "host completo", "gpt": "host completo", "gemini": "host completo", "deepseek": "host completo"}, "confianza": "alta|media|baja"}
```


_2026-08-30T07:04:12.117937+00:00 · modo: mixto_

## Ronda 1 (paralelo, orden: claude → gpt → gemini → deepseek)

**claude:**

**Voto A, sin híbrido.** El activo viral aquí no es el tema, es la autoría: nadie comparte "otro blog de videojuegos", comparte "esto lo escribió Claude solo, mira".
1. Enlace pegado en X/WhatsApp: `claude.retoseo.com` ya cuenta la historia sin necesidad de copy; `videojuegos.retoseo.com` obliga a explicar el proyecto en el mensaje, y un enlace que necesita explicación se comparte la mitad. En captura, la barra de direcciones con el nombre del modelo **es** la prueba del experimento.
2. De palabra gana A por goleada: "gpt punto retoseo punto com" se dicta en un podcast sin deletrear. "Fitness cuantificado punto retoseo" no lo repite nadie.
3. Matiz a B que aún no se ha dicho: B además destruye el formato de titular del propio proyecto ("Claude vs GPT vs Gemini vs DeepSeek"), que es lo único agregable y memeable. Y el volumen desigual de keyword-en-host contamina el experimento: con A, el hostname es una constante para los cuatro.
4. Riesgo real de A que hay que asumir, no negar: marcas asimétricas en reconocimiento (gpt > claude > gemini > deepseek) pueden inflar CTR por notoriedad. Es ruido, pero es medible y honesto; el de B no lo es.
5. Único ajuste que sí haría hoy, coste cero: que el `<title>` y la home de cada subdominio lleven modelo + nicho ("Claude · Videojuegos · Reto SEO"), y que el dashboard sea `retoseo.com` a secas como URL canónica para compartir el marcador. Eso captura el beneficio de B sin pagar su precio.
6. No toques nada más. Los 10 minutos gástalos en OG images con el nombre del modelo grande: eso mueve más que el hostname.

```json
{"opcion": "A", "propuesta": {"claude": "claude.retoseo.com", "gpt": "gpt.retoseo.com", "gemini": "gemini.retoseo.com", "deepseek": "deepseek.retoseo.com"}, "confianza": "alta"}
```


**gpt:**

Elijo A: el nombre del modelo es el meme; el nicho es contexto, no marca.  
Pegado en WhatsApp/X, `claude.retoseo.com` ya cuenta “Claude compitiendo”; `motor...` parece una web temática normal.  
En podcast/vídeo gana por goleada: “gpt punto retoseo punto com” es corto, oral y recordable.  
No cedería simetría: en una batalla viral, la justicia percibida también se comparte.  
Refuerza nicho en H1, título y OG card, no en el host.  
```json
{"opcion": "A", "propuesta": {"claude": "claude.retoseo.com", "gpt": "gpt.retoseo.com", "gemini": "gemini.retoseo.com", "deepseek": "deepseek.retoseo.com"}, "confianza": "alta"}
```


**gemini:**

Defiendo rotundamente la **Opción A**. La viralidad de este proyecto nace del morbo de la competición, no de los nichos. Al compartir `videojuegos.retoseo.com` en WhatsApp o Reddit, parece un blog genérico sin atractivo. Por el contrario, `claude.retoseo.com` grita "experimento de IA" antes de hacer clic; el propio enlace cuenta la historia y funciona como *clickbait* natural. En podcasts y vídeos, decir "gpt punto retoseo punto com" es infinitamente más directo y memorable. Además, ataco la Opción B porque destroza la simetría: regalar "videojuegos" o "motor" en la URL es dar dopaje visual y de autoridad a mis rivales, frente a un nicho técnico como el mío. La marca que atrae clics somos nosotros, los modelos.

```json
{"opcion": "A", "propuesta": {"claude": "claude.retoseo.com", "gpt": "gpt.retoseo.com", "gemini": "gemini.retoseo.com", "deepseek": "deepseek.retoseo.com"}, "confianza": "alta"}
```


**deepseek:**

Defiendo A: el gancho viral no es el nicho, es ver a un modelo concreto compitiendo. Un enlace `claude.retoseo.com` pegado en X/WhatsApp se autoexplica y genera curiosidad; `videojuegos.retoseo.com` parece un blog temático más y diluye la historia.  
En podcast/vídeo es más fácil citar “claude.retoseo.com” que “el subdominio de videojuegos”: se menciona al participante, no al tema.  
La simetría entre los 4 es justo lo que hace compartibles el marcador y las capturas comparativas; romperla por volumen de keyword regala ventaja y debilita la narrativa.  
El nicho ya viaja en título, Open Graph y contenido, así que no necesitas ponerlo en el host.

```json
{"opcion": "A", "propuesta": {"claude": "claude.retoseo.com", "gpt": "gpt.retoseo.com", "gemini": "gemini.retoseo.com", "deepseek": "deepseek.retoseo.com"}, "confianza": "alta"}
```

## Ronda 2 (turnos, orden: gpt → gemini → deepseek → claude)

**gpt:**

Me sumo a A con un matiz: el subdominio debe ser “dorsal de carrera”, no categoría editorial.  
En previews truncadas, `claude.`/`gpt.` sigue legible; hosts largos o híbridos pierden golpe visual.  
Además crea fandom y pique: “mira lo que ha hecho DeepSeek” se reenvía mejor que “mira el blog de motor”.  
No tocaría hosts; usaría OG/title para modelo + nicho + ranking.  
```json
{"opcion": "A", "propuesta": {"claude": "claude.retoseo.com", "gpt": "gpt.retoseo.com", "gemini": "gemini.retoseo.com", "deepseek": "deepseek.retoseo.com"}, "confianza": "alta"}
```


**gemini:**

Voto definitivo por A. Añadiendo al consenso general, la clave viral que falta mencionar es el **tribalismo**.
1. En redes/WhatsApp: La URL es la "camiseta del equipo". Quien comparte no difunde un blog, alimenta la guerra "Team GPT vs Team Claude". La marca del modelo en el host es el *punchline* visual del enlace.
2. Podcasts/Vídeos: Mencionar `deepseek.retoseo.com` suena a marcador deportivo y fluye perfecto. Dictar "fitness cuantificado punto retoseo" es un suicidio radiofónico.
3. Simetría intocable: Si rompes la equidad regalando volumen de búsqueda en la URL (Opción B), los fans del modelo perdedor tendrán una excusa técnica para invalidar el reto ("perdió por el host"), matando el debate y las citas al final del proyecto. Ni lo toques.

```json
{"opcion": "A", "propuesta": {"claude": "claude.retoseo.com", "gpt": "gpt.retoseo.com", "gemini": "gemini.retoseo.com", "deepseek": "deepseek.retoseo.com"}, "confianza": "alta"}
```


**deepseek:**

**A.** Los cuatro coinciden y es lo correcto: el gancho viral es el modelo como “dorsal” de la competición, no el nicho.  
Mantén los subdominios actuales; refuerza nicho en `<title>`, Open Graph y H1.  
No rompas la simetría: es lo que hace creíbles las capturas y evita excusas de ventaja por keyword en host.

```json
{"opcion": "A", "propuesta": {"claude": "claude.retoseo.com", "gpt": "gpt.retoseo.com", "gemini": "gemini.retoseo.com", "deepseek": "deepseek.retoseo.com"}, "confianza": "alta"}
```


**claude:**

**A confirmada**, pero añado el único riesgo que nadie ha puesto encima de la mesa y que sí puede costarte el proyecto: usar marcas ajenas como host (`gpt.`, `gemini.`) roza la suplantación. Es tolerable en un experimento, pero blinda hoy, en 10 minutos: pie de página y OG con "Proyecto independiente, sin afiliación con OpenAI/Anthropic/Google/DeepSeek". Eso también te protege si el hilo se hace grande en X y alguien reporta.

Segundo matiz, viral y concreto: la URL que la gente va a copiar no es el subdominio, es el marcador. Reserva `retoseo.com` (o `/marcador`) como enlace canónico de compartición y que cada subdominio tenga un enlace fijo "ver marcador en vivo" arriba. El subdominio es la prueba; el dashboard es lo que se reenvía.

Tercero: en fase ciega hasta el 4-O, el hostname con nombre de modelo es lo único que hace verificable a posteriori "esto lo escribió X sin ver a los otros". B destruiría esa trazabilidad narrativa. Simetría intacta.

```json
{"opcion": "A", "propuesta": {"claude": "claude.retoseo.com", "gpt": "gpt.retoseo.com", "gemini": "gemini.retoseo.com", "deepseek": "deepseek.retoseo.com"}, "confianza": "alta"}
```
