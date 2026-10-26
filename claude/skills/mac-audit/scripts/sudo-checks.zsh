#!/bin/zsh
# Read-only root checks for the mac-audit skill. Usage: sudo-checks.zsh <out_dir>
setopt nullglob
OUT=${1:?usage: sudo-checks.zsh <out_dir>}
mkdir -p "$OUT"
print "macOS audit: read-only root checks (about 30 s). Enter your password once."
sudo -v || { print "sudo failed" > "$OUT/DONE"; exit 1; }

sudo sfltool dumpbtm > "$OUT/btm.txt" 2>&1
sudo lsof -nP -i > "$OUT/lsof_all.txt" 2>&1
sudo lsof -nP +L1 > "$OUT/lsof_deleted.txt" 2>&1
sudo powermetrics --samplers tasks,cpu_power,gpu_power -n 3 -i 5000 --show-process-energy --show-process-gpu > "$OUT/powermetrics.txt" 2>&1
sudo crontab -u root -l > "$OUT/root_crontab.txt" 2>&1
sudo ls -la /usr/lib/cron/tabs /var/at/tabs /var/at/jobs > "$OUT/cron_tabs.txt" 2>&1
sudo cat /etc/sudoers /etc/sudoers.d/* > "$OUT/sudoers.txt" 2>&1
sudo profiles show -all > "$OUT/profiles.txt" 2>&1
{ sudo systemsetup -getremotelogin; sudo systemsetup -getremoteappleevents; } > "$OUT/remote.txt" 2>&1
sudo defaults read /var/root/Library/Preferences/com.apple.loginwindow > "$OUT/root_loginwindow.txt" 2>&1
sudo ls -la /var/root /var/root/Library/LaunchAgents /var/root/.ssh > "$OUT/root_home.txt" 2>&1
for f in .zshrc .zprofile .zshenv .zlogin .profile .bashrc .bash_profile .ssh/authorized_keys; do
  sudo test -f "/var/root/$f" && { print "=== /var/root/$f"; sudo cat "/var/root/$f"; }
done > "$OUT/root_rc.txt" 2>&1
for h in /Library/PrivilegedHelperTools/*; do
  print "=== $h"; sudo codesign -dv "$h" 2>&1 | grep -E 'Authority=Developer|TeamIdentifier|adhoc|not signed'
done > "$OUT/helpers_sig.txt" 2>&1

sudo -k
print ok > "$OUT/DONE"
print "Done, window closes in 3 s."
sleep 3
