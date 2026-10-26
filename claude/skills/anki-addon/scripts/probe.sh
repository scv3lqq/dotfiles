#!/usr/bin/env bash
# Read facts out of the installed Anki.app instead of guessing them.
set -u

APP="${ANKI_APP:-/Applications/Anki.app}"
PKGS="$APP/Contents/Resources/app_packages"
CSS="$PKGS/_aqt/data/web/css"
DATA="$HOME/Library/Application Support/Anki2"

die() { echo "$*" >&2; exit 1; }

pyc_syms() { # file regex
  python3 - "$1" "$2" <<'PY'
import re, sys
data = open(sys.argv[1], 'rb').read().decode('latin-1')
print('\n'.join(sorted(set(re.findall(sys.argv[2], data)))))
PY
}

case "${1:-}" in
version)
  defaults read "$APP/Contents/Info.plist" CFBundleShortVersionString
  echo "--- add-ons ---"; ls "$DATA/addons21" 2>/dev/null
  echo "--- profile ---"
  python3 - "$DATA/prefs21.db" <<'PY'
import pickle, sqlite3, sys
db = sqlite3.connect(sys.argv[1])
for name, blob in db.execute("select * from profiles"):
    try:
        d = pickle.loads(blob)
    except Exception:
        continue
    if isinstance(d, dict) and 'theme' in d:
        print(name, 'theme =', d['theme'], '(0 system / 1 light / 2 dark)')
PY
  ;;
hooks)
  [ $# -ge 2 ] || die "usage: probe.sh hooks <regex>"
  pyc_syms "$PKGS/_aqt/hooks.pyc" "$2"
  ;;
syms)
  [ $# -ge 3 ] || die "usage: probe.sh syms <module> <regex>   # module: aqt/reviewer, _aqt/hooks"
  pyc_syms "$PKGS/$2.pyc" "$3"
  ;;
css)
  [ $# -ge 2 ] || die "usage: probe.sh css <webview|reviewer|reviewer-bottom|deckbrowser|overview|toolbar>"
  python3 - "$CSS/$2.css" <<'PY'
import sys
s = open(sys.argv[1]).read()
k = 'h1{margin-bottom:.2em}'
i = s.rfind(k)
# the shared prelude repeats; the screen-specific rules are what follows it
print(s[i + len(k):] if i >= 0 else s)
PY
  ;;
check)
  [ $# -ge 2 ] || die "usage: probe.sh check <package-name>"
  pid=$(pgrep -x Anki) || die "Anki is not running"
  for port in $(lsof -nP -iTCP -sTCP:LISTEN -a -p "$pid" | awk 'NR>1{print $9}' | sed 's/.*://' | sort -u); do
    [ "$port" = "8765" ] && continue
    for f in theme.css statusbar.js; do
      code=$(curl -s -o /dev/null -m 4 -w '%{http_code}' "http://127.0.0.1:$port/_addons/$2/web/$f")
      echo "$port /_addons/$2/web/$f -> $code"
    done
  done
  echo "--- ankiconnect ---"
  curl -s -m 4 localhost:8765 -X POST -d '{"action":"version","version":6}'; echo
  echo "--- crash.log ---"; tail -c 500 "$DATA/crash.log" 2>/dev/null
  ;;
restart)
  pgrep -x Anki >/dev/null && osascript -e 'quit app "Anki"'
  for _ in $(seq 1 20); do pgrep -x Anki >/dev/null || break; /bin/sleep 1; done
  open -a Anki
  for _ in $(seq 1 30); do pgrep -x Anki >/dev/null && break; /bin/sleep 1; done
  /bin/sleep 5; echo "Anki pid $(pgrep -x Anki)"
  ;;
*)
  die "usage: probe.sh {version|hooks <re>|syms <mod> <re>|css <name>|check <pkg>|restart}"
  ;;
esac
