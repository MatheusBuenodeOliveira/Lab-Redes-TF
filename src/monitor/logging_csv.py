import csv
import os
import threading
from datetime import datetime
from typing import Dict, Optional


class CsvLogger:
    """
    Logger CSV com flush imediato, thread-safe.
    """
    def __init__(self, path: str, headers: list[str]) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._fh = open(path, 'a', newline='', encoding='utf-8')
        self._csv = csv.writer(self._fh)
        self._lock = threading.Lock()
        # Escreve cabeçalho se arquivo está vazio
        if self._fh.tell() == 0:
            self._csv.writerow(headers)
            self._fh.flush()

    def write_row(self, row: list) -> None:
        with self._lock:
            self._csv.writerow(row)
            self._fh.flush()

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass


class InternetLogger:
    def __init__(self, base_dir: str = 'logs') -> None:
        self.logger = CsvLogger(os.path.join(base_dir, 'internet.csv'), [
            'timestamp', 'protocolo', 'src_ip', 'dst_ip', 'ip_proto', 'info', 'tamanho_bytes'
        ])

    def log(self, proto_name: str, src_ip: str, dst_ip: str, ip_proto: int, info: str, size: int) -> None:
        self.logger.write_row([
            datetime.utcnow().isoformat(), proto_name, src_ip, dst_ip, ip_proto, info, size
        ])


class TransporteLogger:
    def __init__(self, base_dir: str = 'logs') -> None:
        self.logger = CsvLogger(os.path.join(base_dir, 'transporte.csv'), [
            'timestamp', 'protocolo', 'src_ip', 'src_port', 'dst_ip', 'dst_port', 'tamanho_bytes'
        ])

    def log(self, proto_name: str, src_ip: str, src_port: int, dst_ip: str, dst_port: int, size: int) -> None:
        self.logger.write_row([
            datetime.utcnow().isoformat(), proto_name, src_ip, src_port, dst_ip, dst_port, size
        ])


class AplicacaoLogger:
    def __init__(self, base_dir: str = 'logs') -> None:
        self.logger = CsvLogger(os.path.join(base_dir, 'aplicacao.csv'), [
            'timestamp', 'protocolo', 'info'
        ])

    def log(self, app_name: str, info: str) -> None:
        self.logger.write_row([
            datetime.utcnow().isoformat(), app_name, info
        ])
