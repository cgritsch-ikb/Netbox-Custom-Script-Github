import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]


def device(identifier, name, vendor="Cisco", primary=None, tags=None):
    return {
        "id": identifier,
        "name": name,
        "tags": tags or [],
        "device_type": {"manufacturer": {"name": vendor}},
        "platform": None,
        "site": {"name": "Test"},
        "role": {"name": "CPE-GIN"},
        "primary_ip4": primary,
    }


def interface(identifier, name, enabled=True, tags=None):
    return {
        "id": identifier,
        "name": name,
        "tags": tags or [],
        "description": "Test interface",
        "enabled": enabled,
    }


def address(cidr, family, name):
    return {
        "address": cidr,
        "family": {"value": family},
        "assigned_object_type": "dcim.interface",
        "assigned_object": {"name": name},
    }


@unittest.skipUnless(shutil.which("ansible-playbook"), "Ansible is required")
class ConfigGenerationTests(unittest.TestCase):
    def setUp(self):
        self.devices = [
            device(
                1, "router-01",
                tags=[{"name": "Core Network", "slug": "core-network"}],
            ),
            device(2, "router-empty", primary={"address": "192.0.2.9/24"}),
            device(3, "router-v6"),
            device(4, "huawei-01", "Huawei"),
        ]
        self.interfaces = {
            1: [
                interface(
                    11, "GigabitEthernet0/0",
                    tags=[{"name": "Uplink", "slug": "uplink"}],
                ),
                interface(12, "GigabitEthernet0/1", False),
            ],
            2: [],
            3: [interface(31, "Loopback1")],
        }
        self.addresses = {
            1: [
                address("192.0.2.1/24", 4, "GigabitEthernet0/0"),
                address("192.0.2.2/24", 4, "GigabitEthernet0/0"),
                address("2001:db8::1/64", 6, "GigabitEthernet0/0"),
                address("fe80::1/64", 6, "GigabitEthernet0/0"),
            ],
            2: [],
            3: [address("2001:db8::3/128", 6, "Loopback1")],
        }
        self.calls = []
        test = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                parsed = urlparse(self.path)
                query = parse_qs(parsed.query)
                test.calls.append((parsed.path, query))
                if self.headers.get("Authorization") != "Token test-only-token":
                    self.send_error(403)
                    return
                if parsed.path == "/api/dcim/devices/":
                    if query.get("role") != ["cpe-gin"]:
                        self.send_error(400)
                        return
                    data = test.devices
                elif parsed.path == "/api/dcim/interfaces/":
                    data = test.interfaces[int(query["device_id"][0])]
                elif parsed.path == "/api/ipam/ip-addresses/":
                    data = test.addresses[int(query["device_id"][0])]
                else:
                    self.send_error(404)
                    return
                offset = int(query["offset"][0])
                # Deliberately cap pages below the requested limit.
                payload = json.dumps({
                    "count": len(data),
                    "results": data[offset:offset + 1],
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(payload)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.url = f"http://127.0.0.1:{server.server_port}"
        output = tempfile.TemporaryDirectory()
        self.addCleanup(output.cleanup)
        self.output = Path(output.name)

    def generate(self, token="test-only-token"):
        return subprocess.run(
            [
                "ansible-playbook", "-i", "localhost,",
                str(ROOT / "ansible/playbooks/generate_cpe_gin_config.yml"),
                "-e", json.dumps({"config_output_dir": str(self.output)}),
            ],
            cwd=ROOT / "ansible",
            env=dict(
                os.environ, NETBOX_API=self.url, NETBOX_TOKEN=token,
                ANSIBLE_NOCOLOR="1",
            ),
            capture_output=True, text=True, timeout=120,
        )

    def test_paginated_generation(self):
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        config = (self.output / "router-01.cfg").read_text()
        self.assertIn("ip address 192.0.2.1 255.255.255.0\n", config)
        self.assertIn("ip address 192.0.2.2 255.255.255.0 secondary", config)
        self.assertIn("ipv6 address 2001:db8::1/64", config)
        self.assertIn("ipv6 address fe80::1 link-local", config)
        self.assertNotIn("ipv6 address fe80::1/64", config)
        self.assertIn("ipv6 unicast-routing", config)
        self.assertIn("! Device tags: core-network", config)
        self.assertIn(" ! Tags: uplink", config)
        self.assertIn(
            "interface GigabitEthernet0/1\n description Test interface\n shutdown",
            config,
        )
        self.assertNotIn("interface Loopback0", config)
        empty = (self.output / "router-empty.cfg").read_text()
        self.assertNotIn("interface Loopback0", empty)
        ipv6 = (self.output / "router-v6.cfg").read_text()
        self.assertIn("ipv6 address 2001:db8::3/128", ipv6)
        self.assertNotIn("ip address 2001:", ipv6)
        self.assertFalse((self.output / "huawei-01.cfg").exists())
        self.assertEqual((self.output / "router-01.cfg").stat().st_mode & 0o777, 0o600)
        self.assertEqual(len(self.calls), 14)
        self.assertNotIn("status", self.calls[0][1])
        self.assertNotIn("has_primary_ip", self.calls[0][1])

    def test_empty_device_query(self):
        self.devices.clear()
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(list(self.output.iterdir()), [])
        self.assertEqual(len(self.calls), 1)

    def test_api_failure_does_not_render_configs(self):
        result = self.generate(token="invalid-test-token")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.output.iterdir()), [])
        self.assertNotIn("invalid-test-token", result.stdout + result.stderr)

    def test_unsafe_device_name_is_rejected(self):
        self.devices = [device(1, "../unsafe")]
        result = self.generate()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.output.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
