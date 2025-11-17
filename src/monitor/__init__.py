"""
Monitor de Tráfego de Rede em Tempo Real (Trabalho Final de Laboratório de Redes)

Este pacote contém os componentes principais:
- capture: captura pacotes via raw socket na interface (ex.: tun0)
- parsers: interpretadores das camadas IP/IPv6/ICMP, TCP/UDP e protocolos de aplicação
- logging: escrita de logs CSV em tempo real (internet.csv, transporte.csv, aplicacao.csv)
- stats: agregação de estatísticas por cliente (IP no túnel) e por destino
- ui: interface em modo texto para exibir contadores e estatísticas
- main (em nível superior): CLI para executar o monitor

Importante: Captura raw requer privilégios (root ou CAP_NET_RAW).
"""
