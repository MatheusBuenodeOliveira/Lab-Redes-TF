import socket
import struct
import sys
from typing import Optional, Tuple


class RawCapture:
    """
    Captura pacotes brutos na interface informada usando AF_PACKET (Linux).

    Observações sobre TUN (interface L3):
    - Interfaces TUN (ex.: tun0) podem fornecer quadros sem cabeçalho Ethernet.
    - Este capturador tenta detectar automaticamente a presença do cabeçalho
      Ethernet; se não houver, trata o payload como IPv4/IPv6 diretamente.
    """

    def __init__(self, interface: str) -> None:
        self.interface = interface
        self.sock: Optional[socket.socket] = None

    def open(self) -> None:
        try:
            # ETH_P_ALL em ordem de rede (arpa/if_ether.h): 0x0003 -> htons(0x0003)
            ETH_P_ALL = 0x0003
            self.sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
            self.sock.bind((self.interface, 0))
            # Tentar aumentar o buffer de recepção um pouco
            try:
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
            except OSError:
                pass
        except PermissionError:
            print("Permissão negada para abrir socket raw. Execute com sudo ou conceda CAP_NET_RAW.", file=sys.stderr)
            raise
        except OSError as e:
            print(f"Falha ao abrir AF_PACKET na interface {self.interface}: {e}", file=sys.stderr)
            raise

    def close(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            finally:
                self.sock = None

    @staticmethod
    def split_l2_l3(frame: bytes) -> Tuple[Optional[bytes], bytes]:
        """
        Retorna (l2, l3). Se não houver cabeçalho Ethernet (caso típico TUN),
        retorna (None, frame) assumindo que começa em IPv4/IPv6.
        """
        # Tentativa 1: Verificar se os primeiros bytes parecem um cabeçalho Ethernet
        if len(frame) >= 14:
            eth_proto = struct.unpack('!H', frame[12:14])[0]
            # 0x0800 IPv4, 0x86DD IPv6 (EtherType mais comuns)
            if eth_proto in (0x0800, 0x86DD):
                return frame[:14], frame[14:]
        # Tentativa 2: Heurística: primeiro nibble 4 (IPv4) ou 6 (IPv6)
        if frame:
            version = (frame[0] >> 4) & 0xF
            if version in (4, 6):
                return None, frame
        # Caso contrário, retorna tudo como L3 para não descartar
        return None, frame

    def recv(self) -> bytes:
        if not self.sock:
            raise RuntimeError("Socket não inicializado")
        data, _addr = self.sock.recvfrom(65535)
        return data
