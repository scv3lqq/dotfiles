#!/bin/bash
# Read-only disk and RAM audit of this Mac in one pass. Sizes in GB (disk) and MB (RAM).
#   bash audit.sh [ram|disk]   (default: both; disk takes ~1-2 min)
set -u
mode=${1:-all}

hr() { printf '\n## %s\n' "$1"; }
# du -k lines ("<KB>\t<path>") -> top N as "<GB>  <path>"
show() { sort -rn | head -"$1" | awk -F'\t' '{printf "%7.1fG  %s\n", $1 / 1048576, $2}'; }

ram() {
  hr "RAM"
  sysctl -n hw.memsize | awk '{printf "total %.0f GB, ", $1 / 1073741824}'
  memory_pressure | awk '/free percentage/ {printf "free %s, ", $NF}'
  sysctl -n vm.swapusage | awk '{print "swap used " $6 " of " $3}'

  # top MEM is the physical footprint (compressed pages included); ps RSS undercounts it
  hr "Footprint by app (MB, processes)"
  top -l 1 -o mem -n 1000 -stats command,mem | awk '
    f {
      m = $NF; sub(/[+-]$/, "", m); v = m + 0
      if (m ~ /G$/) v *= 1024; else if (m ~ /K$/) v /= 1024; else if (m ~ /B$/) v /= 1048576
      n = $0; sub(/[[:space:]]+[^[:space:]]+[[:space:]]*$/, "", n)
      if (n ~ /^[0-9]+\.[0-9]+\.[0-9]+/) k = "claude-cli"
      else if (n ~ /^(plugin-container|[Zz]en|[Ff]irefox)/) k = "zen/firefox"
      else { split(n, w, " "); k = tolower(w[1]); if (k == "claude") k = "claude.app" }
      a[k] += v; c[k]++
    }
    /^COMMAND/ { f = 1 }
    END { for (k in a) printf "%7.0f %4d  %s\n", a[k], c[k], k }' | sort -rn | head -15

  hr "Claude CLI sessions (elapsed, RSS MB)"
  ps -axo etime=,rss=,comm= | awk '$3 ~ /(^|\/)(claude|[0-9]+\.[0-9]+\.[0-9]+)$/ {printf "%12s %5d\n", $1, $2 / 1024}' | sort -r

  # each CLI session spawns its own stdio MCP servers; their memory is in the "node" row above.
  # Only the matched token is printed, never the argv (it may carry keys)
  hr "MCP server processes (count)"
  ps -axo args= | awk '
    match($0, /[A-Za-z0-9_.@-]*-mcp[A-Za-z0-9_.-]*|mcp-[A-Za-z0-9_.-]+/) {
      k = substr($0, RSTART, RLENGTH); if (k !~ /^-/) c[k]++
    }
    END { for (k in c) printf "%4d  %s\n", c[k], k }' | sort -rn | head -8
}

disk() {
  hr "Disk"
  df -h /System/Volumes/Data | awk 'NR == 2 {print "data volume " $2 ", used " $3 ", free " $4}'

  tmp=$(mktemp -t mac-space)
  trap 'rm -f "$tmp"' EXIT
  # one scan of ~ to depth 3 feeds the three home views below
  du -xk -d3 "$HOME" 2>/dev/null > "$tmp"
  rel='index($2, h "/") == 1 { p = substr($2, length(h) + 2); d = gsub("/", "/", p) + 1 }'
  hr "Home, depth 1"
  awk -F'\t' -v h="$HOME" "$rel"' index($2, h "/") == 1 && d == 1' "$tmp" | show 20
  hr "Home outside Library, depth 2"
  awk -F'\t' -v h="$HOME" "$rel"' index($2, h "/") == 1 && d == 2 && p !~ /^Library\//' "$tmp" | show 20
  hr "Library app data and caches, depth 3"
  awk -F'\t' -v h="$HOME" "$rel"' index($2, h "/") == 1 && d == 3 && p ~ /^Library\/(Application Support|Containers|Group Containers|Caches)\//' "$tmp" | show 25

  hr "Files over 1G outside ~/Library"
  # -size is the logical size: sparse and iCloud-evicted files pass it with ~0 on disk, du filters them
  find "$HOME" -xdev -path "$HOME/Library" -prune -o -type f -size +1G -print0 2>/dev/null |
    xargs -0 du -k 2>/dev/null | awk '$1 >= 1048576' | show 15

  ud=$(dirname "$(getconf DARWIN_USER_TEMP_DIR)")
  hr "Per-user /var/folders, depth 2"
  du -xk -d2 "$ud" 2>/dev/null | show 6
  cs="$ud/X/com.google.Chrome.code_sign_clone"
  if [ -d "$cs" ]; then
    echo "Chrome code_sign_clone versions (count version), installed: $(plutil -extract CFBundleShortVersionString raw '/Applications/Google Chrome.app/Contents/Info.plist' 2>/dev/null)"
    for f in "$cs"/code_sign_clone.*/*/Contents/Info.plist; do
      [ -f "$f" ] && plutil -extract CFBundleShortVersionString raw "$f"
    done | sort | uniq -c
  fi

  hr "Applications and system dirs"
  { du -xk -d1 /Applications 2>/dev/null | awk -F'\t' '$2 != "/Applications"'; du -xks /opt/homebrew /Library /private/var 2>/dev/null; } | show 12

  hr "Colima / Docker"
  if command -v colima >/dev/null; then colima list 2>/dev/null; fi
  if docker info >/dev/null 2>&1; then docker system df; fi
}

case $mode in
  ram) ram ;;
  disk) disk ;;
  *) ram; disk ;;
esac
