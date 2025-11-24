#!/bin/bash
set -euo pipefail

# Inicia serviços leves no proxy para testes via tun0
# - servidor HTTP em 172.31.66.1:8080

echo "[PROXY_SERVICES] Iniciando servidor HTTP em 172.31.66.1:8080"
# Redireciona logs para /dev/null (não poluirá CSVs)
python3 -m http.server 8080 --bind 172.31.66.1 >/dev/null 2>&1 &
HTTP_PID=$!
echo "[PROXY_SERVICES] HTTP PID=$HTTP_PID"

wait $HTTP_PID
