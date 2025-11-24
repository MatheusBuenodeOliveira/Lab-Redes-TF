# Monitor de Tráfego de Rede – Trabalho Final

Este projeto implementa, em Python (raw sockets), um monitor de tráfego em tempo real para a interface `tun0`, conforme o enunciado do Trabalho Final de Laboratório de Redes.

## Funcionalidades Principais
- Captura pacotes via raw socket na interface indicada (padrão: `tun0`).
- Parsing de camadas: IPv4/IPv6/ICMP, TCP/UDP.
- Identificação básica de aplicação: HTTP, DHCP, DNS, NTP.
- Logs CSV atualizados em tempo real em `logs/`:
	- `logs/internet.csv`: timestamp, protocolo (IPv4/IPv6/ICMP), src, dst, ip_proto, info, tamanho_bytes.
	- `logs/transporte.csv`: timestamp, protocolo (TCP/UDP), src, sport, dst, dport, tamanho_bytes.
	- `logs/aplicacao.csv`: timestamp, protocolo (HTTP/DHCP/DNS/NTP/outro), info.
- Interface texto com contadores por protocolo e estatísticas por cliente (IP do túnel `172.31.66.0/24` por padrão): endpoints remotos, portas, protocolos, conexões (SYN), pacotes e volume.

## Requisitos de Execução (Modo Python Direto)
- Linux com suporte a AF_PACKET (ex.: containers / VMs Linux).
- Permissão de captura raw (root ou `CAP_NET_RAW`).
- Interface `tun0` ativa e tráfego passando por ela (modo proxy do túnel do enunciado).

## Estrutura do Projeto
- `main.py`: ponto de entrada do CLI.
- `src/monitor/`: módulos de captura, parsing, logging e UI.

## Execução Direta (Sem Docker)
```bash
# Recomendado: Python 3.10+
# Execute com privilégios (necessário para AF_PACKET):
sudo -E python3 main.py -i tun0 --client-subnet 172.31.66.0/24

# Opções:
#  -i/--interface       Interface de captura (padrão: tun0)
#  --client-subnet      Sub-rede dos clientes no túnel (padrão: 172.31.66.0/24)
```

### Visualização de Logs (Tempo Real)
```bash
tail -f logs/internet.csv
tail -f logs/transporte.csv
tail -f logs/aplicacao.csv
```

### Observações Importantes
- A captura em `tun0` pode não incluir cabeçalho Ethernet. O capturador se adapta automaticamente.
- Em ambientes sem privilégios, o programa exibirá erro de permissão ao abrir socket raw.
- A identificação de aplicação é heurística e limitada ao header inicial dos protocolos.

### Relatório e Evidências
- Inclua no relatório prints da interface texto em execução e trechos dos CSVs com tráfego real capturado em uma rede com túnel, NAT e roteamento conforme o enunciado.
 
## Execução via Docker Compose

Para facilitar testes, há uma configuração containerizada com:
- 1 container proxy (túnel + monitor Python)
- 2 containers clientes (túnel + geração de tráfego HTTP/DNS/NTP)

### Pré-requisitos Docker
- Docker ou Podman compatível com `docker compose`
- Host Linux (recomendado) ou WSL2 com acesso ao dispositivo `/dev/net/tun`

### Componentes da Stack
- `Dockerfile`: imagem base Debian com dependências e túnel compilado.
- `docker-compose.yml`: define serviços `proxy`, `client1`, `client2` com capacidades de rede.
- `scripts/entrypoint.sh`: controla modo server ou client via variável `ROLE`.
- `scripts/generate_traffic.sh`: gera tráfego periódico (HTTP/DNS/NTP) nos clientes.

### Subir Rápido
```bash
docker compose up --build
```
Ver logs do monitor:
```bash
docker compose logs -f proxy
```
Encerrar:
```bash
docker compose down
```

### Variáveis e Ajustes
- Variáveis: `INTERFACE`, `CLIENT_SCRIPT`, `CLIENT_SUBNET` podem ser definidas no `docker-compose.yml`.
- Para mais clientes, duplique o bloco `client2` e ajuste `CLIENT_SCRIPT`.

### Limitações Atuais
- Requer `CAP_NET_ADMIN` e `CAP_NET_RAW` + acesso `/dev/net/tun`.
- Em ambiente não-TTY o monitor não limpa a tela (evita poluição de logs).

### Comando Único Básico
```bash
docker compose up --build
```
Após ~10–15s a interface `tun0` deve estar ativa e os CSV em `logs/` sendo preenchidos.

## Geração de Tráfego Adicional para o Relatório

