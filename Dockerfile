FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    iproute2 \
    iptables \
    python3 python3-venv python3-pip \
    curl dnsutils net-tools iputils-ping ntpdate \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia todo o projeto
COPY . .

# Compila o túnel (deixa binário pronto para reduzir tempo de start)
RUN make -C traffic_tunnel

# Cria venv opcional (não há deps externas, mas deixa pronto)
RUN python3 -m venv .venv
ENV PATH="/app/.venv/bin:${PATH}"

# Reorganiza scripts: copia somente diretório scripts e garante permissões
RUN mkdir -p scripts
COPY scripts/ scripts/
RUN sed -i 's/\r$//' scripts/*.sh && chmod +x scripts/*.sh traffic_tunnel/*.sh

# Define entrypoint apontando para caminho absoluto dentro do WORKDIR
ENTRYPOINT ["bash","scripts/entrypoint.sh"]
