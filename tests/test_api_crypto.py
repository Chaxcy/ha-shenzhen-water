from __future__ import annotations

import json
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "custom_components" / "shenzhen_water"

custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)

shenzhen_water = types.ModuleType("custom_components.shenzhen_water")
shenzhen_water.__path__ = [str(PACKAGE)]
sys.modules.setdefault("custom_components.shenzhen_water", shenzhen_water)

aiohttp = types.ModuleType("aiohttp")
aiohttp.ClientSession = object
sys.modules.setdefault("aiohttp", aiohttp)

async_timeout = types.ModuleType("async_timeout")
async_timeout.timeout = lambda *_args, **_kwargs: None
sys.modules.setdefault("async_timeout", async_timeout)

try:
    from custom_components.shenzhen_water.api import ShenzhenWaterApi
except ModuleNotFoundError as err:
    if err.name != "Crypto":
        raise
    ShenzhenWaterApi = None


class ShenzhenWaterCryptoTest(unittest.TestCase):
    @unittest.skipIf(ShenzhenWaterApi is None, "pycryptodome is not installed")
    def test_make_key_matches_mini_program(self) -> None:
        header = "MHYBFP54PYO9YYRLYP9I15PG4I5RYULQ"

        self.assertEqual(
            ShenzhenWaterApi._make_key(header),
            "CD3AA097PYO9YYRLYP9I15PGCE92AD77",
        )

    @unittest.skipIf(ShenzhenWaterApi is None, "pycryptodome is not installed")
    def test_encrypt_and_decrypt_transposed_response(self) -> None:
        header = "49B90E90B5C3465DBDE5C5F9DA494F77"
        payload = {
            "code": 0,
            "data": [
                {
                    "costDate": 202606,
                    "customerCode": "1234567890",
                    "displayTotal": 63.31,
                }
            ],
            "message": "操作成功",
        }

        encrypted = ShenzhenWaterApi._encrypt(payload, header)
        server_body = encrypted[:7] + encrypted[-13:] + encrypted[7:-13]

        self.assertEqual(
            ShenzhenWaterApi._decrypt(json.dumps(server_body), header),
            payload,
        )


if __name__ == "__main__":
    unittest.main()
