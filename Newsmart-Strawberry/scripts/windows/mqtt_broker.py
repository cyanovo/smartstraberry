"""One broker with credential-free access limited to loopback and local LANs."""

import asyncio
import json
import subprocess

from amqtt.broker import Broker


def local_networks():
    command = (
        "$ErrorActionPreference = 'Stop'; @("
        "Get-NetAdapter -Physical | Where-Object Status -eq 'Up' | ForEach-Object { "
        "Get-NetIPAddress -InterfaceIndex $_.ifIndex -AddressFamily IPv4 | "
        "Where-Object AddressState -eq 'Preferred' | ForEach-Object { "
        "'{0}/{1}' -f $_.IPAddress, $_.PrefixLength } }) | ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ['powershell.exe', '-NoProfile', '-Command', command],
        capture_output=True, text=True, check=True, timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    networks = json.loads(result.stdout) if result.stdout.strip() else []
    return [networks] if isinstance(networks, str) else networks


async def main():
    networks = local_networks()
    broker = Broker({
        'listeners': {
            # AMQTT inherits fields equal to library defaults from this listener.
            'default': {'type': 'tcp', 'bind': '0.0.0.0:1883', 'max_connections': 32},
            'backend': {'type': 'tcp', 'bind': '127.0.0.1:11883'},
        },
        'plugins': {'mqtt_auth.LocalHardwareAuth': {'allowed_networks': networks}},
    })
    await broker.start()
    print(f'MQTT ready: API 127.0.0.1:11883; hardware LAN:1883; credentials ignored; LANs: {networks}', flush=True)
    try:
        await asyncio.Event().wait()
    finally:
        await broker.shutdown()


if __name__ == '__main__':
    asyncio.run(main())
