"""Per-connection byte counts between one client and a server port, from tcpdump text.

Usage: tcpdump -tt -nn -r cap.pcap | python3 flows.py <client-ip> <server-port>

Mobile DPI freeze signature: handshake done, 8-16 KB down, down retransmits > 0,
nothing after. A healthy flow keeps growing past that.
"""

import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field

LINE = re.compile(
    r"^(?P<ts>\d+\.\d+) IP6? (?P<src>\S+)\.(?P<sport>\d+) > (?P<dst>\S+)\.(?P<dport>\d+): "
    r"Flags \[(?P<flags>[^\]]*)\](?:, seq (?P<seq>\d+)(?::\d+)?)?.*?length (?P<len>\d+)"
)


@dataclass
class Flow:
    first: float = 0.0
    last: float = 0.0
    up: int = 0
    down: int = 0
    up_retx: int = 0
    down_retx: int = 0
    flags: set[str] = field(default_factory=set)
    seen_up: set[int] = field(default_factory=set)
    seen_down: set[int] = field(default_factory=set)


def main() -> None:
    client, port = sys.argv[1], sys.argv[2]
    flows: dict[str, Flow] = defaultdict(Flow)
    for line in sys.stdin:
        m = LINE.match(line)
        if not m:
            continue
        if m["src"] == client and m["dport"] == port:
            key, up = m["sport"], True
        elif m["dst"] == client and m["sport"] == port:
            key, up = m["dport"], False
        else:
            continue
        f = flows[key]
        ts = float(m["ts"])
        f.first = f.first or ts
        f.last = ts
        size = int(m["len"])
        f.flags.update(c for c in m["flags"] if c in "SFR")
        seq = int(m["seq"]) if m["seq"] else None
        seen = f.seen_up if up else f.seen_down
        retx = bool(size and seq is not None and seq in seen)
        if size and seq is not None:
            seen.add(seq)
        if up:
            f.up += size
            f.up_retx += retx
        else:
            f.down += size
            f.down_retx += retx

    print(f"{len(flows)} flows from {client} to :{port}")
    print(f"{'cport':>6} {'dur s':>6} {'up B':>8} {'down B':>9} {'down retx':>9} {'up retx':>7} flags")
    for key, f in sorted(flows.items(), key=lambda kv: kv[1].first)[:40]:
        dur = f.last - f.first
        flags = "".join(sorted(f.flags))
        print(f"{key:>6} {dur:6.1f} {f.up:8d} {f.down:9d} {f.down_retx:9d} {f.up_retx:7d} {flags}")
    buckets: dict[int, int] = defaultdict(int)
    for f in flows.values():
        buckets[f.down // 4096 * 4] += 1
    hist = " ".join(f"{k}K:{v}" for k, v in sorted(buckets.items()))
    total = sum(f.down for f in flows.values())
    total_retx = sum(f.down_retx for f in flows.values())
    print(f"total down {total} B, down retransmits {total_retx}; flows by down size {hist}")


if __name__ == "__main__":
    main()
