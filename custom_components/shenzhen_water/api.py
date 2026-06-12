from __future__ import annotations

import base64
import json
import re
from typing import Any

from aiohttp import ClientSession
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from .const import API_URL_BILL_INFO, DEFAULT_CHANNEL


class ShenzhenWaterApiError(Exception):
    """Shenzhen Water API error."""


class ShenzhenWaterApi:
    """Shenzhen Water API client."""

    def __init__(
        self,
        session: ClientSession,
        openid: str,
        guid: str,
        customer_code: str,
        bill_month: int,
        tenant_id: str,
        utoken: str,
        request_header_value: str,
    ) -> None:
        self._session = session
        self._openid = openid
        self._guid = guid
        self._customer_code = customer_code
        self._bill_month = bill_month
        self._tenant_id = tenant_id
        self._utoken = utoken
        self._request_header_value = request_header_value

    @staticmethod
    def make_key(header_value: str) -> str:
        """Generate AES key from 04A52C9F header value."""
        if not header_value or len(header_value) < 24:
            raise ShenzhenWaterApiError(f"Invalid 04A52C9F header value: {header_value}")

        return "33F4A3D6" + header_value[8:24] + "A9E19798"

    @staticmethod
    def encrypt_aes_ecb(data: Any, key: str) -> str:
        """Encrypt request body with AES-ECB-PKCS7."""
        if not isinstance(data, str):
            data = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

        cipher = AES.new(key.encode("utf-8"), AES.MODE_ECB)
        encrypted = cipher.encrypt(pad(data.encode("utf-8"), AES.block_size))
        return base64.b64encode(encrypted).decode("utf-8")

    @staticmethod
    def decrypt_aes_ecb_raw(cipher_text: str, key: str) -> str:
        """Decrypt AES-ECB-PKCS7 base64 cipher text."""
        cipher_text = cipher_text.strip()
        cipher_text += "=" * (-len(cipher_text) % 4)

        raw = base64.b64decode(cipher_text)

        cipher = AES.new(key.encode("utf-8"), AES.MODE_ECB)
        plain = unpad(cipher.decrypt(raw), AES.block_size)
        return plain.decode("utf-8")

    @classmethod
    def decrypt_response(cls, resp_text: str, response_header_value: str) -> dict[str, Any]:
        """
        Decrypt Shenzhen Water response.

        Frontend logic:
            var t = e.data
            var s = t.slice(0, 7)
            var n = t.slice(7, 20)
            var o = Hg(
                s + t.substring(20) + n,
                "33F4A3D6" + e.headers["04a52c9f"].substr(8, 16) + "A9E19798"
            )
        """
        try:
            t = json.loads(resp_text)
        except Exception:
            t = resp_text.strip().strip('"')

        t = re.sub(r"\s+", "", t)

        s = t[:7]
        n = t[7:20]
        cipher_text = s + t[20:] + n

        response_key = cls.make_key(response_header_value)
        plain = cls.decrypt_aes_ecb_raw(cipher_text, response_key)
        return json.loads(plain)

    def _build_payload(self) -> dict[str, Any]:
        return {
            "customerCodes": [
                {
                    "customercode": self._customer_code,
                    "billmonth": self._bill_month,
                }
            ],
            "channel": DEFAULT_CHANNEL,
            "openid": self._openid,
            "guid": self._guid,
        }

    def _build_headers(self) -> dict[str, str]:
        return {
            "04A52C9F": self._request_header_value,
            "Accept": "application/json, text/plain, */*",
            "Channel": DEFAULT_CHANNEL,
            "Content-Type": "application/json;charset=UTF-8",
            "OpenId": self._openid,
            "Origin": "https://www.82137777.com",
            "Referer": "https://www.82137777.com/",
            "TenantId": self._tenant_id,
            "Utoken": self._utoken,
            "User-Agent": "Mozilla/5.0",
        }

    async def async_get_bill_info(self) -> dict[str, Any]:
        """Fetch bill info."""
        request_key = self.make_key(self._request_header_value)
        encrypted_payload = self.encrypt_aes_ecb(self._build_payload(), request_key)

        async with self._session.post(
            API_URL_BILL_INFO,
            headers=self._build_headers(),
            data=encrypted_payload,
            timeout=15,
        ) as resp:
            text = await resp.text()

            if resp.status != 200:
                raise ShenzhenWaterApiError(f"HTTP {resp.status}: {text}")

            response_header_value = resp.headers.get("04A52C9F")
            if not response_header_value:
                raise ShenzhenWaterApiError("Response header 04A52C9F not found")

            data = self.decrypt_response(text, response_header_value)

            if data.get("code") != 0:
                raise ShenzhenWaterApiError(data.get("message", "Unknown API error"))

            return data