"""Remove extensions from a Chromium browser's Default profile offline, moving their data into a backup.

Usage: remove_chromium_ext.py <user_data_dir> <process_name> <backup_dir> <ext_id>...
Example: remove_chromium_ext.py "~/Library/Application Support/Arc/User Data" Arc ~/Backups/arc-ext-2026-10-25 <id>
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DATA_DIRS = (
    "Extensions",
    "Local Extension Settings",
    "Sync Extension Settings",
    "Managed Extension Settings",
)
SECURE_KEYS = (
    ["extensions", "settings"],
    ["protection", "macs", "extensions", "settings"],
    ["protection", "macs", "extensions", "settings_encrypted_hash"],
)


def write_json(path: Path, data: dict[str, object]) -> None:
    # Chromium writes compact JSON; keep that shape and swap atomically.
    tmp = path.with_name(path.name + ".tmp-audit")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    shutil.copymode(path, tmp)
    os.replace(tmp, path)


def drop(d: dict[str, object], keys: list[str], ext_id: str) -> bool:
    node: object = d
    for k in keys:
        if not isinstance(node, dict) or k not in node:
            return False
        node = node[k]
    if isinstance(node, dict) and ext_id in node:
        del node[ext_id]
        return True
    return False


def main() -> int:
    if len(sys.argv) < 5:
        print(__doc__)
        return 2
    user_data, proc = Path(sys.argv[1]).expanduser(), sys.argv[2]
    backup, ids = Path(sys.argv[3]).expanduser(), sys.argv[4:]
    profile = user_data / "Default"
    if (
        subprocess.run(
            ["pgrep", "-x", proc], capture_output=True, check=False
        ).returncode
        == 0
    ):
        print(f"{proc} is running, abort")
        return 1
    backup.mkdir(parents=True, exist_ok=False)
    pref_files = sorted(user_data.glob("*/Preferences"))
    for f in [*pref_files, profile / "Secure Preferences"]:
        dst = backup / f.relative_to(user_data)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dst)

    for ext_id in ids:
        for sub in DATA_DIRS:
            src = profile / sub / ext_id
            if src.exists():
                dst = backup / "Default" / sub / ext_id
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                print(f"moved {sub}/{ext_id}")

    secure = json.loads((profile / "Secure Preferences").read_text())
    for ext_id in ids:
        for keys in SECURE_KEYS:
            if drop(secure, keys, ext_id):
                print(f"Secure Preferences: dropped {'.'.join(keys)}.{ext_id}")
    write_json(profile / "Secure Preferences", secure)

    for f in pref_files:
        prefs = json.loads(f.read_text())
        changed = [i for i in ids if drop(prefs, ["updateclientdata", "apps"], i)]
        if changed:
            write_json(f, prefs)
            print(f"{f.relative_to(user_data)}: dropped updateclientdata for {changed}")
    print(f"backup: {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
