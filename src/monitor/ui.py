import os
import shutil
import sys
import time
from typing import Dict


def human_bytes(n: int) -> str:
    # Conversão simples para legibilidade
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def render(snapshot: Dict) -> str:
    lines: list[str] = []
    gp = snapshot.get('global_proto', {})
    lines.append("Monitor de Tráfego (Resumo por protocolo)")
    if gp:
        parts = [f"{k}:{v}" for k, v in sorted(gp.items(), key=lambda x: x[0])]
        lines.append("  " + "  ".join(parts))
    else:
        lines.append("  (sem dados)")

    clients = snapshot.get('clients', {})
    for cip, cs in clients.items():
        lines.append("")
        lines.append(f"Cliente {cip}: pkts={cs['total_packets']} bytes={human_bytes(cs['total_bytes'])}")
        pc = cs.get('proto_counts', {})
        if pc:
            parts = [f"{k}:{v}" for k, v in sorted(pc.items(), key=lambda x: -x[1])[:6]]
            lines.append("  Prot.: " + ", ".join(parts))
        endpoints = cs.get('endpoints', {})
        # Mostra top 3 endpoints por número de pacotes
        top_eps = sorted(endpoints.items(), key=lambda x: -x[1]['packets'])[:3]
        for rip, es in top_eps:
            ports = ', '.join(f"{p}:{c}" for p, c in es['top_ports'])
            prots = ', '.join(f"{p}:{c}" for p, c in es['top_protocols'])
            lines.append(f"  -> {rip}: pkts={es['packets']} bytes={human_bytes(es['bytes'])} conns={es['tcp_connections']}")
            if ports:
                lines.append(f"     portas: {ports}")
            if prots:
                lines.append(f"     prot.: {prots}")
    return "\n".join(lines)


def print_periodic(get_snapshot_fn, interval: float = 1.0) -> None:
    """Atualiza a cada intervalo.

    Se stdout não for TTY (ex: logs Docker), não tenta limpar a tela
    para evitar poluir o log com códigos de controle.
    """
    is_tty = sys.stdout.isatty()
    try:
        while True:
            snap = get_snapshot_fn()
            out = render(snap)
            if is_tty:
                # Limpa somente em terminal interativo
                try:
                    cols = shutil.get_terminal_size((100, 24)).columns  # noqa: F841
                except Exception:
                    pass
                os.system('clear')
            print(out)
            if is_tty:
                print("\nCtrl+C para encerrar.")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Encerrando monitor...")
