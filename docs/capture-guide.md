# 深圳水务抓包说明

本文用于确认 Home Assistant 集成需要填写哪些字段，以及如何在 Charles 里找到它们。

## 需要填写

当前配置表单需要 3 个字段：

* 水务户号
* OpenId
* Utoken

本次抓包确认：`OpenId` 和 `Utoken` 在登录后的深圳水务请求头里可以抓到；`GUID` 没有出现在明文请求头或 URL 中，因此不再作为配置项。

## 抓包步骤

1. 打开 Charles，并确保手机或电脑微信流量已经走 Charles 代理。
2. 打开微信小程序“环水管家”。
3. 进入户号或账单页面，触发一次账单查询。
4. 在 Charles 左侧找到域名：

```text
szgk.sz-water.com.cn
```

5. 优先查看下面几个登录后的请求：

```text
/api/wechat/op/user/GetUsersV20
/api/wechat/op/BillInfo/GetLatestBillDetails2V30
/api/wechat/op/user/billInfo/BillingInfoBycustomerCodesV30
```

6. 点开请求后，在 Request Headers 里复制：

```text
OpenId
Utoken
```

注意：登录前的请求里 `OpenId` 和 `Utoken` 可能是空的。要看 `AutomaticLoginV20` 之后的请求，也就是 `GetUsersV20` 或账单接口。

## 户号在哪里

户号可以从小程序页面直接看，也可以在 Charles 里找类似请求：

```text
/api/wechat/op/Customer/checkFaceInfoNew/wxxcx/{户号}/{手机号}
```

其中 `{户号}` 就是水务户号。

如果后续能解开小程序加密响应，也可以从 `GetUsersV20` 响应里的用户列表拿户号。

## 已确认的接口

本次 HAR 确认小程序账单相关接口路径是：

```text
/api/wechat/op/BillInfo/GetLatestBillDetails2V30
/api/wechat/op/BillInfo/GetLatestBillDetailsV30
/api/wechat/op/user/billInfo/BillingInfoBycustomerCodesV30
/api/wechat/op/user/CustomerInfo/GetCustomerDetailV20
```

当前集成使用：

```text
/api/wechat/op/BillInfo/GetLatestBillDetails2V30
/api/wechat/op/user/billInfo/BillingInfoBycustomerCodesV30
```

这两个路径和抓包一致。

## 目前仍需确认

小程序 `wxxcx` 渠道的 POST 请求体和响应都是加密字符串，并且与旧网厅 `wt` 渠道的 AES 解密方式不完全一致。

也就是说：

* 接口路径确认是对的
* `OpenId`、`Utoken`、户号确认能抓到
* 小程序加密算法仍需继续适配

如果 Home Assistant 里添加集成时报连接失败，优先怀疑不是字段填错，而是小程序加密算法还没完全匹配。
