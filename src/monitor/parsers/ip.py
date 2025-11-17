import ipaddress
import struct
from typing import Dict, Optional, Tuple, Union


def parse_ipv4(packet: bytes) -> Optional[Dict]:
    if len(packet) < 20:
        return None
    ver_ihl = packet[0]
    version = ver_ihl >> 4
    ihl = (ver_ihl & 0x0F) * 4
    if version != 4 or ihl < 20 or len(packet) < ihl:
        return None
    total_length = struct.unpack('!H', packet[2:4])[0]
    proto = packet[9]
    src = ipaddress.IPv4Address(packet[12:16]).compressed
    dst = ipaddress.IPv4Address(packet[16:20]).compressed
    payload = packet[ihl:total_length] if total_length <= len(packet) else packet[ihl:]
    return {
        'version': 4,
        'ihl': ihl,
        'proto': proto,
        'src': src,
        'dst': dst,
        'total_length': total_length,
        'payload': payload,
    }


def parse_ipv6(packet: bytes) -> Optional[Dict]:
    if len(packet) < 40:
        return None
    first = packet[0]
    version = first >> 4
    if version != 6:
        return None
    # IPv6 header: 40 bytes
    payload_len = struct.unpack('!H', packet[4:6])[0]
    next_header = packet[6]
    src = ipaddress.IPv6Address(packet[8:24]).compressed
    dst = ipaddress.IPv6Address(packet[24:40]).compressed
    header_len = 40
    total_length = header_len + payload_len
    payload = packet[header_len:total_length] if total_length <= len(packet) else packet[header_len:]
    return {
        'version': 6,
        'header_len': header_len,
        'next_header': next_header,
        'src': src,
        'dst': dst,
        'total_length': total_length,
        'payload': payload,
    }


def parse_icmpv4(payload: bytes) -> Optional[Dict]:
    if len(payload) < 4:
        return None
    icmp_type = payload[0]
    icmp_code = payload[1]
    return {
        'type': icmp_type,
        'code': icmp_code,
    }


def parse_icmpv6(payload: bytes) -> Optional[Dict]:
    if len(payload) < 4:
        return None
    icmp_type = payload[0]
    icmp_code = payload[1]
    return {
        'type': icmp_type,
        'code': icmp_code,
    }


IPLike = Dict[str, Union[int, str, bytes]]


def parse_ip(packet: bytes) -> Tuple[Optional[IPLike], Optional[str]]:
    """
    Tenta parsear como IPv4 depois IPv6. Retorna (dict_ip, nome_protocolo_cam_internet).
    nome_protocolo_cam_internet = 'IPv4' | 'IPv6' | None
    """
    ipv4 = parse_ipv4(packet)
    if ipv4:
        return ipv4, 'IPv4'
    ipv6 = parse_ipv6(packet)
    if ipv6:
        return ipv6, 'IPv6'
    return None, None
