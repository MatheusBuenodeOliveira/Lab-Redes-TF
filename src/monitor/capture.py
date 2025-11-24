import socket
import struct
import sys
import os
import fcntl
from typing import Optional, Tuple


class RawCapture:
    """Captura pacotes na interface informada.

    Dois modos:
    - AF_PACKET (camada 2) para interfaces "normais" (ex.: eth0).
    - Leitura direta do /dev/net/tun quando interface começa com "tun".

    O modo TUN permite observar pacotes injetados e recebidos mesmo quando o
    AF_PACKET não entrega quadros (caso comum em túnel criado manualmente).
    """

    def __init__(self, interface: str) -> None:
        self.interface = interface
        self.sock: Optional[socket.socket] = None
        self.tun_fd: Optional[int] = None
        self.mode: str = 'af_packet'

    def open(self) -> None:
        # Usa modo TUN se nome da interface começa com 'tun'
        if self.interface.startswith('tun'):
            self._open_tun()
            return
        try:
            ETH_P_ALL = 0x0003
            self.sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
            self.sock.bind((self.interface, 0))
            self.mode = 'af_packet'
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

    def _open_tun(self) -> None:
        # Abre /dev/net/tun e associa-se à interface. Cria se necessário via ioctl.
        TUNSETIFF = 0x400454ca
        IFF_TUN = 0x0001
        IFF_NO_PI = 0x1000
        name = self.interface.encode()
        if len(name) > 15:
            raise ValueError("Nome de interface TUN muito longo")
        ifr = struct.pack('16sH', name, IFF_TUN | IFF_NO_PI)
        try:
            fd = os.open('/dev/net/tun', os.O_RDWR)
            fcntl.ioctl(fd, TUNSETIFF, ifr)
            self.tun_fd = fd
            self.mode = 'tun'
        except OSError as e:
            print(f"Falha ao abrir /dev/net/tun para {self.interface}: {e}", file=sys.stderr)
            raise

    def close(self) -> None:
        if self.mode == 'af_packet' and self.sock:
            try:
                self.sock.close()
            finally:
                self.sock = None
        if self.mode == 'tun' and self.tun_fd is not None:
            try:
                os.close(self.tun_fd)
            finally:
                self.tun_fd = None

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
        if self.mode == 'af_packet':
            if not self.sock:
                raise RuntimeError("Socket não inicializado")
            data, _addr = self.sock.recvfrom(65535)
            return data
        if self.mode == 'tun':
            if self.tun_fd is None:
                raise RuntimeError("FD TUN não inicializado")
            # Leitura direta do pacote IP (sem Ethernet); tamanho máximo típico MTU
            return os.read(self.tun_fd, 65535)
        raise RuntimeError("Modo de captura inválido")
