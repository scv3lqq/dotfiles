"""End-to-end test of an Xray server through a local client bound to one NIC.

Usage:
  e2e.py reality PARAMS HOST [--port 443] [--sni S] [--fp chrome] [--iface en0]
  e2e.py vmess-xhttp PARAMS HOST --email E [--port 80] [--iface en0]

PARAMS is the server-side client file: reality {uuid, pbk, sid, sni},
vmess-xhttp {path, clients: {email: uuid}}. Binding to the NIC bypasses a VPN
app that owns the default route, so the test takes the real ISP path.
"""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

CHECKS = [
    ("egress ip", "https://api.ipify.org", "-"),
    ("google 204", "https://www.google.com/generate_204", "/dev/null"),
    ("10 MB download", "https://speed.cloudflare.com/__down?bytes=10000000", "/dev/null"),
]


def outbound(args: argparse.Namespace, params: dict[str, object]) -> dict[str, object]:
    sockopt = {"interface": args.iface} if args.iface != "-" else {}
    if args.proto == "reality":
        return {
            "protocol": "vless",
            "settings": {
                "vnext": [
                    {
                        "address": args.host,
                        "port": args.port or 443,
                        "users": [{"id": params["uuid"], "encryption": "none", "flow": "xtls-rprx-vision"}],
                    }
                ]
            },
            "streamSettings": {
                "network": "raw",
                "security": "reality",
                "realitySettings": {
                    "serverName": args.sni or params["sni"],
                    "fingerprint": args.fp,
                    "publicKey": params["pbk"],
                    "shortId": params["sid"],
                    "spiderX": "/",
                },
                "sockopt": sockopt,
            },
        }
    clients = params["clients"]
    assert isinstance(clients, dict)
    return {
        "protocol": "vmess",
        "settings": {
            "vnext": [
                {
                    "address": args.host,
                    "port": args.port or 80,
                    "users": [{"id": clients[args.email], "security": "auto"}],
                }
            ]
        },
        "streamSettings": {
            "network": "xhttp",
            "security": "none",
            "xhttpSettings": {"path": params["path"], "mode": "auto"},
            "sockopt": sockopt,
        },
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("proto", choices=["reality", "vmess-xhttp"])
    p.add_argument("params")
    p.add_argument("host")
    p.add_argument("--port", type=int)
    p.add_argument("--sni")
    p.add_argument("--fp", default="chrome")
    p.add_argument("--email", default="mac")
    p.add_argument("--iface", default="en0", help="'-' to use the default route")
    p.add_argument("--xray", default=os.environ.get("XRAY") or shutil.which("xray") or "xray")
    args = p.parse_args()

    params: dict[str, object] = json.loads(Path(args.params).read_text())
    cfg = {
        "log": {"loglevel": "warning"},
        "inbounds": [{"listen": "127.0.0.1", "port": 10811, "protocol": "socks", "settings": {"udp": False}}],
        "outbounds": [outbound(args, params)],
    }
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(cfg, f)
    proc = subprocess.Popen([args.xray, "run", "-c", path], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        time.sleep(1.5)
        for label, url, out in CHECKS:
            r = subprocess.run(
                [
                    "curl",
                    "-sS",
                    "--max-time",
                    "30",
                    "-x",
                    "socks5h://127.0.0.1:10811",
                    "-o",
                    out,
                    "-w",
                    " [%{http_code} %{time_total}s %{speed_download}B/s]",
                    url,
                ],
                capture_output=True,
                text=True,
            )
            print(f"{label:16} rc={r.returncode} {(r.stdout.strip() or r.stderr.strip())[:100]}")
    finally:
        proc.terminate()
        os.unlink(path)


if __name__ == "__main__":
    main()
