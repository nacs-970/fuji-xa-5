#!/usr/bin/env bash
# Join the camera's Wi-Fi, run one command, then go back to the previous Wi-Fi connection.
#
#   scripts/with_camera_wifi.sh [options] -- <command> [args...]
#
# One cycle per command: connect -> run -> reconnect to the previous network. The camera tends to stop
# its Wi-Fi after a client connection, so start each test with a fresh join.
#
# Options:
#   --ssid-prefix P   camera network name prefix (default FUJIFILM-)
#   --dev IFACE       Wi-Fi interface (default: first Wi-Fi device NetworkManager reports)
#   --ip ADDR         camera address to wait for (default 192.168.0.1)
#   --settle SEC      pause after the camera answers ping (default 5, the control port opens late)
#   --tries N         scan and join attempts (default 8)
#   --keep            stay on the camera network afterwards (skip the reconnect)
#
# The camera must already show its wireless screen. The command's exit status is returned.
# Needs NetworkManager (nmcli). It does not change the default route: keep your internet on another
# interface (for example a USB tether) while the Wi-Fi interface is on the camera network.
set -u

usage() { sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; }

prefix="FUJIFILM-"; dev=""; ip="192.168.0.1"; settle=5; tries=8; keep=0
while [ $# -gt 0 ]; do
  case "$1" in
    --ssid-prefix) prefix=$2; shift 2 ;;
    --dev) dev=$2; shift 2 ;;
    --ip) ip=$2; shift 2 ;;
    --settle) settle=$2; shift 2 ;;
    --tries) tries=$2; shift 2 ;;
    --keep) keep=1; shift ;;
    --) shift; break ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done
[ $# -gt 0 ] || { usage >&2; exit 2; }
command -v nmcli >/dev/null || { echo "nmcli not found" >&2; exit 2; }

[ -n "$dev" ] || dev=$(nmcli -t -f DEVICE,TYPE dev | awk -F: '$2=="wifi"{print $1; exit}')
[ -n "$dev" ] || { echo "no Wi-Fi device found" >&2; exit 2; }

# The connection to return to: the active Wi-Fi profile if it is not the camera, otherwise the most
# recently used non-camera Wi-Fi profile.
prev=$(nmcli -t -f NAME,TYPE,DEVICE con show --active | awk -F: -v d="$dev" '$2=="802-11-wireless" && $3==d {print $1; exit}')
case "$prev" in "$prefix"*) prev="" ;; esac
if [ -z "$prev" ]; then
  prev=$(nmcli -t -f NAME,TYPE,TIMESTAMP con show \
    | awk -F: -v p="$prefix" '$2=="802-11-wireless" && index($1,p)!=1 {print $3 "\t" $1}' \
    | sort -rn | head -1 | cut -f2-)
fi

restored=0
restore() {
  [ "$restored" -eq 1 ] && return
  restored=1
  if [ "$keep" -eq 1 ]; then echo "[wifi] staying on the camera network (--keep)"; return; fi
  if [ -n "$prev" ]; then
    if nmcli con up id "$prev" ifname "$dev" >/dev/null 2>&1; then
      echo "[wifi] reconnected to the previous network"
    else
      echo "[wifi] could not reconnect to the previous network. Run: nmcli con up id \"$prev\"" >&2
    fi
  else
    echo "[wifi] no previous Wi-Fi profile known, left on the camera network" >&2
  fi
}
trap restore EXIT
trap 'exit 130' INT TERM

echo "[wifi] joining the camera network on $dev (up to $tries tries)"
joined=0
for i in $(seq 1 "$tries"); do
  ssid=$(nmcli -t -f SSID dev wifi list ifname "$dev" 2>/dev/null | grep -m1 "^$prefix")
  if [ -n "$ssid" ] && nmcli dev wifi connect "$ssid" ifname "$dev" >/dev/null 2>&1; then joined=1; break; fi
  nmcli dev wifi rescan ifname "$dev" >/dev/null 2>&1
  sleep 3
done
[ "$joined" -eq 1 ] || { echo "[wifi] camera network not found. Is the wireless screen on?" >&2; exit 3; }

reached=0
for i in $(seq 1 15); do
  if ping -c1 -W1 "$ip" >/dev/null 2>&1; then reached=1; break; fi
done
[ "$reached" -eq 1 ] || { echo "[wifi] joined, but $ip does not answer ping" >&2; exit 4; }
echo "[wifi] camera answers, waiting ${settle}s for the control port"
sleep "$settle"

"$@"
rc=$?
echo "[wifi] command exited with status $rc"
exit "$rc"
