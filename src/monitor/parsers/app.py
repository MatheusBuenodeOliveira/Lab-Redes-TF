import struct
from typing import Dict, Optional


HTTP_METHODS = {b'GET', b'POST', b'PUT', b'DELETE', b'HEAD', b'PATCH', b'OPTIONS'}


def sniff_http(payload: bytes) -> Optional[str]:
    # Identifica HTTP por método ou prefixo HTTP/. Remove quebras e normaliza espaços.
    try:
        head = payload[:8]
        if any(head.startswith(m) for m in HTTP_METHODS) or head.startswith(b'HTTP/'):
            raw = payload.split(b"\r\n\r\n", 1)[0][:256]
            decoded = raw.decode(errors='ignore')
            decoded = decoded.replace('\r', ' ').replace('\n', ' ')
            decoded = ' '.join(decoded.split())  # colapsa múltiplos espaços
            return decoded
    except Exception:
        return None
    return None


def sniff_dns(payload: bytes) -> Optional[str]:
    # DNS header: 12 bytes mínimo
    if len(payload) < 12:
        return None
    try:
        (tid, flags, qdcount, ancount, nscount, arcount) = struct.unpack('!HHHHHH', payload[:12])
        qr = (flags >> 15) & 1
        opcode = (flags >> 11) & 0xF
        rcode = flags & 0xF
        return f"DNS tid={tid} qr={qr} opcode={opcode} rcode={rcode} qd={qdcount} an={ancount}"
    except struct.error:
        return None


def sniff_dhcp(payload: bytes) -> Optional[str]:
    # DHCPv4 sobre BOOTP: mínimo 240 bytes incluindo opções até magic cookie
    if len(payload) < 240:
        return None
    try:
        op = payload[0]
        xid = struct.unpack('!I', payload[4:8])[0]
        yiaddr = '.'.join(str(b) for b in payload[16:20])
        siaddr = '.'.join(str(b) for b in payload[20:24])
        ciaddr = '.'.join(str(b) for b in payload[12:16])
        return f"DHCP op={op} xid={xid} yiaddr={yiaddr} siaddr={siaddr} ciaddr={ciaddr}"
    except Exception:
        return None


def sniff_ntp(payload: bytes) -> Optional[str]:
    # NTP: 48 bytes
    if len(payload) < 48:
        return None
    li_vn_mode = payload[0]
    vn = (li_vn_mode >> 3) & 0x7
    mode = li_vn_mode & 0x7
    return f"NTP v={vn} mode={mode}"


def identify_app(src_port: int, dst_port: int, payload: bytes) -> Optional[Dict]:
    """
    Identifica protocolo de aplicação com base em portas bem conhecidas e/ou assinatura.
    Retorna dict com 'name' e 'info' (string curta) ou None.
    """
    sp, dp = src_port, dst_port
    # HTTP: tipicamente 80/8080/8000/443 (TLS impede parse do conteúdo). Assinatura textual ajuda.
    http_info = sniff_http(payload)
    if http_info and (sp in (80, 8080, 8000) or dp in (80, 8080, 8000)):
        return {'name': 'HTTP', 'info': http_info}

    # DNS: porta 53 UDP/TCP
    if 53 in (sp, dp):
        info = sniff_dns(payload)
        return {'name': 'DNS', 'info': info or ''}

    # DHCP: portas 67/68 UDP
    if (sp, dp) in ((67, 68), (68, 67)) or sp in (67, 68) or dp in (67, 68):
        info = sniff_dhcp(payload)
        return {'name': 'DHCP', 'info': info or ''}

    # NTP: porta 123 UDP
    if 123 in (sp, dp):
        info = sniff_ntp(payload)
        return {'name': 'NTP', 'info': info or ''}

    return None
