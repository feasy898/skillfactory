# WS3 对拍条目题面输入（逐字复制自 office-eval-suite oracle/suite.json，不得改动）

- id: ie-01
- domain: info-extraction（信息抽取）
- difficulty: 易

## instruction（原文）

从下列邮件正文中抽取关键信息并输出为 JSON（键用英文）。邮件：『王经理您好，我们是星辰传媒。就贵司11月8日年会场地预订事宜：我们推荐滨江国际会展中心三楼宴会厅，可容纳600人，日报价（含基础音响与LED屏）为28,000元，含服务费；如确定，请在11月1日前支付30%定金。联系人：刘小姐，电话 138-5762-1900，邮箱 liu@xingchen-media.com。』要求输出键：vendor、venue、capacity、price、deposit_ratio、deposit_deadline、contact_name、contact_phone、contact_email；缺失字段置 null；金额与日期保持原文写法。
