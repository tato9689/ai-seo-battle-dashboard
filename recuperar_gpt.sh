#!/usr/bin/env bash
# Recupera los turnos de gpt perdidos por crédito de OpenAI agotado
# (pedido por Tato el 2026-09-24). Lo llama el cron cada 10 min.
# - Sin crédito: apunta en .pendientes_gpt cada turno que se va perdiendo
#   (contenido a diario tras las 17:30, diseño mar/jue tras las 10:50).
# - Con crédito: turno doble — lanza UN pendiente al día, además del turno
#   normal (2026-09-27, Tato: «que gpt tenga turnos dobles hasta recuperar»).
#   run_agente.sh ya avisa por Telegram y serializa con flock.
# Cuando la lista se vacía, se quita a sí mismo del cron.
set -uo pipefail
cd /root/ai-seo-battle-dashboard
exec 8>/var/lock/aisb-recuperar.lock
flock -n 8 || exit 0
LISTA=.pendientes_gpt
ULTIMA=.ultima_recuperacion_gpt
HOY=$(date +%F)
set -a; . /root/.config/ai-seo-battle/.env; set +a

avisar() {
  venv/bin/python - "$1" <<'PY' || true
import sys
sys.path.insert(0, "/root/ai-seo-battle-dashboard")
from avisos import enviar
try: enviar(sys.argv[1])
except Exception as e: print(f"[avisar] {e}", file=sys.stderr)
PY
}

# Si `crontab -l` fallara, el pipe instalaría un crontab VACÍO y se llevaría
# por delante todos los cron de root (batalla, blog, trading, copias...).
# Se lee primero, se comprueba y se instala desde un temporal con copia.
quitar_cron() {
  local actual tmp
  actual=$(crontab -l) || { avisar "🔴 AI SEO Battle: no pude leer el crontab para quitar recuperar_gpt.sh; quítalo a mano"; return 1; }
  grep -q 'recuperar_gpt.sh' <<<"$actual" || return 0
  printf '%s\n' "$actual" > "logs/crontab-antes-de-quitar-recuperar.bak"
  tmp=$(mktemp)
  grep -v 'recuperar_gpt.sh' <<<"$actual" > "$tmp"
  # Nunca instalar algo vacío: el crontab de root tiene mucho más que esto.
  [ -s "$tmp" ] && crontab "$tmp"
  rm -f "$tmp"
}

apuntar() {  # apuntar <diario|diseno>: añade el turno de hoy si no está ya
  grep -qx "$1 $HOY" "$LISTA" 2>/dev/null && return
  echo "$1 $HOY" >> "$LISTA"
  echo "$(date -Is) apuntado como perdido: $1 $HOY"
}

[ -s "$LISTA" ] || { quitar_cron; exit 0; }

# Hoy ya hubo turno doble: no gastar ni el sondeo.
[ "$(cat "$ULTIMA" 2>/dev/null)" = "$HOY" ] && exit 0

# Sondeo casi gratis: 16 tokens (con 1 el modelo da 400 aunque haya crédito) con el modelo barato de gpt.
codigo=$(curl -s -m 30 -o /tmp/aisb-sondeo.json -w '%{http_code}' https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H 'Content-Type: application/json' \
  -d '{"model":"gpt-5.4-mini-2026-03-17","messages":[{"role":"user","content":"ok"}],"max_completion_tokens":16}')
if [ "$codigo" != "200" ]; then
  echo "$(date -Is) sondeo gpt: HTTP $codigo, sin crédito o API caída, espero"
  # Solo se apunta si es falta de crédito de verdad, no una caída de la API.
  if grep -q 'credit_balance_exhausted\|insufficient_quota' /tmp/aisb-sondeo.json; then
    ahora=$(date +%H%M); dia=$(date +%u)
    [ "$ahora" -ge 1730 ] && apuntar diario
    [ "$ahora" -ge 1050 ] && { [ "$dia" = 2 ] || [ "$dia" = 4 ]; } && apuntar diseno
  fi
  exit 0
fi

quedan=$(wc -l < "$LISTA")
tipo=$(head -n1 "$LISTA" | cut -d' ' -f1)
flag=""; [ "$tipo" = "diseno" ] && flag="--diseno"
avisar "🔁 AI SEO Battle: turno doble de gpt, recupero '$(head -n1 "$LISTA")' (quedan $quedan pendientes)"
echo "$(date -Is) lanzando pendiente: $(head -n1 "$LISTA")"
# Un solo intento al día, salga como salga. Antes, si el turno ya se había
# pagado y fallaba un paso del despliegue, el pendiente seguía en la lista y
# a los 10 min se lanzaba otro turno de pago, sin tope.
echo "$HOY" > "$ULTIMA"
/root/ai-seo-battle-dashboard/run_agente.sh gpt $flag >> logs/cron-gpt.log 2>&1
rc=$?
# Solo cuenta como recuperado si se publicó de verdad: un turno bloqueado
# por guardarraíles también sale con 0 (lo marca run_agente.sh vía cron_agente.py).
if [ "$(head -n1 .resultado-gpt 2>/dev/null)" = "publicado" ]; then
  sed -i '1d' "$LISTA"
  echo "$(date -Is) recuperado (código $rc)"
else
  avisar "⚠️ AI SEO Battle: el pendiente '$(head -n1 "$LISTA")' de gpt no se publicó en la recuperación (código $rc); lo reintento mañana"
  exit 1
fi
if [ ! -s "$LISTA" ]; then
  avisar "✅ AI SEO Battle: recuperados todos los turnos pendientes de gpt"
  quitar_cron
fi
