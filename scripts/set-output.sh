#!/usr/bin/env bash
set -euo pipefail

want="${1:-}"
if [[ -z "$want" ]]; then
  echo "Usage: $0 dac|hdmi|headphones|snap|both|none"
  mpc outputs
  exit 1
fi

disable_all () {
  while read -r line; do
    id="$(echo "$line" | awk '{print $2}' | tr -d '()')"
    [[ "$id" =~ ^[0-9]+$ ]] && mpc disable "$id" >/dev/null 2>&1 || true
  done < <(mpc outputs | grep -E '^Output ')
}

enable_by_name () {
  local name="$1"
  local id
  id="$(mpc outputs | sed -n "s/^Output \([0-9]\+\) (${name}).*/\1/p" | head -n1)"
  [[ -n "$id" ]] && mpc enable "$id"
}

disable_all

case "$want" in
  dac)        enable_by_name "DAC strict" ;;
  hdmi)       enable_by_name "HDMI" ;;
  headphones) enable_by_name "Headphones" ;;
  snap)       enable_by_name "snapcast" ;;
  both)       enable_by_name "DAC strict"; enable_by_name "snapcast" ;;
  none)       ;;
  *) echo "Option inconnue: $want"; exit 1 ;;
esac

mpc outputs
