"""Read-only local identity/hardware information. No telemetry."""
import json
import os
from pathlib import Path
import platform
import re
import subprocess


def identity():
    base = json.loads(Path('/usr/share/erodist-neon/base.json').read_text())
    status_path = Path('/var/lib/erodist/installation.json')
    if status_path.exists():
        try:
            state = json.loads(status_path.read_text())
            if not isinstance(state, dict):
                raise ValueError('Invalid installation status')
            base['edition'] = state.get('edition', 'unknown')
            base['status'] = state.get('status', 'unknown')
        except (ValueError, OSError):
            base.update(edition='unknown', status='unreadable')
    else:
        base['status'] = 'live' if 'boot=casper' in Path('/proc/cmdline').read_text().split() else 'unconfigured'
        if base['status'] != 'live':
            base['edition'] = 'unknown'
    return base


def virtualization():
    if Path('/sys/bus/vmbus').exists():
        return 'Hyper-V / Microsoft Hypervisor (обнаружена шина VMBus)'
    return 'Не определена; это не проверка наличия аппаратного ускорения'


def collect():
    data = identity()
    labels = {'home': 'Home', 'pro': 'Pro', 'program': 'Program', 'live': 'Live — редакция выбирается при установке'}
    cpuinfo = Path('/proc/cpuinfo').read_text(errors='replace')
    cpu = re.search(r'^model name\s*:\s*(.*)$', cpuinfo, re.M)
    mem = re.search(r'^MemTotal:\s*(\d+)', Path('/proc/meminfo').read_text(), re.M)
    try:
        gpu = subprocess.run(['lspci'], capture_output=True, text=True, timeout=8, check=True).stdout
        gpu = '\n'.join(line for line in gpu.splitlines() if re.search('VGA|3D controller|Display controller', line)) or 'Не определено'
    except (OSError, subprocess.SubprocessError):
        gpu = 'Не определено'
    return '\n'.join([
        f"EroDist {labels.get(data['edition'], data['edition'])}",
        f"Версия: {data['version']}", f"Создатель: {data['creator']}", f"Основа: {data['base']}",
        f"Состояние установки редакции: {data['status']}",
        f'Ядро: {platform.release()} ({platform.machine()})',
        'Загрузка: ' + ('UEFI' if Path('/sys/firmware/efi').exists() else 'BIOS'),
        f"Процессор: {cpu.group(1) if cpu else platform.machine()} · потоков: {os.cpu_count()}",
        f"RAM: {int(mem.group(1))/1048576:.1f} ГиБ" if mem else 'RAM: не определено',
        'Среда: ' + virtualization(),
        'Графика:\n' + gpu,
    ])
