import asyncio
import logging
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts' / 'windows'))

from mqtt_auth import LocalHardwareAuth
from mqtt_broker import local_networks
from unittest.mock import patch


class LocalAuthTests(unittest.TestCase):
    def allowed(self, address, username=None, password=None, networks=None):
        context = SimpleNamespace(
            logger=logging.getLogger(__name__),
            config=LocalHardwareAuth.Config(allowed_networks=networks or []),
        )
        plugin = LocalHardwareAuth(context)
        session = SimpleNamespace(remote_address=address, username=username, password=password)
        return asyncio.run(plugin.authenticate(session=session))

    def test_lan_accepts_any_or_empty_credentials(self):
        for username, password in [(None, None), ('arbitrary', 'wrong-password'), ('', '')]:
            with self.subTest(username=username):
                self.assertTrue(self.allowed('172.168.1.61', username, password, ['172.168.1.156/24']))

    def test_loopback_accepts_credentials_without_lan(self):
        for address in ['127.0.0.1', '::1']:
            self.assertTrue(self.allowed(address, 'anything', 'anything'))

    def test_other_networks_and_invalid_addresses_denied(self):
        for address in ['172.168.2.61', '8.8.8.8', '192.168.1.10', 'invalid', None]:
            self.assertFalse(self.allowed(address, networks=['172.168.1.156/24']))

    def test_missing_session_denied(self):
        plugin = LocalHardwareAuth(SimpleNamespace(logger=logging.getLogger(__name__), config=LocalHardwareAuth.Config()))
        self.assertFalse(asyncio.run(plugin.authenticate(session=None)))

    def test_network_discovery_normalizes_powershell_json(self):
        for value, expected in [('', []), ('"172.168.1.156/24"', ['172.168.1.156/24']), ('["10.0.0.1/24"]', ['10.0.0.1/24'])]:
            with patch('mqtt_broker.subprocess.run', return_value=SimpleNamespace(stdout=value)):
                self.assertEqual(local_networks(), expected)
