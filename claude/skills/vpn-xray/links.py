"""Print client share links from a server-side params file.

Usage:
  links.py reality PARAMS NAME=HOST [NAME=HOST ...] [--port 443] [--fp chrome]
  links.py vmess-xhttp PARAMS --email E NAME=HOST [...] [--port 80]

HOST is an IPv4, a [bracketed] IPv6 or a name. VMess links use the v2rayN
base64 JSON form, which carries the XHTTP mode in `type`.
"""

import argparse
import base64
import json
from pathlib import Path
from urllib.parse import quote


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("proto", choices=["reality", "vmess-xhttp"])
    p.add_argument("params")
    p.add_argument("targets", nargs="+", metavar="NAME=HOST")
    p.add_argument("--port", type=int)
    p.add_argument("--fp", default="chrome")
    p.add_argument("--email", default="mac")
    args = p.parse_args()

    c = json.loads(Path(args.params).read_text())
    for target in args.targets:
        name, _, host = target.partition("=")
        if args.proto == "reality":
            q = (
                f"encryption=none&flow=xtls-rprx-vision&security=reality&sni={c['sni']}&fp={args.fp}"
                f"&pbk={c['pbk']}&sid={c['sid']}&spx={quote('/', safe='')}&type=tcp&headerType=none"
            )
            print(f"vless://{c['uuid']}@{host}:{args.port or 443}?{q}#{name}")
        else:
            body = {
                "v": "2",
                "ps": name,
                "add": host.strip("[]"),
                "port": str(args.port or 80),
                "id": c["clients"][args.email],
                "aid": "0",
                "scy": "auto",
                "net": "xhttp",
                "type": "auto",
                "host": "",
                "path": c["path"],
                "tls": "",
                "sni": "",
                "alpn": "",
                "fp": "",
            }
            print("vmess://" + base64.b64encode(json.dumps(body, separators=(",", ":")).encode()).decode())


if __name__ == "__main__":
    main()
