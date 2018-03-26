import smtplib
from email.mime.text import MIMEText
import os
from pathlib import Path
import json
from typing import Dict
from urllib.parse import parse_qs

CONFIG_ROOT = "/etc/send-mail.lizeyan.me/"


class MailServerPool:
    def __init__(self, config_root: str):
        config_root = Path(os.path.abspath(config_root))
        self.mail_server_dict = {}  # type: Dict[MailServer]
        for config_file in config_root.glob("*.conf"):
            with open(config_root / config_file, "r") as f:
                config = json.load(f)
                self.mail_server_dict[config["user"]] = MailServer(config["host"], config["user"], config["pass"])

    def __str__(self):
        return str(list(_.mail_user for _ in self.mail_server_dict.values()))


class MailServer:
    def __init__(self, mail_host, mail_user, mail_pass):
        self.server = smtplib.SMTP()
        self.server.connect(mail_host)
        self.server.login(mail_user, mail_pass)
        self.mail_user = mail_user

    def send_mail(self, sub, content, to_list: list):
        msg = MIMEText(content, _subtype='plain')
        msg['Subject'] = sub
        msg['From'] = self.mail_user
        msg['To'] = ";".join(to_list)
        try:
            self.server.sendmail(self.mail_user, to_list, msg.as_string())
            return {"status": "success"}
        except Exception as e:
            return {"status": "fail", "error_msg": str(e)}


mail_server_pool = MailServerPool(CONFIG_ROOT)


def application(environ, start_response):
    query_string = parse_qs(environ["QUERY_STRING"])
    sub = ";".join(query_string.get("sub"))
    content = "\n".join(query_string.get("content"))
    to_list = query_string.get("to")
    from_list = query_string.get("from")

    path = environ["PATH_INFO"]
    if Path(path) == Path("/"):
        for from_server in from_list:
            if from_server in mail_server_pool.mail_server_dict:
                start_response('200 OK', [('Content-Type', 'text/html')])
                ret = mail_server_pool.mail_server_dict[from_server].send_mail(sub, content, to_list)
                return [str(ret)]
    elif Path(path) == Path("/server_list"):
        start_response('200 OK', [('Content-Type', 'text/html')])
        return [str(mail_server_pool)]
    else:
        start_response('404 Not Found')
        return None

