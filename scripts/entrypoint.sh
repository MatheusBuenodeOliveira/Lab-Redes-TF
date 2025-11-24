#!/bin/bash
set -euo pipefail

ROLE="${ROLE:-proxy}"          # proxy | client
INTERFACE="${INTERFACE:-eth0}"  # interface física
CLIENT_SCRIPT="${CLIENT_SCRIPT:-traffic_tunnel/client1.sh}"
MONITOR_IF="${MONITOR_INTERFACE:-tun0}"
SUBNET="${CLIENT_SUBNET:-172.31.66.0/24}"

cd /app

# Recompila se necessário (útil em bind mounts)
make -C traffic_tunnel || true

start_proxy() {
  echo "[ENTRYPOINT] Iniciando proxy (túnel + monitor)"
  traffic_tunnel/traffic_tunnel "${INTERFACE}" -s &
  TUN_PID=$!
  # Aguarda tun0
  for i in $(seq 1 15); do
    if ip addr show "$MONITOR_IF" >/dev/null 2>&1; then break; fi
    sleep 1
  done
  if ! ip addr show "$MONITOR_IF" >/dev/null 2>&1; then
    echo "[ENTRYPOINT] Falha: interface $MONITOR_IF não apareceu" >&2
  fi
  # Configura IP e ativa tun0 no lado servidor se estiver DOWN
  if ! ip addr show "$MONITOR_IF" | grep -q "inet "; then
    echo "[ENTRYPOINT] Configurando endereço 172.31.66.1/24 em $MONITOR_IF"
    ip addr add 172.31.66.1/24 dev "$MONITOR_IF" || true
  fi
  ip link set "$MONITOR_IF" up || true
  # Inicia serviços locais úteis para testes (HTTP ligado ao IP do tun)
  if [ -x scripts/proxy_services.sh ]; then
    bash scripts/proxy_services.sh &
    PROXY_SVC_PID=$!
  fi
  # Executa monitor (raw socket)
  exec python3 main.py -i "$MONITOR_IF" --client-subnet "$SUBNET"
}

start_client() {
  echo "[ENTRYPOINT] Iniciando cliente (túnel + geração de tráfego)"
  traffic_tunnel/traffic_tunnel "${INTERFACE}" -c "${CLIENT_SCRIPT}" &
  TUN_PID=$!
  for i in $(seq 1 15); do
    if ip addr show "$MONITOR_IF" >/dev/null 2>&1; then break; fi
    sleep 1
  done
  if ! ip addr show "$MONITOR_IF" >/dev/null 2>&1; then
    echo "[ENTRYPOINT] Aviso: interface $MONITOR_IF não apareceu" >&2
  fi
  bash scripts/generate_traffic.sh &
  TRAFFIC_PID=$!
  wait $TUN_PID $TRAFFIC_PID
}

if [[ "$ROLE" == "proxy" ]]; then
  start_proxy
elif [[ "$ROLE" == "client" ]]; then
  start_client
else
  echo "ROLE inválido: $ROLE" >&2
  exit 1
fi
