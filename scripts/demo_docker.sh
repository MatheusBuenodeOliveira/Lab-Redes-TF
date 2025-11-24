#!/bin/bash
set -euo pipefail

# Demonstração automatizada usando Docker.
# Cria um container, instala ferramentas de geração de tráfego,
# roda o monitor em eth0 e exibe amostras dos CSVs.

# Configuráveis via env:
#   IMAGE (default python:3.12-slim)
#   CONTAINER_NAME (default monitor-demo)
#   ROUNDS (ciclos de geração de tráfego) default 3
#   SLEEP_BETWEEN (intervalo entre ciclos) default 3
#   CLIENT_SUBNET (sub-rede para stats) default 0.0.0.0/0
#   MON_IF (interface dentro do container) default eth0

IMAGE="${IMAGE:-python:3.12-slim}"
CONTAINER_NAME="${CONTAINER_NAME:-monitor-demo}"
ROUNDS="${ROUNDS:-3}"
SLEEP_BETWEEN="${SLEEP_BETWEEN:-3}"
CLIENT_SUBNET="${CLIENT_SUBNET:-0.0.0.0/0}"
MON_IF="${MON_IF:-eth0}"

echo "[docker-demo] Image=$IMAGE Container=$CONTAINER_NAME IF=$MON_IF ROUNDS=$ROUNDS"

if ! command -v docker >/dev/null 2>&1; then
  echo "[docker-demo] Erro: docker não encontrado no PATH." >&2
  exit 1
fi

echo "[docker-demo] Removendo container anterior (se existir)..."
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

echo "[docker-demo] Subindo container..."
docker run -d \
  --name "$CONTAINER_NAME" \
  --cap-add NET_RAW --cap-add NET_ADMIN \
  -v "$(pwd)":/app -w /app \
  "$IMAGE" sleep infinity

echo "[docker-demo] Instalando ferramentas de rede dentro do container..."
docker exec "$CONTAINER_NAME" bash -lc 'apt-get update && apt-get install -y --no-install-recommends curl dnsutils ntpsec-ntpdate iputils-ping'

echo "[docker-demo] Limpando logs antigos..."
docker exec "$CONTAINER_NAME" bash -lc 'rm -f logs/*.csv 2>/dev/null || true; mkdir -p logs'

echo "[docker-demo] Iniciando monitor..."
docker exec -d "$CONTAINER_NAME" bash -lc "python3 main.py -i $MON_IF --client-subnet $CLIENT_SUBNET > monitor_ui.txt 2>&1"

sleep 2

gen_cycle() {
  local n="$1"
  echo "[docker-demo] Ciclo $n: tráfego HTTP/DNS/NTP/ICMP"
  docker exec "$CONTAINER_NAME" bash -lc 'curl -m 5 -s http://example.com >/dev/null || true'
  docker exec "$CONTAINER_NAME" bash -lc 'dig +time=2 +tries=1 @8.8.8.8 example.com A >/dev/null || true'
  docker exec "$CONTAINER_NAME" bash -lc 'ntpsec-ntpdate -q pool.ntp.org >/dev/null || true'
  docker exec "$CONTAINER_NAME" bash -lc 'ping -c 2 8.8.8.8 >/dev/null || true'
}

for i in $(seq 1 "$ROUNDS"); do
  gen_cycle "$i"
  sleep "$SLEEP_BETWEEN"
done

echo "[docker-demo] Coletando amostras de logs..."
docker exec "$CONTAINER_NAME" bash -lc 'for f in logs/internet.csv logs/transporte.csv logs/aplicacao.csv; do echo "--- $(basename $f)"; head -n 20 $f || true; done'

echo "[docker-demo] Estatísticas da UI (últimas linhas relevantes):"
docker exec "$CONTAINER_NAME" bash -lc 'grep -E "Cliente|Prot.:|->" monitor_ui.txt | tail -n 40 || true'

echo "[docker-demo] Encerrando monitor..."
docker exec "$CONTAINER_NAME" bash -lc 'pkill -f "main.py -i" || true'
sleep 1

echo "[docker-demo] Pronto. Para inspecionar mais:" \
     "docker exec $CONTAINER_NAME tail -n 50 logs/internet.csv" \
     "| transporte.csv | aplicacao.csv"

echo "[docker-demo] Para remover: docker rm -f $CONTAINER_NAME"

exit 0