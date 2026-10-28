"""Bounded network probe. APT remains responsible for repository signatures."""
from http.client import HTTPException
from urllib.request import Request, urlopen

PROBE_URL = 'https://archive.ubuntu.com/ubuntu/dists/noble/InRelease'


def network_check():
    try:
        request = Request(PROBE_URL, headers={'User-Agent': 'EroDist-Installer/1.0', 'Range': 'bytes=0-255'})
        with urlopen(request, timeout=8) as response:
            if response.status not in (200, 206) or not response.read(256).startswith(b'-----BEGIN PGP SIGNED MESSAGE-----'):
                return False, 'Архив Ubuntu не подтвердил доступ. Проверьте сеть, время и страницу входа Wi-Fi.'
        return True, 'Архив Ubuntu доступен. Остальные зеркала, подписи и зависимости проверит APT при установке.'
    except (OSError, ValueError, HTTPException):
        return False, 'Нет подтверждённого доступа к архиву Ubuntu. Подключите интернет и нажмите «Проверить ещё раз».'
