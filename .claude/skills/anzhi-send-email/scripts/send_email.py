#!/usr/bin/env python3
"""独立邮件发送工具。用法：
py -3.11 send_email.py --to a@b.com [--to c@d.com] --subject "主题" (--body "正文" | --body-file 路径) [--attach 文件]... [--dry-run]
凭据读取同目录向上查找的 .env：MAIL_ACCOUNT / MAIL_AUTH_CODE / MAIL_SMTP_SERVER(默认 smtp.qq.com) / MAIL_SMTP_PORT(默认465)"""
import argparse, mimetypes, os, smtplib, sys
from email.message import EmailMessage
from pathlib import Path

def load_env():
    p = Path(__file__).resolve()
    for d in [p.parent, *p.parents]:
        f = d / ".env"
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", action="append", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--body"); ap.add_argument("--body-file")
    ap.add_argument("--attach", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.body is None and a.body_file is None:
        sys.exit("缺少正文：请提供 --body 或 --body-file 二者之一")
    body = a.body if a.body is not None else Path(a.body_file).read_text(encoding="utf-8")
    if a.dry_run:
        print(f"[dry-run] to={a.to} subject={a.subject} attach={a.attach} body_len={len(body)}"); return
    load_env()
    acct, code = os.getenv("MAIL_ACCOUNT"), os.getenv("MAIL_AUTH_CODE")
    if not (acct and code): sys.exit("缺少 MAIL_ACCOUNT / MAIL_AUTH_CODE（复制 .env.example 为 .env 并填写）")
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = acct, ", ".join(a.to), a.subject
    msg.set_content(body)
    for att in a.attach:
        p = Path(att); ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)
        msg.add_attachment(p.read_bytes(), maintype=maintype, subtype=subtype, filename=p.name)
    with smtplib.SMTP_SSL(os.getenv("MAIL_SMTP_SERVER", "smtp.qq.com"), int(os.getenv("MAIL_SMTP_PORT", "465"))) as s:
        s.login(acct, code); s.send_message(msg)
    print("已发送")

if __name__ == "__main__": main()
