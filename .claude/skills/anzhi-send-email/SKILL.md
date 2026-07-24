---
name: anzhi-send-email
description: 独立邮件发送工具，QQ/企业邮箱 SMTP 直发，支持多收件人+多附件+dry-run 预演。触发词：发邮件、把文件发给、发送报告、发给XX邮箱、寄送附件。用户说"发邮件/把文件发给某人/发送报告"且给出收件人+内容（正文或附件）时使用。不用于批量群发营销邮件或需要邮件模板渲染的场景。
---

# anzhi-send-email — 独立邮件发送工具

**声明：** 我正在使用 anzhi-send-email 技能，通过 SMTP 直接发送邮件。

**职责边界：** 只做"发邮件"这一件事——组装收件人/主题/正文/附件并通过 SMTP 发出。不做邮件模板渲染、不做群发名单管理、不做收件回执追踪。

---

## 首次配置

1. 复制 `.env.example` 为同目录下的 `.env`
2. 编辑 `.env`，填写四项：
   - `MAIL_ACCOUNT`：发件邮箱地址
   - `MAIL_AUTH_CODE`：邮箱**授权码**（不是登录密码，见下方常见错误表）
   - `MAIL_SMTP_SERVER`：SMTP 服务器地址，默认 `smtp.qq.com`
   - `MAIL_SMTP_PORT`：SMTP 端口，默认 `465`
3. `.env` 已被 `.gitignore` 排除，不会被提交
4. （可选）复制 `contacts.example.md` 为 `contacts.md`，记录常用收件人地址，仅供人工速查，不参与脚本逻辑

---

## 用法

### 冒烟测试（不真正发送）

```
py -3.11 scripts/send_email.py --to test@example.com --subject "测试主题" --body "测试正文" --dry-run
```

预期输出形如：`[dry-run] to=['test@example.com'] subject=测试主题 attach=[] body_len=4`

### 真实发送

单收件人、纯文本正文：

```
py -3.11 scripts/send_email.py --to zhangsan@example.com --subject "月度报告" --body "报告已完成，详见附件。"
```

多收件人 + 正文来自文件 + 多个附件（路径含空格需加引号）：

```
py -3.11 scripts/send_email.py --to a@example.com --to b@example.com --subject "月度报告" --body-file report.txt --attach "月度报告.docx" --attach "附表 1.xlsx"
```

---

## 常见错误表

| 现象 | 原因 | 处理 |
|------|------|------|
| 登录失败 / 认证失败 | 把邮箱登录密码填进了 `MAIL_AUTH_CODE` | 登录密码不能用于 SMTP，需到邮箱设置里的「账户 - 开启SMTP服务」生成专用授权码 |
| 连接超时 / SSL 握手失败 | 端口填成了 587（STARTTLS 端口） | 本工具固定走 SSL，端口必须是 465，不支持 587/STARTTLS |
| 附件找不到 / 命令解析异常 | 附件路径含空格但没加引号 | `--attach "月度报告 v2.docx"` 整体加双引号 |
| 企业邮箱始终登录失败 | 企业邮箱默认关闭第三方客户端登录 | 需联系企业邮箱管理员开启「客户端授权登录」或 SMTP 服务后重试 |
| 报错"缺少正文" | 既没给 `--body` 也没给 `--body-file` | 二选一必填其一 |
| 报错"缺少 MAIL_ACCOUNT / MAIL_AUTH_CODE" | 未配置 `.env` 或配置项拼写有误 | 检查 `.env` 是否存在、四个变量名是否与 `.env.example` 完全一致 |
