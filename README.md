# Monitor de Tráfego de Rede (Trabalho Final)

Este projeto implementa, em Python (sockets raw), um monitor de tráfego em tempo real para a interface `tun0`, conforme o enunciado do trabalho final de Laboratório de Redes.

Funcionalidades principais:
- Captura pacotes via raw socket na interface indicada (padrão: `tun0`).
- Parsing de camadas: IPv4/IPv6/ICMP, TCP/UDP.
- Identificação básica de aplicação: HTTP, DHCP, DNS, NTP.
- Logs CSV atualizados em tempo real em `logs/`:
	- `logs/internet.csv`: timestamp, protocolo (IPv4/IPv6/ICMP), src, dst, ip_proto, info, tamanho_bytes.
	- `logs/transporte.csv`: timestamp, protocolo (TCP/UDP), src, sport, dst, dport, tamanho_bytes.
	- `logs/aplicacao.csv`: timestamp, protocolo (HTTP/DHCP/DNS/NTP/outro), info.
- Interface texto com contadores por protocolo e estatísticas por cliente (IP do túnel `172.31.66.0/24` por padrão): endpoints remotos, portas, protocolos, conexões (SYN), pacotes e volume.

Requisitos de execução:
- Linux com suporte a AF_PACKET (ex.: containers / VMs Linux).
- Permissão de captura raw (root ou `CAP_NET_RAW`).
- Interface `tun0` ativa e tráfego passando por ela (modo proxy do túnel do enunciado).

Estrutura do projeto:
- `main.py`: ponto de entrada do CLI.
- `src/monitor/`: módulos de captura, parsing, logging e UI.

Como executar
```bash
# Recomendado: Python 3.10+
# Execute com privilégios (necessário para AF_PACKET):
sudo -E python3 main.py -i tun0 --client-subnet 172.31.66.0/24

# Opções:
#  -i/--interface       Interface de captura (padrão: tun0)
#  --client-subnet      Sub-rede dos clientes no túnel (padrão: 172.31.66.0/24)
```

Visualização de logs (em tempo real)
```bash
tail -f logs/internet.csv
tail -f logs/transporte.csv
tail -f logs/aplicacao.csv
```

Observações importantes
- A captura em `tun0` pode não incluir cabeçalho Ethernet. O capturador se adapta automaticamente.
- Em ambientes sem privilégios, o programa exibirá erro de permissão ao abrir socket raw.
- A identificação de aplicação é heurística e limitada ao header inicial dos protocolos.

Relatório e evidências
- Inclua no relatório prints da interface texto em execução e trechos dos CSVs com tráfego real capturado em uma rede com túnel, NAT e roteamento conforme o enunciado.
 
## Execução via Docker Compose

Para facilitar testes, há uma configuração containerizada com:
- 1 container proxy (túnel + monitor Python)
- 2 containers clientes (túnel + geração de tráfego HTTP/DNS/NTP)

### Pré-requisitos
- Docker ou Podman compatível com `docker compose`
- Host Linux (recomendado) ou WSL2 com acesso ao dispositivo `/dev/net/tun`

### Arquivos adicionados
- `Dockerfile`: imagem base Debian com dependências e túnel compilado.
- `docker-compose.yml`: define serviços `proxy`, `client1`, `client2` com capacidades de rede.
- `scripts/entrypoint.sh`: controla modo server ou client via variável `ROLE`.
- `scripts/generate_traffic.sh`: gera tráfego periódico (HTTP/DNS/NTP) nos clientes.

### Uso rápido
```bash
docker compose up --build
```
Monitor:
```bash
docker compose logs -f proxy
```
Encerrar:
```bash
docker compose down
```

### Ajustes
- Variáveis: `INTERFACE`, `CLIENT_SCRIPT`, `CLIENT_SUBNET` podem ser definidas no `docker-compose.yml`.
- Para mais clientes, duplique o bloco `client2` e ajuste `CLIENT_SCRIPT`.

### Limitações
- Requer `CAP_NET_ADMIN` e `CAP_NET_RAW` + acesso `/dev/net/tun`.
- Em ambiente não-TTY o monitor não limpa a tela (evita poluição de logs).

### Comando único para teste
```bash
docker compose up --build
```
Após ~10–15s a interface `tun0` deve estar ativa e os CSV em `logs/` sendo preenchidos.