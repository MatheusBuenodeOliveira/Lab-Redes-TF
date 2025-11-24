#!/bin/bash
set -euo pipefail

# Loop simples gerando tráfego HTTP, DNS e NTP
# Executa indefinidamente para alimentar o monitor.

DNS_SERVER="8.8.8.8"
HTTP_HOST="http://example.com"
NTP_POOL="pool.ntp.org"

while true; do
  curl -m 5 -o /dev/null -s "$HTTP_HOST" || true
  dig +time=2 +tries=1 @"$DNS_SERVER" example.com A || true
  ntpdate -q "$NTP_POOL" || true
  sleep 5
done
