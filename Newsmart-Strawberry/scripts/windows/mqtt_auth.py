"""Allow local hardware regardless of the credentials stored on the device."""

import ipaddress
from dataclasses import dataclass, field

from amqtt.plugins.base import BaseAuthPlugin


class LocalHardwareAuth(BaseAuthPlugin):
    @dataclass
    class Config:
        allowed_networks: list[str] = field(default_factory=list)

    def __init__(self, context):
        super().__init__(context)
        self.networks = [ipaddress.ip_network(value, strict=False) for value in self.config.allowed_networks]

    async def authenticate(self, *, session):
        if not session:
            return False
        try:
            address = ipaddress.ip_address(session.remote_address)
        except (ValueError, TypeError):
            return False
        return address.is_loopback or any(address in network for network in self.networks)