Como o túnel atual não encaminha plenamente tráfego entre clientes (sem forwarding completo), alguns protocolos de aplicação podem não surgir automaticamente. Abaixo estão estratégias para enriquecer os logs sem alterar o binário C:

1. Limpar logs antes de um novo experimento:
	```bash
	rm -f logs/*.csv
	docker compose down
	docker compose up --build -d
	```
2. Verificar estado do proxy e da interface:
	```bash
	docker logs -f proxy
	docker exec proxy-monitor ip addr show tun0
	```
3. Iniciar um servidor HTTP no cliente (gera tráfego TCP observável):
	```bash
	docker exec -d client1-tunnel python3 -m http.server 8080 --bind 172.31.66.101
	```
4. Gerar tentativas de acesso via túnel (do proxy para o cliente):
	```bash
	docker exec proxy-monitor curl --interface tun0 -v http://172.31.66.101:8080/ || true
	```
	Isso cria entradas TCP em `logs/transporte.csv` (mesmo que a conexão não estabeleça payload completo). Pacotes de tamanho 60 normalmente indicam SYN/ACK/keepalive sem payload — podendo não aparecer em `aplicacao.csv`.
5. Observar crescimento dos arquivos:
	```bash
	docker exec proxy-monitor wc -l logs/*.csv
	docker exec proxy-monitor tail -n 20 logs/transporte.csv
	```
6. ICMP/IPv6 (mensagens de vizinhança) aparecem naturalmente em `internet.csv`. Para forçar mais eventos:
	```bash
	docker exec client2-tunnel ping -c 3 172.31.66.101 || true
	docker exec client1-tunnel ping -c 3 172.31.66.102 || true
	```
	(Podem falhar sem forwarding; ainda assim alguns pacotes de controle IPv6 podem ser capturados.)

### Dicas para Capturar HTTP em `aplicacao.csv`
O parser de aplicação registra linhas quando um pacote contém texto iniciando com um método HTTP (GET/POST/...) ou linha de status (HTTP/1.1 ...). Se apenas segmentos sem payload forem vistos, nada será gravado em `aplicacao.csv`.

Opções para gerar payload HTTP real:
- Implementar forwarding no túnel (modificação mais profunda em C) para permitir fluxo completo.
- Adicionar um servidor HTTP dentro do próprio `proxy-monitor` e gerar requisições internas mapeadas para a tun (pode exigir ajuste de rotas para que os pacotes atravessem `tun0`).

## Workflow Resumido
```bash
# 1. Subir ambiente
docker compose up --build -d

# 2. Verificar monitor
docker logs -f proxy

# 3. Gerar tráfego adicional
docker exec -d client1-tunnel python3 -m http.server 8080 --bind 172.31.66.101
docker exec proxy-monitor curl --interface tun0 -v http://172.31.66.101:8080/ || true

# 4. Coletar amostras
docker exec proxy-monitor wc -l logs/*.csv
docker exec proxy-monitor tail -n 10 logs/internet.csv
docker exec proxy-monitor tail -n 10 logs/transporte.csv
docker exec proxy-monitor tail -n 10 logs/aplicacao.csv

# 5. Limpar e repetir (se necessário)
rm -f logs/*.csv
docker compose down && docker compose up --build -d
```

## Licença / Uso
Projeto acadêmico para fins educacionais; não otimizado para produção.

## Demo Rápida Sem Túnel (Fallback)

Caso o ambiente de túnel esteja indisponível, é possível demonstrar a captura e
classificação usando a interface física (ex.: `eth0`). O script
`scripts/demo_no_tunnel.sh`:

1. Limpa arquivos CSV em `logs/`.
2. Inicia o monitor em segundo plano apontando para `eth0`.
3. Gera tráfego HTTP/DNS/NTP (se ferramentas disponíveis) por alguns ciclos.
4. Finaliza o monitor e mostra um resumo inicial dos CSVs + extratos da UI.

Execução:
```bash
sudo bash scripts/demo_no_tunnel.sh
```
Variáveis opcionais:
- `MON_IF` (padrão `eth0`)
- `CLIENT_SUBNET` (padrão `0.0.0.0/0` para tratar todo IPv4 como cliente)
- `ROUNDS` número de ciclos (padrão 3)
- `SLEEP_BETWEEN` intervalo entre ciclos (padrão 3s)

Saída esperada: preenchimento de `logs/internet.csv`, `logs/transporte.csv` e
`logs/aplicacao.csv` com pacotes reais (IPv4/TCP, DNS, HTTP, etc.). Caso algum
protocolo específico não apareça, verifique se o comando associado (ex.: `dig`,
`ntpdate`) está instalado.
