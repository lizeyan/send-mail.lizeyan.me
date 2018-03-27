import smtplib
from smtplib import SMTP, SMTP_SSL
from email.mime.text import MIMEText
import os
from pathlib import Path
import json
from urllib.parse import parse_qs

CONFIG_ROOT = "/etc/send-mail.lizeyan.me/"


class MailServerPool:
    def __init__(self, config_root):
        config_root = Path(os.path.abspath(config_root))
        self.mail_server_dict = {}  # type: Dict[MailServer]
        for config_file in config_root.glob("*.conf"):
            with open(str(config_root / config_file), "r") as f:
                config = json.load(f)
                self.mail_server_dict[config["user"]] = MailServer(config["host"], config["user"], config["pass"], config.get("port", 25), config.get("server_type", "SMTP"))

    def __str__(self):
        return str(list(_.mail_user for _ in self.mail_server_dict.values()))


class MailServer:
    def __init__(self, mail_host, mail_user, mail_pass, mail_port=25, server_type=SMTP):
        self.mail_host = mail_host
        self.mail_user = mail_user
        self.mail_pass = mail_pass
        self.mail_port = mail_port
        assert server_type in ("SMTP", "SMTP_SSL")
        self.server_cls = server_type

    def send_mail(self, sub, content, to_list):

        msg = MIMEText(content, _subtype='plain')
        msg['Subject'] = sub
        msg['From'] = "hello"+"<"+self.mail_user+">"
        msg['To'] = ";".join(to_list)
        try:
            server = eval(self.server_cls)()
            server.connect(self.mail_host, self.mail_port)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.mail_user, self.mail_pass)
            server.sendmail(self.mail_user, to_list, msg.as_string())
            ret = {"status": "success"}
        except Exception as e:
            ret = {"status": "fail", "error_msg": str(e)}
        ret.update(self.__dict__)
        ret.update({"sub": sub, "content": content, "to_list": to_list})
        del ret["mail_pass"]
        return ret




def application(environ, start_response):
    query_string = parse_qs(environ["QUERY_STRING"])
    sub = ";".join(query_string.get("sub", []))
    content = "\n".join(query_string.get("content", ""))
    to_list = query_string.get("to", [])
    from_list = query_string.get("from", "")

    path = environ["PATH_INFO"]
    mail_server_pool = MailServerPool(CONFIG_ROOT)
    if Path(path) == Path("/"):
        ret_list = []
        for from_server in from_list:
            if from_server in mail_server_pool.mail_server_dict:
                ret = mail_server_pool.mail_server_dict[from_server].send_mail(sub, content, to_list)
                ret_list.append(json.dumps(ret).encode("utf-8"))
        start_response('200 OK', [('Content-Type', 'text/html')])
        return ret_list
    elif Path(path) == Path("/server_list"):
        start_response('200 OK', [('Content-Type', 'text/html')])
        return [str(mail_server_pool).encode("utf-8")]
    else:
        start_response('404 Not Found', [("Content-Type", 'text/html')])
        return ["".encode("utf-8")]

