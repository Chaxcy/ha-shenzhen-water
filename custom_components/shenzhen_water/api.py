from __future__ import annotations

import base64
from datetime import datetime
import json
import re
import secrets
import string
from typing import Any

import aiohttp
import async_timeout
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from .const import DEFAULT_CHANNEL, DEFAULT_TENANT_ID

REQUEST_KEY_PREFIX = "CD3AA097"
REQUEST_KEY_SUFFIX = "CE92AD77"


class ShenzhenWaterApiError(Exception):
    """Shenzhen Water API error."""


class ShenzhenWaterAuthError(ShenzhenWaterApiError):
    """Shenzhen Water auth error."""


class ShenzhenWaterApi:
    """Client for Shenzhen Water mini-program API."""

    BASE_URL = "https://szgk.sz-water.com.cn"

    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        customer_code: str,
        openid: str,
        tenant_id: str = DEFAULT_TENANT_ID,
        channel: str = DEFAULT_CHANNEL,
    ) -> None:
        self._session = session
        self._customer_code = customer_code
        self._openid = openid
        self._guid = ""
        self._utoken = ""
        self._tenant_id = tenant_id
        self._channel = channel
        self._logged_in = False

    @property
    def customer_code(self) -> str:
        """Return water customer code."""
        return self._customer_code

    @staticmethod
    def _random_header_value(length: int = 32) -> str:
        chars = string.digits + string.ascii_uppercase[:25]
        return "".join(secrets.choice(chars) for _ in range(length))

    @staticmethod
    def _make_key(header_value: str) -> str:
        if not header_value or len(header_value) < 24:
            raise ShenzhenWaterApiError(
                f"Invalid 04A52C9F header value: {header_value}"
            )

        return REQUEST_KEY_PREFIX + header_value[8:24] + REQUEST_KEY_SUFFIX

    @classmethod
    def _encrypt(cls, payload: dict[str, Any], header_value: str) -> str:
        key = cls._make_key(header_value)
        plain = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        cipher = AES.new(key.encode("utf-8"), AES.MODE_ECB)
        encrypted = cipher.encrypt(pad(plain.encode("utf-8"), AES.block_size))
        return base64.b64encode(encrypted).decode("utf-8")

    @classmethod
    def _decrypt(cls, text: str, header_value: str) -> dict[str, Any]:
        try:
            body = json.loads(text)
        except Exception:
            body = text.strip().strip('"')

        if not isinstance(body, str):
            raise ShenzhenWaterApiError("Encrypted response is not a string")

        body = re.sub(r"\s+", "", body)
        if len(body) <= 20:
            raise ShenzhenWaterApiError(f"Invalid encrypted response: {body}")

        cipher_text = body[:7] + body[20:] + body[7:20]
        cipher_text += "=" * (-len(cipher_text) % 4)
        raw = base64.b64decode(cipher_text)

        if len(raw) % AES.block_size != 0:
            raise ShenzhenWaterApiError(
                f"Invalid AES payload length: {len(raw)}"
            )

        key = cls._make_key(header_value)
        cipher = AES.new(key.encode("utf-8"), AES.MODE_ECB)
        plain = unpad(cipher.decrypt(raw), AES.block_size).decode("utf-8")

        try:
            return json.loads(plain)
        except json.JSONDecodeError as err:
            raise ShenzhenWaterApiError(f"Invalid decrypted JSON: {plain}") from err

    def _build_headers(
        self, header_value: str, *, include_token: bool = True
    ) -> dict[str, str]:
        return {
            "04A52C9F": header_value,
            "Accept": "*/*",
            "Channel": self._channel,
            "Content-Type": "application/json",
            "OpenId": self._openid,
            "Referer": "https://servicewechat.com/wx987545bf02573f61/198/page-frame.html",
            "TenantId": self._tenant_id,
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 MiniProgramEnv/Mac "
                "MicroMessenger/7.0.20"
            ),
            "Utoken": self._utoken if include_token else "",
            "xweb_xhr": "1",
        }

    @staticmethod
    def _looks_like_auth_error(message: str) -> bool:
        lowered = message.lower()
        return any(
            keyword in lowered
            for keyword in (
                "utoken",
                "unauthorized",
                "token信息不合法",
                "token不合法",
                "登录失效",
                "未登录",
                "请登录",
                "9999904",
            )
        )

    async def _request(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        include_token: bool = True,
    ) -> dict[str, Any]:
        """Send encrypted request to Shenzhen Water mini-program API."""
        url = f"{self.BASE_URL}{path}"
        header_value = self._random_header_value()
        encrypted_payload = self._encrypt(payload, header_value)

        try:
            async with async_timeout.timeout(20):
                async with self._session.post(
                    url,
                    headers=self._build_headers(
                        header_value, include_token=include_token
                    ),
                    data=json.dumps(encrypted_payload),
                ) as resp:
                    text = await resp.text()

                    if resp.status != 200:
                        message = f"HTTP {resp.status}: {text[:300]}"
                        if self._looks_like_auth_error(message):
                            raise ShenzhenWaterAuthError(message)
                        raise ShenzhenWaterApiError(message)

                    response_header = resp.headers.get("04A52C9F")
                    if not response_header:
                        raise ShenzhenWaterApiError(
                            f"Response header 04A52C9F not found: {text[:300]}"
                        )

                    data = self._decrypt(text, response_header)

        except ShenzhenWaterApiError:
            raise
        except Exception as err:
            raise ShenzhenWaterApiError(f"Request failed: {err}") from err

        if data.get("code") not in (0, "0"):
            message = json.dumps(data, ensure_ascii=False)
            if self._looks_like_auth_error(message):
                raise ShenzhenWaterAuthError(message)
            raise ShenzhenWaterApiError(f"API error: {message}")

        return data

    async def async_login(self) -> dict[str, Any]:
        """Refresh mini-program token and GUID from OpenId."""
        data = await self._request(
            "/api/wechat/op/user/AutomaticLoginV20",
            {
                "openid": self._openid,
                "channel": self._channel,
            },
            include_token=False,
        )
        login_data = data.get("data") or {}
        token = login_data.get("token")
        guid = login_data.get("guid")

        if not token or not guid:
            raise ShenzhenWaterAuthError(
                f"Automatic login did not return token and guid: {data}"
            )

        self._utoken = str(token)
        self._guid = str(guid)
        self._logged_in = True
        return data

    async def _ensure_login(self) -> None:
        if not self._logged_in:
            await self.async_login()

    def _base_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "channel": self._channel,
            "openid": self._openid,
            "guid": self._guid,
        }

        if self._guid in ("", None):
            payload.pop("guid")

        return payload

    async def async_get_users(self) -> dict[str, Any]:
        """Get bound water users."""
        await self._ensure_login()
        return await self._request(
            "/api/wechat/op/user/GetUsersV20",
            {
                **self._base_payload(),
                "status": 0,
            },
        )

    async def async_get_latest_bill_details(self) -> dict[str, Any]:
        """Get latest bill details."""
        await self._ensure_login()
        return await self._request(
            "/api/wechat/op/BillInfo/GetLatestBillDetails2V30",
            {
                **self._base_payload(),
                "customerType": "details",
                "customercodelist": [self._customer_code],
                "isLimitRequest": "1",
            },
        )

    async def async_get_bill_info(self, bill_month: int | None = None) -> dict[str, Any]:
        """Get bill info from the mini-program bill endpoint."""
        await self._ensure_login()
        payload = {
            **self._base_payload(),
            "customerCodes": [self._customer_code],
        }
        if bill_month:
            payload["costdate"] = int(bill_month)

        return await self._request(
            "/api/wechat/op/user/billInfo/BillingInfoBycustomerCodesV30",
            payload,
        )

    async def async_get_all(self) -> dict[str, Any]:
        """Get all Shenzhen Water data."""
        try:
            current = await self.async_get_latest_bill_details()
        except ShenzhenWaterAuthError:
            self._logged_in = False
            await self.async_login()
            current = await self.async_get_latest_bill_details()

        current_rows = current.get("data") or []
        current_month = current_rows[0].get("costDate") if current_rows else None

        current_bill_info = {}
        try:
            current_bill_info = await self.async_get_bill_info(current_month)
        except ShenzhenWaterAuthError:
            raise
        except ShenzhenWaterApiError:
            current_bill_info = {}

        previous = {}
        bill_info_rows = current_bill_info.get("data") or []
        previous_month = None
        if bill_info_rows:
            current_month = bill_info_rows[0].get("costDate") or current_month
        if current_month:
            month = datetime.strptime(str(current_month), "%Y%m")
            year = month.year - 1 if month.month == 1 else month.year
            previous = 12 if month.month == 1 else month.month - 1
            previous_month = year * 100 + previous

        if previous_month:
            try:
                previous = await self.async_get_bill_info(previous_month)
            except ShenzhenWaterAuthError:
                raise
            except ShenzhenWaterApiError:
                previous = {}

        return {
            "current": current,
            "current_bill_info": current_bill_info,
            "previous": previous,
        }
