import struct
import unittest

from src.monitor.parsers.ip import parse_ip
from src.monitor.parsers.transport import parse_tcp, parse_udp
from src.monitor.parsers.app import identify_app


def build_ipv4(proto: int, src: bytes, dst: bytes, payload: bytes) -> bytes:
    version_ihl = (4 << 4) | 5
    tos = 0
    total_length = 20 + len(payload)
    identification = 0
    flags_fragment = 0
    ttl = 64
    header_checksum = 0
    header = struct.pack(
        '!BBHHHBBH4s4s',
        version_ihl,
        tos,
        total_length,
        identification,
        flags_fragment,
        ttl,
        proto,
        header_checksum,
        src,
        dst,
    )
    return header + payload


def build_udp(src_port: int, dst_port: int, app_payload: bytes) -> bytes:
    length = 8 + len(app_payload)
    header = struct.pack('!HHH', src_port, dst_port, length) + b'\x00\x00'
    return header + app_payload


class TestParsers(unittest.TestCase):
    def test_ipv4_udp_dns(self):
        # DNS header mínimo 12 bytes
        dns = struct.pack('!HHHHHH', 0x1234, 0x0100, 1, 0, 0, 0)
        udp = build_udp(12345, 53, dns)
        pkt = build_ipv4(17, b'\xC0\xA8\x01\x02', b'\x08\x08\x08\x08', udp)
        ip_dict, ip_name = parse_ip(pkt)
        self.assertIsNotNone(ip_dict)
        self.assertEqual(ip_name, 'IPv4')
        self.assertEqual(ip_dict['src'], '192.168.1.2')
        self.assertEqual(ip_dict['dst'], '8.8.8.8')
        self.assertEqual(ip_dict['proto'], 17)
        udp_dict = parse_udp(ip_dict['payload'])
        self.assertIsNotNone(udp_dict)
        self.assertEqual(udp_dict['dst_port'], 53)
        app = identify_app(udp_dict['src_port'], udp_dict['dst_port'], udp_dict['payload'])
        self.assertIsNotNone(app)
        self.assertEqual(app['name'], 'DNS')

    def test_http_detection(self):
        http_payload = b'GET / HTTP/1.1\r\nHost: example\r\n\r\n'
        udp = build_udp(50000, 80, http_payload)  # usando UDP só para assinar; assinatura textual é o foco
        pkt = build_ipv4(17, b'\x0A\x00\x00\x01', b'\x0A\x00\x00\x02', udp)
        ip_dict, _ = parse_ip(pkt)
        udp_dict = parse_udp(ip_dict['payload'])
        app = identify_app(udp_dict['src_port'], udp_dict['dst_port'], udp_dict['payload'])
        self.assertIsNotNone(app)
        self.assertEqual(app['name'], 'HTTP')
        self.assertIn('GET / HTTP/1.1', app['info'])

    def test_ntp_detection(self):
        # 48 bytes NTP, com vn=4, mode=3
        li_vn_mode = (0 << 6) | (4 << 3) | 3
        ntp = bytes([li_vn_mode]) + b'\x00' * 47
        udp = build_udp(123, 123, ntp)
        pkt = build_ipv4(17, b'\x7F\x00\x00\x01', b'\x7F\x00\x00\x01', udp)
        ip_dict, _ = parse_ip(pkt)
        udp_dict = parse_udp(ip_dict['payload'])
        app = identify_app(udp_dict['src_port'], udp_dict['dst_port'], udp_dict['payload'])
        self.assertIsNotNone(app)
        self.assertEqual(app['name'], 'NTP')
        self.assertIn('v=4', app['info'])

    def test_dhcp_detection(self):
        # DHCP/BOOTP mínimo 240 bytes
        bootp = bytearray(240)
        bootp[0] = 1  # op request
        # xid em 4..7
        bootp[4:8] = b'\x12\x34\x56\x78'
        # ciaddr, yiaddr, siaddr
        bootp[12:16] = b'\x00\x00\x00\x00'
        bootp[16:20] = b'\x0A\x00\x00\x64'  # 10.0.0.100
        bootp[20:24] = b'\x0A\x00\x00\x01'  # 10.0.0.1
        udp = build_udp(68, 67, bytes(bootp))
        pkt = build_ipv4(17, b'\x0A\x00\x00\x02', b'\x0A\x00\x00\x01', udp)
        ip_dict, _ = parse_ip(pkt)
        udp_dict = parse_udp(ip_dict['payload'])
        app = identify_app(udp_dict['src_port'], udp_dict['dst_port'], udp_dict['payload'])
        self.assertIsNotNone(app)
        self.assertEqual(app['name'], 'DHCP')


if __name__ == '__main__':
    unittest.main()
