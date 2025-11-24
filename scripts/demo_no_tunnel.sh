#!/bin/bash
set -euo pipefail

# Demo simples SEM uso do túnel: captura na interface física (eth0)
# e gera tráfego HTTP/DNS/NTP/ICMP para preencher os CSVs.
# Variáveis ajustáveis:
#   MON_IF: interface de captura (padrão eth0)
#   CLIENT_SUBNET: sub-rede considerada "clientes" para estatísticas (padrão 0.0.0.0/0)
#   ROUNDS: número de ciclos de geração de tráfego
#   SLEEP_BETWEEN: intervalo entre ciclos

MON_IF="${MON_IF:-eth0}"
CLIENT_SUBNET="${CLIENT_SUBNET:-0.0.0.0/0}"
ROUNDS="${ROUNDS:-3}"
SLEEP_BETWEEN="${SLEEP_BETWEEN:-3}"
LOG_DIR="logs"
UI_LOG="monitor_ui.txt"

echo "[demo] Interface: $MON_IF | Sub-rede clientes: $CLIENT_SUBNET"

if [[ ! -f main.py ]]; then
  echo "[demo] Erro: executar no diretório raiz do projeto (main.py ausente)." >&2
  exit 1
fi

echo "[demo] Limpando logs antigos..."
rm -f "$LOG_DIR"/*.csv 2>/dev/null || true
mkdir -p "$LOG_DIR"

echo "[demo] Iniciando monitor em segundo plano..."
python3 main.py -i "$MON_IF" --client-subnet "$CLIENT_SUBNET" >"$UI_LOG" 2>&1 &
MON_PID=$!
echo "[demo] Monitor PID=$MON_PID (UI em $UI_LOG)"

sleep 2

gen_cycle() {
  local n="$1"
  echo "[demo] Ciclo $n: gerando tráfego..."
  # HTTP
  (curl -m 5 -s http://example.com >/dev/null) || true
  # DNS
  (command -v dig >/dev/null && dig +time=2 +tries=1 @8.8.8.8 example.com A >/dev/null) || true
  # NTP
  (command -v ntpdate >/dev/null && ntpdate -q pool.ntp.org >/dev/null) || true
  # ICMP
  (ping -c 2 8.8.8.8 >/dev/null) || true
}

for i in $(seq 1 "$ROUNDS"); do
  gen_cycle "$i"
  sleep "$SLEEP_BETWEEN"
done

echo "[demo] Parando monitor..."
kill "$MON_PID" 2>/dev/null || true
wait "$MON_PID" 2>/dev/null || true

echo "[demo] Resumo dos CSVs:"; for f in internet.csv transporte.csv aplicacao.csv; do
  if [[ -f "$LOG_DIR/$f" ]]; then
    echo "--- $f (linhas $(wc -l < "$LOG_DIR/$f"))"; head -n 20 "$LOG_DIR/$f"; echo
  else
    echo "[demo] Arquivo $LOG_DIR/$f inexistente"
  fi
done

echo "[demo] Estatísticas (top 10 final):"
grep -E "Cliente|Prot.:|->" "$UI_LOG" | tail -n 30 || true

echo "[demo] Concluído. UI completa em $UI_LOG"

exit 0