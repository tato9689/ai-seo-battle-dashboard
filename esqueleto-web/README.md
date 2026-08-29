# Esqueleto web — punto de partida para las 4 IAs

Esto NO parte de cero: es la "casa ya construida" que cada una de las 4 IAs
viste una sola vez el día 0 con su propia piel visual (colores, tipografía,
CSS/Tailwind/lo que sea). Se copia entero a cada uno de los 4 repos cuando
se creen.

Qué trae:
- `index.html` — landing con hero, formulario de suscripción (doble opt-in
  vía Listmonk) y lista de artículos. Placeholders entre `[CORCHETES]` para
  lo que cada IA debe rellenar.
- `log.html` — el "diario de guerra" público. Lee el mismo `/log.json` que
  ya consume el poller del dashboard central (ver `../CONTRATO_LOG.md`), así
  que el log narrativo y el log estructurado son la misma fuente, no dos
  cosas que mantener por separado.
- `reset.css` — normaliza box-sizing/márgenes/tipografía base, no opina de
  diseño. Sin framework CSS (se descartó Bootstrap u otros a propósito: no
  son neutros, cada IA tendría que pelearse contra su estilo por defecto).

Qué NO debe tocar cada IA al vestir su piel: la estructura semántica
(header/nav/main/section/footer), el `action`/`method` del formulario de
suscripción, ni el fetch a `/log.json` en `log.html` — eso es la parte
técnica (accesibilidad, Core Web Vitals, contrato de datos) que controla
Tato desde la base común.

Pendiente antes de publicar cualquiera de los 4 sitios de verdad: sustituir
el texto de consentimiento GDPR (marcado `[PENDIENTE]` en `index.html`) por
la plantilla legal real — uno de los 3 riesgos ya anotados como bloqueante
antes del primer email real.
