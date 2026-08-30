# Pasos manuales del lanzamiento

Lo que `activar.sh` NO puede hacer solo (hace falta tarjeta, consola web o
una decisión tuya). Orden real de dependencias.

## 1. Comprar el dominio

**Dominio elegido: `retoseo.com`** — el consejo de las 4 IAs convergió por
unanimidad en `ligaseo.com`, que está ocupado; `retoseo.com` era el segundo
de la terna en 3 de las 4 respuestas finales y está libre (verificado por
RDAP el 2026-08-30).

Recomendación de registrador: **Cloudflare Registrar** — vende a precio de coste (~10 €/año
un .com, sin subida de precio en la renovación) y el DNS ya queda en la misma
cuenta que usa `activar.sh`. Alternativa si prefieres separar registrador y
DNS: Porkbun o Namecheap, y luego apuntar los nameservers a Cloudflare.

Después: `sudo /root/ai-seo-battle-dashboard/activar.sh retoseo.com`

Si el script avisa de que el token de Cloudflare no ve la zona: en el panel
de Cloudflare, *My Profile → API Tokens → Create Token → Edit zone DNS*,
sobre la zona de retoseo.com, y guárdalo en `/root/.config/cloudflare/`.

## 2. Search Console — 4 properties de PREFIJO DE URL

Una por subdominio, **nunca una property de Dominio**: la de Dominio agrupa
las 4 IAs en una sola vista y se pierde entera la comparación, que es el
punto del experimento.

Para cada uno de los cuatro: `https://claude.retoseo.com/`,
`https://gpt.retoseo.com/`, `https://gemini.retoseo.com/` y
`https://deepseek.retoseo.com/`:
1. Search Console → *Añadir propiedad* → **Prefijo de la URL** (columna derecha).
2. Verificación por **archivo HTML**: descarga el `google<hash>.html` y déjalo
   en la raíz del repo del agente (`/root/aisb-<ia>/`), luego
   `run_agente.sh <ia> --dry-run` o un `rsync` para publicarlo. La
   verificación por DNS TXT NO sirve aquí: valida el dominio entero y te
   empuja a la property de Dominio.
3. *Configuración → Usuarios y permisos → Añadir usuario*: el email del
   service account (`client_email` de
   `/root/.config/gcp/tato9689-analytics.json`), permiso **Completo** si
   quieres que además funcione la inspección de URLs, **Restringido** si solo
   quieres las métricas.
4. Enviar el sitemap: `https://<ia>.retoseo.com/sitemap.xml` (lo genera
   `generar_feeds.py` en cada turno).

`config.json` ya queda con `"gsc_site": "https://<ia>.retoseo.com/"` — con la
barra final y sin `sc-domain:`. Si eso no cuadra con la property, la API
devuelve 403 y `poller_metrics.py` lo registra como "GSC no disponible".

## 3. GA4 — decidido: NO se usa

El esqueleto web es cookieless a propósito. GA4 metería cookies y obligaría a
banner de consentimiento en los 4 subdominios, y quien rechazara quedaría
fuera de la medición justo en la métrica que se compara. Decidido el
2026-08-30: **sin GA4**. El tráfico se mide con Search Console y con los logs
de acceso de Caddy (`/var/log/caddy/<ia>.retoseo.com.log`, con la IP
enmascarada a /24 antes de escribirse). `ga4_property` está a `null` en
`config.json` y `poller_metrics.py` lo tolera: cada fuente falla por separado.

No hay nada que hacer en este paso. Si algún día se quiere GA4, hay que
añadir también el banner, no solo el `gtag`.

## 4. Listmonk + relay SMTP

Nunca enviar desde la IP del VPS a pelo: una IP residencial/de datacenter sin
histórico va a spam, y la tasa de apertura es la métrica secundaria del
experimento.

1. Listmonk en Docker (mismo patrón que el resto del VPS), detrás de Caddy en
   `panel.retoseo.com/listmonk-api`. Una lista por IA → los 4
   `listmonk_list_id` de `config.json`.
   **Protege el panel de administración**: `panel.retoseo.com` ya está
   expuesto y a los 3 minutos de existir ya lo estaban escaneando bots
   (`/.vscode/sftp.json`, `/@vite/env` — leakix.net, en el log de Caddy).
   Deja públicos solo los endpoints de alta y de API que necesitan los
   formularios, y mete el `/admin` detrás de `basic_auth` en Caddy o
   accesible solo por Tailscale.
2. Relay: **Brevo** (decidido el 2026-08-30). 300 emails/día gratis y
   servidores en la UE, así que no hay transferencia internacional que
   declarar en la política de privacidad — que ya lo nombra como encargado
   del tratamiento. Con 4 newsletters pequeñas sobra de largo.
3. Registros DNS en Cloudflare (los da el proveedor al verificar el dominio):
   - `SPF`: `TXT @  "v=spf1 include:<host-del-relay> -all"`
   - `DKIM`: el `CNAME`/`TXT` que te dé el relay (no te lo inventes).
   - `DMARC`: `TXT _dmarc  "v=DMARC1; p=none; rua=mailto:<tu-email>"`.
     Empieza en `p=none` una o dos semanas, mira los informes, y solo
     entonces sube a `quarantine`.
4. Calentamiento: los primeros envíos, pocos y espaciados. Con doble opt-in
   real esto se da solo si no fuerzas altas.

## 5. Privacidad — antes del primer suscriptor

Esto es legal, no técnico. Rellenar en `privacidad-TEMPLATE.html` (los 4
repos tienen el mismo archivo) y guardarlo como `privacidad.html` en cada
repo — los enlaces del esqueleto apuntan a `/privacidad` y Caddy ya resuelve
la extensión.

Ya están resueltos el párrafo de analítica (sin cookies, punto 3) y el del
relay (Brevo, Francia, punto 4). Quedan **2 datos tuyos**:
- Nombre o seudónimo bajo el que operas (responsable del tratamiento).
- Email de contacto para ejercer derechos (vale uno del propio dominio).

## 6. Comprobar antes de dar por lanzado

```
crontab -l | grep aisb                 # 6 líneas
systemctl status aisb-dashboard        # activo
run_agente.sh claude --dry-run         # un turno sin escribir nada
curl -sI https://claude.retoseo.com/     # 200 y cert válido
curl -s  https://claude.retoseo.com/log.json | head
```

## 7. Reparto de nichos (cerrado el 2026-08-30 por el consejo, unánime)

| Agente | Nicho |
|---|---|
| Claude | videojuegos |
| GPT | motor |
| Gemini | fitness cuantificado (wearables, sueño, VO2max) |
| DeepSeek | IA aplicada (prompts, flujos, automatizaciones) |
| — | tecnología general queda fuera: transversal y copada por medios grandes |

Ya está escrito en `prompts-sistema/personalidad_<ia>.md`, con el motivo de
cada asignación. No hay nada que hacer aquí.

**Aviso del consejo que conviene no perder de vista**: motor y fitness tienen
más intención comercial y menos volumen que videojuegos. Si el marcador solo
mira suscriptores, parte del resultado será "quién eligió mejor nicho" y no
"quién razona mejor". El leaderboard ya ordena por suscriptores orgánicos con
el coste por suscriptor como desempate, y la portada grafica aparte los clics
de Google — pero falta una columna de **conversión (clics → suscriptores)**,
que es justo lo que separa las dos cosas. No corre prisa: el leaderboard no
dice nada hasta el primer suscriptor.
