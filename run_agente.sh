#!/usr/bin/env bash
# Envoltorio de cron para un agente: carga las claves, ejecuta su turno y
# publica el repo en su raíz web. La publicación va aquí y no dentro de
# cron_agente.py a propósito: el Python ya está probado y lo que hace es
# escribir+commitear en el repo; servirlo es cosa del despliegue.
set -euo pipefail
IA="${1:?Uso: run_agente.sh <claude|gpt|gemini|deepseek> [--newsletter]}"
shift || true

TIPO="turno diario"
[[ "$*" == *"--newsletter"* ]] && TIPO="newsletter semanal"

# Aviso de control por Telegram (pedido por Tato para vigilar los 8 turnos
# reales de las 4 IAs): lanzamiento al principio, éxito o fallo al final, vía
# trap EXIT para que cubra cualquier salida del script (incluida la del
# guardarraíl de DESTINO más abajo). No bloqueante: un fallo de Telegram no
# debe tumbar el turno, por eso avisar() nunca propaga su propio error.
avisar() {
  /root/ai-seo-battle-dashboard/venv/bin/python - "$1" <<'PY' || true
import sys
sys.path.insert(0, "/root/ai-seo-battle-dashboard")
from avisos import enviar
try:
    enviar(sys.argv[1])
except Exception as e:
    print(f"[avisar] fallo enviando a Telegram: {e}", file=sys.stderr)
PY
}

on_exit() {
  local rc=$?
  if [ "$rc" -eq 0 ]; then
    local dom
    dom=$(cat /root/ai-seo-battle-dashboard/.dominio 2>/dev/null || echo '?')
    avisar "✅ AI SEO Battle: ${TIPO} de ${IA} completado y publicado en https://${IA}.${dom}"
  else
    avisar "🔴 AI SEO Battle: ${TIPO} de ${IA} FALLÓ (código ${rc}) — revisa logs/cron-${IA}.log"
  fi
}
trap on_exit EXIT

avisar "🚀 AI SEO Battle: arranca ${TIPO} de ${IA}"

# Candado: los turnos van escalonados cada 15 min, pero un modelo lento puede
# pasarse y solaparse con el siguiente. Los cuatro escriben en la misma SQLite
# y en el mismo log, así que se serializan. flock espera, no descarta: perder
# un turno por llegar tarde sería peor que empezarlo cinco minutos después.
exec 9>/var/lock/aisb-turno.lock
flock 9

set -a; . /root/.config/ai-seo-battle/.env; set +a
cd /root/ai-seo-battle-dashboard
venv/bin/python cron_agente.py "$IA" "$@"

DOM=$(cat /root/ai-seo-battle-dashboard/.dominio)
DESTINO="/var/www/${IA}.${DOM}"
# Guardarraíl: --delete sobre una ruta equivocada borraría un sitio ajeno.
[ -d "$DESTINO" ] || { echo "ERROR: no existe $DESTINO, no publico"; exit 1; }
rsync -a --delete --exclude '.git' --exclude 'privacidad-TEMPLATE.html' \
      "/root/aisb-${IA}/" "$DESTINO/"
# La etiqueta de Search Console se repone en cada publicación: el agente
# reescribe su index.html entera cada turno y se la llevaría por delante.
sed -e "s/\[NOMBRE DEL PROYECTO\/NEWSLETTER\]/${IA}.${DOM}/g" \
    -e "s/\[FECHA\]/$(date -u +%F)/g" \
    /root/ai-seo-battle-dashboard/esqueleto-web/privacidad-TEMPLATE.html \
    > "$DESTINO/privacidad.html"
# Red de seguridad para el marcador [SUBDOMINIO]. La piel semilla lo traía
# dentro del canonical, del og:url, del JSON-LD y de la línea Sitemap del
# robots.txt, y así estuvo publicado en los 4 sitios el día 0: un canonical
# que apunta a un host inventado le dice a Google que la URL buena es otra, y
# eso no se ve hasta semanas después en Search Console. El guardarraíl de
# marcadores solo mira lo que escribe el agente, y el robots.txt no lo
# escribe él, así que la última palabra tiene que estar aquí. Sustituye el
# marcador, no reescribe el fichero: lo que el agente añadiera se conserva.
# El `|| true` final es necesario: no encontrar el marcador es el caso
# normal a partir del día 1 (ya se sustituyó una vez), y sin él `grep -rl`
# sin coincidencias devuelve 1, que con `pipefail` tumbaba el script entero
# aunque el turno se hubiera publicado bien (así fallaron los turnos de hoy).
grep -rl '\[SUBDOMINIO\]' "$DESTINO" 2>/dev/null | while read -r f; do
  sed -i "s/\[SUBDOMINIO\]/${IA}.${DOM}/g" "$f"
done || true

"$PWD/venv/bin/python" /root/ai-seo-battle-dashboard/verificacion.py "$IA" "$DESTINO"
chown -R root:caddy "$DESTINO"

# Aviso a los buscadores que consumen IndexNow (Bing, Yandex, Seznam, Naver).
# Después del chown: el fichero de verificación tiene que estar servido antes
# de que ellos vengan a comprobarlo.
"$PWD/venv/bin/python" /root/ai-seo-battle-dashboard/indexnow.py "$IA" "$DESTINO" || true
chown -R root:caddy "$DESTINO"

# El poller corre cada 15 min en los mismos minutos que los 4 turnos
# (:00/:15/:30/:45), así que casi siempre pasa segundos ANTES de que el
# turno termine de commitear y el evento se queda sin aparecer en el panel
# hasta el ciclo siguiente (pasó de verdad con gemini y deepseek el
# 2026-08-30). Se lanza aquí, justo al terminar, para que el marcador quede
# al día sin depender de ese cruce de minutos. `|| true`: si falla, ya lo
# recogerá el cron de */15 min normal, no debe tumbar el turno.
"$PWD/venv/bin/python" /root/ai-seo-battle-dashboard/poller.py || true
