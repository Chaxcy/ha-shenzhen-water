from __future__ import annotations

import base64
import json
import re
import secrets
import string
from typing import Any

from aiohttp import ClientSession
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from .const import (
    API_URL_BILL_INFO,
    API_URL_CUS_GENERATE_CTOKEN,
    API_URL_GET_LATEST_BILL,
    API_URL_GET_USERS,
    API_URL_LOGIN,
    API_URL_SEND_SMS_CODE,
    DEFAULT_CHANNEL,
)


def generate_header_value(length: int = 32) -> str:
    """Generate random 04A52C9F request header value."""
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


class ShenzhenWaterApiError(Exception):
    """Shenzhen Water API error."""

class ShenzhenWaterAuthExpiredError(ShenzhenWaterApiError):
    """Shenzhen Water login token expired."""

class ShenzhenWaterApi:
    """Shenzhen Water API client."""

    def __init__(
        self,
        session: ClientSession,
        tenant_id: str,
        openid: str = "",
        guid: str = "",
        customer_code: str = "",
        bill_month: int = 0,
        utoken: str = "",
        app_user_id: str = "",
        ctoken: str = "",
    ) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._openid = openid
        self._guid = guid
        self._customer_code = customer_code
        self._bill_month = bill_month
        self._utoken = utoken
        self._app_user_id = app_user_id
        self._ctoken = ctoken

    @staticmethod
    def make_key(header_value: str) -> str:
        """Generate AES key from 04A52C9F header value."""
        if not header_value or len(header_value) < 24:
            raise ShenzhenWaterApiError(
                f"Invalid 04A52C9F header value: {header_value}"
            )

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

        if len(raw) % 16 != 0:
            raise ShenzhenWaterApiError(
                f"Invalid AES payload length: {len(raw)}, not aligned to 16 bytes"
            )

        cipher = AES.new(key.encode("utf-8"), AES.MODE_ECB)
        plain = unpad(cipher.decrypt(raw), AES.block_size)
        return plain.decode("utf-8")

    @classmethod
    def decrypt_response(
        cls,
        resp_text: str,
        response_header_value: str,
    ) -> dict[str, Any]:
        """Decrypt Shenzhen Water encrypted response."""
        try:
            t = json.loads(resp_text)
        except Exception:
            t = resp_text.strip().strip('"')

        if not isinstance(t, str):
            raise ShenzhenWaterApiError("Encrypted response is not a string")

        t = re.sub(r"\s+", "", t)

        if len(t) <= 20:
            raise ShenzhenWaterApiError(
                f"Invalid encrypted response length: {len(t)}"
            )

        s = t[:7]
        n = t[7:20]
        cipher_text = s + t[20:] + n

        response_key = cls.make_key(response_header_value)
        plain = cls.decrypt_aes_ecb_raw(cipher_text, response_key)

        try:
            return json.loads(plain)
        except json.JSONDecodeError as err:
            raise ShenzhenWaterApiError(f"Invalid decrypted JSON: {plain}") from err

    def _build_common_headers(
        self,
        request_header_value: str,
        *,
        openid: str | None = None,
        utoken: str | None = None,
        ctoken: str | None = None,
    ) -> dict[str, str]:
        """Build common Shenzhen Water request headers."""
        headers = {
            "04A52C9F": request_header_value,
            "Accept": "application/json, text/plain, */*",
            "Channel": DEFAULT_CHANNEL,
            "Content-Type": "application/json;charset=UTF-8",
            "OpenId": openid if openid is not None else self._openid,
            "Origin": "https://www.82137777.com",
            "Referer": "https://www.82137777.com/",
            "TenantId": self._tenant_id,
            "User-Agent": "Mozilla/5.0",
        }

        final_utoken = utoken if utoken is not None else self._utoken
        final_ctoken = ctoken if ctoken is not None else self._ctoken

        if final_utoken:
            headers["Utoken"] = final_utoken

        if final_ctoken:
            headers["Ctoken"] = final_ctoken

        return headers

    async def _async_post_encrypted(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        openid: str | None = None,
        utoken: str | None = None,
        ctoken: str | None = None,
    ) -> dict[str, Any]:
        """POST encrypted payload and decrypt encrypted response."""
        request_header_value = generate_header_value()
        request_key = self.make_key(request_header_value)

        encrypted_payload = self.encrypt_aes_ecb(payload, request_key)

        headers = self._build_common_headers(
            request_header_value,
            openid=openid,
            utoken=utoken,
            ctoken=ctoken,
        )

        async with self._session.post(
            url,
            headers=headers,
            data=encrypted_payload,
            timeout=15,
        ) as resp:
            text = await resp.text()

            if resp.status != 200:
                raise ShenzhenWaterApiError(
                    f"HTTP {resp.status}: url={url}, response={text}"
                )

            response_header_value = resp.headers.get("04A52C9F")
            if not response_header_value:
                raise ShenzhenWaterApiError(
                    f"Response header 04A52C9F not found: url={url}, response={text}"
                )

            data = self.decrypt_response(text, response_header_value)

            api_code = data.get("code")
            if api_code not in (0, "0"):
                error_message = (
                    "API error, "
                    f"url={url}, "
                    f"code={api_code}, "
                    f"message={data.get('message')}, "
                    f"msg={data.get('msg')}, "
                    f"response={json.dumps(data, ensure_ascii=False)}"
                )

                if self._is_utoken_error_message(error_message):
                    raise ShenzhenWaterAuthExpiredError(
                        "深圳水务登录已失效，请删除该集成配置项后重新添加，"
                        f"重新获取短信验证码登录。原始错误：{error_message}"
                    )

                raise ShenzhenWaterApiError(error_message)

            return data

    @staticmethod
    def _is_ctoken_error(err: Exception) -> bool:
        """Return true if the API error looks like a Ctoken problem."""
        message = str(err).lower()

        return any(
            keyword.lower() in message
            for keyword in (
                "ctoken",
                "9999902",
                "请求头ctoken",
                "ctoken参数缺失",
                "ctoken信息不合法",
            )
        )

    @staticmethod
    def _is_utoken_error_message(message: str) -> bool:
        """Return true if the API error looks like an expired or invalid Utoken."""
        lowered = message.lower()

        # Ctoken errors should be handled by Ctoken retry, not treated as login expired.
        if "ctoken" in lowered:
            return False

        return any(
            keyword.lower() in lowered
            for keyword in (
                "9999904",
                "utoken",
                "请求头token信息不合法",
                "token信息不合法",
                "token不合法",
                "登录失效",
                "未登录",
            )
        )

    async def _async_post_with_ctoken_retry(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        customer_code: str,
    ) -> dict[str, Any]:
        """POST with Ctoken and retry once if Ctoken is missing, invalid, or expired."""
        if not customer_code:
            raise ShenzhenWaterApiError("customer_code is required")

        if not self._ctoken:
            await self.async_generate_ctoken(customer_code)

        try:
            return await self._async_post_encrypted(
                url,
                payload,
                openid=self._openid,
                utoken=self._utoken,
                ctoken=self._ctoken,
            )

        except ShenzhenWaterApiError as err:
            if not self._is_ctoken_error(err):
                raise

            self._ctoken = ""
            await self.async_generate_ctoken(customer_code)

            return await self._async_post_encrypted(
                url,
                payload,
                openid=self._openid,
                utoken=self._utoken,
                ctoken=self._ctoken,
            )

    async def async_send_sms_code(
        self,
        mobile: str,
        ctoken: str | None = None,
        old_utoken: str | None = None,
    ) -> dict[str, Any]:
        """Send SMS validation code."""
        payload = {
            "validationType": 4,
            "mobile": mobile,
            "customerType": "login",
            "channel": DEFAULT_CHANNEL,
        }

        return await self._async_post_encrypted(
            API_URL_SEND_SMS_CODE,
            payload,
            openid="",
            utoken=old_utoken or "",
            ctoken=ctoken or "",
        )

    async def async_login_v20(
        self,
        mobile: str,
        sms_code: str,
        ctoken: str | None = None,
        old_utoken: str | None = None,
    ) -> dict[str, Any]:
        """Login with mobile SMS code."""
        payload = {
            "mobile": mobile,
            "validationNum": sms_code,
            "validationType": 4,
            "openid": mobile,
            "channel": DEFAULT_CHANNEL,
        }

        return await self._async_post_encrypted(
            API_URL_LOGIN,
            payload,
            openid="",
            utoken=old_utoken or "",
            ctoken=ctoken or "",
        )

    async def async_get_users_v20(self) -> dict[str, Any]:
        """Fetch bound water customer list."""
        if not self._openid:
            raise ShenzhenWaterApiError("openid is required")

        if not self._guid:
            raise ShenzhenWaterApiError("guid is required")

        if not self._utoken:
            raise ShenzhenWaterApiError("utoken is required")

        payload = {
            "status": 1,
            "channel": DEFAULT_CHANNEL,
            "openid": self._openid,
            "guid": self._guid,
        }

        return await self._async_post_encrypted(
            API_URL_GET_USERS,
            payload,
            openid=self._openid,
            utoken=self._utoken,
            ctoken="",
        )

    async def async_generate_ctoken(
        self,
        customer_code: str | None = None,
    ) -> str:
        """Generate Ctoken for a customer code."""
        target_customer_code = customer_code or self._customer_code

        if not target_customer_code:
            raise ShenzhenWaterApiError("customer_code is required")

        if not self._openid:
            raise ShenzhenWaterApiError("openid is required")

        if not self._utoken:
            raise ShenzhenWaterApiError("utoken is required")

        payload = {
            "customercode": target_customer_code,
            "channel": DEFAULT_CHANNEL,
            "openid": self._openid,
        }

        data = await self._async_post_encrypted(
            API_URL_CUS_GENERATE_CTOKEN,
            payload,
            openid=self._openid,
            utoken=self._utoken,
            ctoken="",
        )

        token = ((data.get("data") or {}).get("token")) or ""

        if not token:
            raise ShenzhenWaterApiError(
                f"Ctoken not found in response: {json.dumps(data, ensure_ascii=False)}"
            )

        self._ctoken = token
        return token

    async def async_get_latest_bill_details(
        self,
        customer_code: str | None = None,
    ) -> dict[str, Any]:
        """Fetch latest bill details."""
        if not self._openid:
            raise ShenzhenWaterApiError("openid is required")

        if not self._guid:
            raise ShenzhenWaterApiError("guid is required")

        if not self._utoken:
            raise ShenzhenWaterApiError("utoken is required")

        target_customer_code = customer_code or self._customer_code
        if not target_customer_code:
            raise ShenzhenWaterApiError("customer_code is required")

        payload = {
            "customerType": "details",
            "customercodelist": [target_customer_code],
            "channel": DEFAULT_CHANNEL,
            "openid": self._openid,
            "guid": self._guid,
        }

        return await self._async_post_with_ctoken_retry(
            API_URL_GET_LATEST_BILL,
            payload,
            customer_code=target_customer_code,
        )

    def _build_bill_payload(self, bill_month: int | None = None) -> dict[str, Any]:
        """Build encrypted bill request payload."""
        if not self._customer_code:
            raise ShenzhenWaterApiError("customer_code is required")

        if not self._openid:
            raise ShenzhenWaterApiError("openid is required")

        if not self._guid:
            raise ShenzhenWaterApiError("guid is required")

        target_bill_month = bill_month or self._bill_month
        if not target_bill_month:
            raise ShenzhenWaterApiError("bill_month is required")

        return {
            "customerCodes": [
                {
                    "customercode": self._customer_code,
                    "billmonth": int(target_bill_month),
                }
            ],
            "channel": DEFAULT_CHANNEL,
            "openid": self._openid,
            "guid": self._guid,
        }

    async def async_get_bill_info(
        self,
        bill_month: int | None = None,
    ) -> dict[str, Any]:
        """Fetch bill info."""
        if not self._utoken:
            raise ShenzhenWaterApiError("utoken is required")

        payload = self._build_bill_payload(bill_month)

        return await self._async_post_with_ctoken_retry(
            API_URL_BILL_INFO,
            payload,
            customer_code=self._customer_code,
        )