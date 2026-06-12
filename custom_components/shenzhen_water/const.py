DOMAIN = "shenzhen_water"

DEFAULT_CHANNEL = "wt"
DEFAULT_TENANT_ID = "18a85453-ee3f-4cda-b3bf-7f6421319dcc"

API_URL_LOGIN = "https://szgk.sz-water.com.cn/api/wechat/op/user/LoginV20"
API_URL_SEND_SMS_CODE = "https://szgk.sz-water.com.cn/api/wechat/op/user/GenerateValidationNumV20"
API_URL_GET_USERS = "https://szgk.sz-water.com.cn/api/wechat/op/user/GetUsersV20"

API_URL_CUS_GENERATE_CTOKEN = (
    "https://szgk.sz-water.com.cn/api/wechat/op/CustomerInfo/"
    "generaterCtoken"
)

API_URL_GET_LATEST_BILL = (
    "https://szgk.sz-water.com.cn/api/wechat/op/BillInfo/"
    "GetLatestBillDetails2V30"
)

API_URL_BILL_INFO = (
    "https://szgk.sz-water.com.cn/api/wechat/op/user/billInfo/"
    "BillingInfoBycustomerCodesAndMonthsV20"
)

CONF_MOBILE = "mobile"
CONF_OPENID = "openid"
CONF_GUID = "guid"
CONF_CUSTOMER_CODE = "customer_code"
CONF_BILL_MONTH = "bill_month"
CONF_TENANT_ID = "tenant_id"
CONF_UTOKEN = "utoken"
CONF_APP_USER_ID = "app_user_id"
CONF_CTOKEN = "ctoken"

CONF_UPDATE_INTERVAL_MINUTES = "update_interval_minutes"
DEFAULT_UPDATE_INTERVAL_MINUTES = 360
MIN_UPDATE_INTERVAL_MINUTES = 10
MAX_UPDATE_INTERVAL_MINUTES = 10080