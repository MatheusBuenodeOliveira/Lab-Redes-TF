import struct
from typing import Dict, Optional


def parse_tcp(payload: bytes) -> Optional[Dict]:
    if len(payload) < 20:
        return None
    src_port, dst_port, seq, ack_seq, offset_reserved_flags = struct.unpack('!HHIIH', payload[:14])
    data_offset = (offset_reserved_flags >> 12) * 4
    if data_offset < 20 or len(payload) < data_offset:
        return None
    flags = offset_reserved_flags & 0x01FF  # 9 bits: NS,CWR,ECE,URG,ACK,PSH,RST,SYN,FIN
    return {
        'protocol': 'TCP',
        'src_port': src_port,
        'dst_port': dst_port,
        'seq': seq,
        'ack': ack_seq,
        'flags': flags,
        'header_len': data_offset,
        'payload': payload[data_offset:],
    }


def parse_udp(payload: bytes) -> Optional[Dict]:
    if len(payload) < 8:
        return None
    src_port, dst_port, length = struct.unpack('!HHH', payload[:6])
    # checksum = payload[6:8]
    app = payload[8:length] if length <= len(payload) else payload[8:]
    return {
        'protocol': 'UDP',
        'src_port': src_port,
        'dst_port': dst_port,
        'length': length,
        'payload': app,
    }
