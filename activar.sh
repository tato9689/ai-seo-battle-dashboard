#!/usr/bin/env bash
# activar.sh <dominio.com> — todo lo que cuelga del dominio, en un comando.
#
# Idempotente: se puede volver a lanzar sin romper nada. Hace DNS en
# Cloudflare, Caddy, raíces web, config.json, servicio del dashboard y los
# 6 crons. NO compra el dominio (eso es manual y con tarjeta) ni crea las
# properties de GSC/GA4 (se hacen a mano, ver PASOS_MANUALES.md).
set -euo pipefail

DOM="${1:?Uso: activar.sh <dominio.com>}"
[[ "$DOM" =~ ^[a-z0-9-]+\.[a-z]{2,}$ ]] || { echo "Dominio no válido: $DOM"; exit 1; }
BASE=/root/ai-seo-battle-dashboard
IAS=(claude gpt gemini deepseek)
PUERTO_DASH=8093

# Se cargan todos los .env de Cloudflare y se prueba cada token hasta dar con
# uno que vea la zona: el token viejo solo alcanza a tato9689.com, así que un
# dominio nuevo trae token nuevo y no hay que acordarse de cuál es cuál.
for f in /root/.config/cloudflare/*.env; do
  [ -f "$f" ] && { set -a; . "$f"; set +a; }
done

echo "== 1/7 DNS en Cloudflare =="
IP=$(curl -4 -s https://api.ipify.org)
echo "IP pública: $IP"
ZONE=""
for var in $(compgen -v | grep '^CF_API_TOKEN'); do
  candidato="${!var}"
  [ -n "$candidato" ] || continue
  id=$(curl -s -H "Authorization: Bearer $candidato" \
    "https://api.cloudflare.com/client/v4/zones?name=$DOM" | jq -r '.result[0].id // empty')
  if [ -n "$id" ]; then ZONE="$id"; CF_API_TOKEN="$candidato"; echo "  zona vista con \$$var"; break; fi
done
if [ -z "$ZONE" ]; then
  echo "AVISO: el token de Cloudflare no ve la zona $DOM."
  echo "  → Añade el dominio a Cloudflare y/o genera un token con Zone:DNS:Edit"
  echo "    sobre esa zona, guárdalo en /root/.config/cloudflare/, y repite."
  echo "  Sigo con el resto (Caddy no arrancará HTTPS hasta que el DNS apunte aquí)."
else
  for sub in "@" www "${IAS[@]}" panel; do
    nombre=$([ "$sub" = "@" ] && echo "$DOM" || echo "$sub.$DOM")
    existente=$(curl -s -H "Authorization: Bearer $CF_API_TOKEN" \
      "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records?name=$nombre&type=A" \
      | jq -r '.result[0].id // empty')
    # proxied:false a propósito — Caddy necesita ver el reto de Let's
    # Encrypt y los logs de Nginx/Caddy son una señal del experimento:
    # detrás del proxy naranja todas las IPs serían de Cloudflare.
    cuerpo=$(jq -nc --arg n "$nombre" --arg c "$IP" \
      '{type:"A",name:$n,content:$c,ttl:1,proxied:false}')
    if [ -n "$existente" ]; then
      curl -s -X PATCH -H "Authorization: Bearer $CF_API_TOKEN" \
        -H "Content-Type: application/json" -d "$cuerpo" \
        "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records/$existente" \
        | jq -e '.success' >/dev/null && echo "  actualizado $nombre"
    else
      curl -s -X POST -H "Authorization: Bearer $CF_API_TOKEN" \
        -H "Content-Type: application/json" -d "$cuerpo" \
        "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records" \
        | jq -e '.success' >/dev/null && echo "  creado $nombre"
    fi
  done
fi

echo "== 2/7 raíces web =="
for ia in "${IAS[@]}"; do
  install -d -o root -g caddy -m 2750 "/var/www/$ia.$DOM"
  # La política de privacidad se genera desde la plantilla en cada
  # despliegue: así el responsable, el encargado (Brevo) y la fecha salen
  # de un solo sitio para las 4 y no se desincronizan a mano.
  sed -e "s/\[NOMBRE DEL PROYECTO\/NEWSLETTER\]/$ia.$DOM/g" \
      -e "s/\[FECHA\]/$(date -u +%F)/g" \
      "$BASE/esqueleto-web/privacidad-TEMPLATE.html" > "/root/aisb-$ia/privacidad.html"
  rsync -a --delete --exclude '.git' --exclude 'privacidad-TEMPLATE.html' \
        "/root/aisb-$ia/" "/var/www/$ia.$DOM/"
  chown -R root:caddy "/var/www/$ia.$DOM"
done
echo "$DOM" > "$BASE/.dominio"

echo "== 3/7 Caddy =="
install -d -o caddy -g caddy -m 750 /var/log/caddy
{
  for ia in "${IAS[@]}"; do
    cat <<EOF
$ia.$DOM {
	root * /var/www/$ia.$DOM
	encode zstd gzip
	# Los enlaces internos del esqueleto van a /privacidad sin extensión.
	try_files {path} {path}.html {path}/index.html
	file_server {
		hide .git .gitignore
	}
	# Log propio de cada agente: es una de sus señales (qué bots de
	# buscadores entran, y cuándo) y va en tiempo real, mientras que GSC
	# llega con un día de retraso. La IP se enmascara antes de escribirse,
	# no después: lo que no se guarda no hay que anonimizarlo luego.
	log {
		output file /var/log/caddy/$ia.$DOM.log {
			roll_size 10MiB
			roll_keep 5
		}
		format filter {
			wrap json
			fields {
				request>remote_ip ip_mask {
					ipv4 24
					ipv6 32
				}
			}
		}
	}
}

EOF
  done
  cat <<EOF
# El dashboard va en la raíz, no en un subdominio: la clasificación en vivo
# es la pieza de portfolio del proyecto y esconderla detrás de panel. la
# deja fuera de lo que alguien encuentra al teclear el dominio.
$DOM {
	encode zstd gzip
	reverse_proxy 127.0.0.1:$PUERTO_DASH
}

www.$DOM {
	redir https://$DOM{uri} permanent
}

# Reservado para Listmonk (todavía sin levantar: da 502 hasta entonces).
panel.$DOM {
	encode zstd gzip
	reverse_proxy 127.0.0.1:9000
}
EOF
} > "/etc/caddy/sites/$DOM.caddy"
# `caddy validate` corre como root y CREA los ficheros de log al vuelo,
# root:root 600 — y luego el proceso real, que corre como el usuario caddy,
# no puede abrirlos y la recarga falla con "permission denied". Por eso el
# chown va entre validar y recargar, no antes.
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null || {
  echo "ERROR: la configuración de Caddy no valida, no recargo"; exit 1; }
chown caddy:caddy /var/log/caddy/*.log 2>/dev/null || true
chmod 640 /var/log/caddy/*.log 2>/dev/null || true
systemctl reload caddy && echo "  Caddy recargado"

echo "== 4/7 config.json =="
LANZAMIENTO=$(date -u +%F)
CHECKPOINT=$(date -u -d "+35 days" +%F)   # lanzamiento + 5 semanas
python3 - "$DOM" "$CHECKPOINT" <<'PY'
import json, sys
dom, checkpoint = sys.argv[1], sys.argv[2]
p = "/root/ai-seo-battle-dashboard/config.json"
cfg = json.load(open(p))
cfg["checkpoint_fase2"] = checkpoint
cfg["listmonk_base_url"] = f"https://panel.{dom}/listmonk-api"
for a in cfg["agentes"]:
    ia = a["ia"]
    a["log_url"] = f"https://{ia}.{dom}/log.json"
    # Propiedad de PREFIJO DE URL, no sc-domain: sc-domain agruparía las 4
    # IAs en una sola vista y se pierde la comparación entera.
    a["gsc_site"] = f"https://{ia}.{dom}/"
json.dump(cfg, open(p, "w"), indent=2, ensure_ascii=False)
print(f"  dominio aplicado, checkpoint_fase2={checkpoint}")
PY

echo "== 5/7 servicio del dashboard =="
cat > /etc/systemd/system/aisb-dashboard.service <<EOF
[Unit]
Description=Dashboard publico de AI SEO Battle
After=network.target

[Service]
Type=simple
WorkingDirectory=$BASE/dashboard
ExecStart=$BASE/venv/bin/uvicorn main:app --host 127.0.0.1 --port $PUERTO_DASH
Restart=on-failure
RestartSec=5
User=root
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now aisb-dashboard.service
systemctl is-active --quiet aisb-dashboard && echo "  dashboard activo en :$PUERTO_DASH"

echo "== 6/7 crons =="
# Ventana elegida: 17:00-18:00 UTC (19:00-20:00 Madrid). Fuera de la franja
# cara de DeepSeek (01-04 y 06-10 UTC, L-V) y misma hora para las 4 —
# escalonadas 15 min solo para no escribir a la vez en la misma SQLite;
# distinta hora del día sí sería una asimetría real entre agentes.
TMP=$(mktemp)
crontab -l 2>/dev/null | grep -v "# aisb" > "$TMP" || true
cat >> "$TMP" <<EOF
0 17 * * * $BASE/run_agente.sh claude >> $BASE/logs/cron-claude.log 2>&1 # aisb
15 17 * * * $BASE/run_agente.sh gpt >> $BASE/logs/cron-gpt.log 2>&1 # aisb
30 17 * * * $BASE/run_agente.sh gemini >> $BASE/logs/cron-gemini.log 2>&1 # aisb
45 17 * * * $BASE/run_agente.sh deepseek >> $BASE/logs/cron-deepseek.log 2>&1 # aisb
*/15 * * * * $BASE/venv/bin/python $BASE/poller.py >> $BASE/logs/poller.log 2>&1 # aisb
30 5 * * * $BASE/venv/bin/python $BASE/poller_metrics.py >> $BASE/logs/metrics.log 2>&1 # aisb
EOF
crontab "$TMP" && rm "$TMP"
mkdir -p "$BASE/logs"
echo "  6 crons instalados (crontab -l | grep aisb)"

echo "== 7/7 comprobación =="
for ia in "${IAS[@]}"; do
  printf "  %-9s " "$ia.$DOM"
  curl -s -o /dev/null -w "%{http_code}\n" -m 10 "https://$ia.$DOM/" || echo "sin respuesta todavía (DNS/cert)"
done
printf "  %-9s " "$DOM (panel)"; curl -s -o /dev/null -w "%{http_code}\n" -m 10 "https://$DOM/" || true
echo
echo "Hecho. Falta lo manual: GSC (Prefijo de URL) x4, Listmonk+Brevo,"
echo "y rellenar privacidad.html — ver PASOS_MANUALES.md"
