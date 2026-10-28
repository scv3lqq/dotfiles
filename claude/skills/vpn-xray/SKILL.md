---
name: vpn-xray
description: Operate and debug the user's personal Xray VPN (VLESS REALITY on 443, VMess over XHTTP on 80, optional RU forwarding bridge) against Russian DPI. Use for «VPN не работает», «с мобильного не работает», «дай ключ / новый пользователь», «новый VPS под VPN», «проверь блокировку», REALITY target or SNI choice, share links (vless://, vmess://).
argument-hint: "[symptom or task]"
---

# vpn-xray

Hosts, ports and history: auto-memory `vpn-lt-and-ru-bridge`, then the server's own `/root/AGENTS.md` (read it over ssh before changing anything). Client params (`/root/xray-client*.json`) are secrets: copy them to the scratchpad under `umask 077`, delete after use, never print them except as the links the user asked for.

## Local tools
- No `xray` on the Mac: download the release matching the server (`xray version` there) for macOS arm64 into the scratchpad, check its `.dgst` SHA256, pass `--xray <path>` to `e2e.py`.
- `e2e.py` (client bound to `en0`, SOCKS checks: egress IP, 204, 10 MB), `links.py` (share links), `flows.py` (per-flow bytes from a pcap). Run with `python3 -I ~/.claude/skills/vpn-xray/<script> -h`.
- The Mac's default route usually belongs to a VPN app's TUN (see the memory note): every ISP-path test binds to `en0` (`nc -z -v -b en0`, `curl --interface en0`, `e2e.py --iface en0`). The bridge is the Russian datacenter vantage point.
- Run scripts on a host with `ssh h python3 - < file` or `scp` first; `python3 -c "$(cat f)"` inside an ssh string breaks on quoting.

## Triage ladder (stop at the first failing rung)
1. TCP: `nc -z -v -b en0 <ip> <port>`; also `timeout 6 bash -c "</dev/tcp/<ip>/<port>"` from the bridge. No SYN in `tcpdump` on the server = per-IP block upstream: new IPv4 from the provider (neighbors in the /24 usually pass) or the IPv6 address.
2. TLS with the real SNI: `openssl s_client -connect <ip>:443 -servername <sni> -brief` from the bridge, `curl -k --interface en0 --resolve <sni>:443:<ip> https://<sni>/` from home. TCP fine + handshake timeout = SNI block: compare with other SNIs to the same IP. The provider-issued VPS hostname was SNI-blocked, so no "steal yourself" on it.
3. Tunnel: `e2e.py reality|vmess-xhttp <params> <host>`. Auth failure with an odd uTLS `--fp`: only `chrome`, `safari`, `firefox` pass REALITY.
4. Mobile only: TLS to hosting IPs (foreign and RU) freezes after 8-16 KB downstream. Use the VMess/XHTTP profile on :80 (plain-HTTP framing passes). Wikipedia opening without VPN on the phone = not whitelist mode; in whitelist mode only a whitelisted cloud range (Yandex, VK) can help.

## Diagnosing the phone
iPhone USB tethering did not come up on this Mac (en5 stays inactive): skip it. Instead capture on the server(s) while the user tries one profile per ~30 s:
`timeout 900 tcpdump -ni eth0 -s 96 -w /root/x.pcap "tcp port 443 and not host <home ip>"` (background), then `tcpdump -tt -nn -r /root/x.pcap | python3 flows.py <phone ip> 443` (scp `flows.py` there; the phone's IP is the busiest non-home source). Control test: a 2 MB random file via `systemd-run --unit=dl-test --property=RuntimeMaxSec=1800 python3 -m http.server 8080`. Delete pcaps and test units afterwards.

## Server changes
- New VPS: log in with the pasted password through an askpass script in the scratchpad (`SSH_ASKPASS=<script> SSH_ASKPASS_REQUIRE=force ssh -o PubkeyAuthentication=no ...`, no sshpass), append `~/.ssh/id_ed25519.pub` to root's `authorized_keys`, delete the script. A first "timed out during banner exchange" is transient: retry. Check reachability (rungs 1-2) before installing anything.
- Xray: official `install-release.sh install --version <v>`; REALITY target from `xray tls ping <domain>` (TLS 1.3, H2) plus rung 2 from the bridge.
- Add a client: `xray uuid`, the same `email` in every inbound (`flow: xtls-rprx-vision` only on REALITY), `xray run -test -config ...`, then `systemd-run --on-active=2s /bin/systemctl restart xray`: a direct restart cuts the user's own tunnel and the ssh session riding it.
- Bridge = nftables DNAT + masquerade per port, `net.ipv4.ip_forward=1`; `bridge` is an nft keyword, name the table something else.
- After a change: rerun `e2e.py` for every profile the user has, update `/root/AGENTS.md` and the memory note.
