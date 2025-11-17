from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass
class EndpointStats:
    packets: int = 0
    bytes: int = 0
    tcp_connections: int = 0  # contado via SYN
    ports: Dict[int, int] = field(default_factory=lambda: defaultdict(int))  # porta -> contagem
    protocols: Dict[str, int] = field(default_factory=lambda: defaultdict(int))  # nome -> contagem


@dataclass
class ClientStats:
    total_packets: int = 0
    total_bytes: int = 0
    proto_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    endpoints: Dict[str, EndpointStats] = field(default_factory=dict)  # remote_ip -> EndpointStats


class Stats:
    """Agrega estatísticas por cliente (IP da rede túnel) e globais."""

    def __init__(self) -> None:
        self.clients: Dict[str, ClientStats] = {}
        self.global_proto: Dict[str, int] = defaultdict(int)

    def _get_client(self, client_ip: str) -> ClientStats:
        cs = self.clients.get(client_ip)
        if not cs:
            cs = ClientStats()
            self.clients[client_ip] = cs
        return cs

    def add_packet(self, client_ip: str, remote_ip: str, proto_name: str, length: int, dst_port: int | None = None, is_tcp_syn: bool = False) -> None:
        cs = self._get_client(client_ip)
        es = cs.endpoints.get(remote_ip)
        if not es:
            es = EndpointStats()
            cs.endpoints[remote_ip] = es
        # Atualizações
        cs.total_packets += 1
        cs.total_bytes += length
        cs.proto_counts[proto_name] += 1
        self.global_proto[proto_name] += 1

        es.packets += 1
        es.bytes += length
        es.protocols[proto_name] += 1
        if dst_port is not None:
            es.ports[dst_port] += 1
        if is_tcp_syn:
            es.tcp_connections += 1

    def snapshot(self) -> Dict:
        # Retorna vista imutável básica para UI
        out: Dict[str, Dict] = {
            'global_proto': dict(self.global_proto),
            'clients': {}
        }
        for cip, cs in self.clients.items():
            out['clients'][cip] = {
                'total_packets': cs.total_packets,
                'total_bytes': cs.total_bytes,
                'proto_counts': dict(cs.proto_counts),
                'endpoints': {
                    rip: {
                        'packets': es.packets,
                        'bytes': es.bytes,
                        'tcp_connections': es.tcp_connections,
                        'top_ports': sorted(es.ports.items(), key=lambda x: x[1], reverse=True)[:5],
                        'top_protocols': sorted(es.protocols.items(), key=lambda x: x[1], reverse=True)[:5],
                    } for rip, es in cs.endpoints.items()
                }
            }
        return out
