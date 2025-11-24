import argparse
import ipaddress
import signal
import sys
import threading
from datetime import datetime

from .capture import RawCapture
from .parsers.ip import parse_ip, parse_icmpv4, parse_icmpv6
from .parsers.transport import parse_tcp, parse_udp
from .parsers.app import identify_app
from .logging_csv import InternetLogger, TransporteLogger, AplicacaoLogger
from .stats import Stats
from . import ui


class Monitor:
    def __init__(self, interface: str, client_subnet: str | None = None) -> None:
        self.interface = interface
        # Sub-rede padrão do enunciado (pode ser ajustada via CLI)
        self.client_net = ipaddress.ip_network(client_subnet or '172.31.66.0/24', strict=False)
        self.cap = RawCapture(interface)
        self.stats = Stats()
        self.internet_log = InternetLogger()
        self.transp_log = TransporteLogger()
        self.app_log = AplicacaoLogger()
        self._stop = threading.Event()

    def start(self) -> None:
        self.cap.open()
        t = threading.Thread(target=self._loop_capture, daemon=True)
        t.start()
        # Mantém execução contínua até interrupção externa (Ctrl+C / signal)
        ui.print_periodic(self.stats.snapshot, interval=1.0)

    def stop(self) -> None:
        self._stop.set()
        try:
            self.cap.close()
        except Exception:
            pass

    def _loop_capture(self) -> None:
        while not self._stop.is_set():
            try:
                frame = self.cap.recv()
            except Exception:
                break
            # Separa L2/L3
            _l2, l3 = self.cap.split_l2_l3(frame)
            ip_pkt, ip_name = parse_ip(l3)
            if not ip_pkt or not ip_name:
                continue

            if ip_pkt['version'] == 4:
                ip_src = ip_pkt['src']
                ip_dst = ip_pkt['dst']
                ip_proto = ip_pkt['proto']
                ip_payload = ip_pkt['payload']
            else:
                ip_src = ip_pkt['src']
                ip_dst = ip_pkt['dst']
                ip_proto = ip_pkt['next_header']
                ip_payload = ip_pkt['payload']

            total_len = ip_pkt['total_length']

            # Log da camada de internet (IPv4/IPv6/ICMP)
            info_internet = ''
            if ip_name == 'IPv4' and ip_proto == 1:  # ICMPv4
                icmp = parse_icmpv4(ip_payload)
                if icmp:
                    info_internet = f"ICMP type={icmp['type']} code={icmp['code']}"
                self.internet_log.log('ICMP', ip_src, ip_dst, ip_proto, info_internet, total_len)
            elif ip_name == 'IPv6' and ip_proto == 58:  # ICMPv6
                icmp6 = parse_icmpv6(ip_payload)
                if icmp6:
                    info_internet = f"ICMPv6 type={icmp6['type']} code={icmp6['code']}"
                self.internet_log.log('ICMP', ip_src, ip_dst, ip_proto, info_internet, total_len)
            else:
                self.internet_log.log(ip_name, ip_src, ip_dst, ip_proto, info_internet, total_len)

            # Camada de transporte
            transp = None
            proto_name = None
            dst_port = None
            is_tcp_syn = False

            if ip_proto == 6:  # TCP
                transp = parse_tcp(ip_payload)
                if transp:
                    proto_name = 'TCP'
                    dst_port = transp['dst_port']
                    # SYN flag: bit 1 (mask 0x002) na nossa máscara de 9 bits (0..8) -> 0x002
                    is_tcp_syn = bool(transp['flags'] & 0x002)
                    self.transp_log.log('TCP', ip_src, transp['src_port'], ip_dst, transp['dst_port'], total_len)
                    app = identify_app(transp['src_port'], transp['dst_port'], transp['payload'])
                    if app:
                        self.app_log.log(app['name'], app.get('info', '')[:300])
            elif ip_proto == 17:  # UDP
                transp = parse_udp(ip_payload)
                if transp:
                    proto_name = 'UDP'
                    dst_port = transp['dst_port']
                    self.transp_log.log('UDP', ip_src, transp['src_port'], ip_dst, transp['dst_port'], total_len)
                    app = identify_app(transp['src_port'], transp['dst_port'], transp['payload'])
                    if app:
                        self.app_log.log(app['name'], app.get('info', '')[:300])
            elif (ip_proto == 1 and ip_name == 'IPv4') or (ip_proto == 58 and ip_name == 'IPv6'):
                # ICMP (v4 ou v6), já logado em internet
                proto_name = 'ICMP'
            else:
                proto_name = ip_name  # Outros mantêm nome IP

            # Estatísticas por cliente (IP na rede túnel)
            try:
                src_ip_obj = ipaddress.ip_address(ip_src)
                dst_ip_obj = ipaddress.ip_address(ip_dst)
                # Considera cliente se src está na sub-rede do túnel
                if src_ip_obj.version == 4 and src_ip_obj in self.client_net:
                    client_ip = ip_src
                    remote_ip = ip_dst
                elif dst_ip_obj.version == 4 and dst_ip_obj in self.client_net:
                    # Conta tráfego de retorno para o cliente também
                    client_ip = ip_dst
                    remote_ip = ip_src
                else:
                    client_ip = None
                    remote_ip = None
            except ValueError:
                client_ip = None
                remote_ip = None

            if client_ip and remote_ip and proto_name:
                self.stats.add_packet(client_ip, remote_ip, proto_name, total_len, dst_port=dst_port, is_tcp_syn=is_tcp_syn)


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='Monitor de Tráfego em Tempo Real (raw socket)')
    p.add_argument('-i', '--interface', default='tun0', help='Interface de captura (padrão: tun0)')
    p.add_argument('--client-subnet', default='172.31.66.0/24', help='Sub-rede dos clientes no túnel (padrão: 172.31.66.0/24)')
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_argparser().parse_args(argv)
    mon = Monitor(interface=args.interface, client_subnet=args.client_subnet)

    def handle_sigint(_sig, _frm):
        mon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    try:
        mon.start()
    except KeyboardInterrupt:
        pass
    except PermissionError:
        return 1
    except Exception as e:
        print(f"Erro: {e}")
        return 1
    finally:
        mon.stop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
