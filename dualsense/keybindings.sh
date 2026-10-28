#!/usr/bin/env bash
# Omarchy keybindings menu with editable DualSense entries.
set -uo pipefail
upstream=/usr/bin/omarchy-menu-keybindings
[[ -r $upstream ]] || exec omarchy-menu-keybindings "$@"
source "$upstream" --print >/dev/null 2>&1
declare -F output_binding_records >/dev/null || exec omarchy-menu-keybindings "$@"
declare -F dispatch_binding >/dev/null || exec omarchy-menu-keybindings "$@"
records=$(output_binding_records)
controller_records=$("$HOME/.local/share/omarchy-dualsense/menu.py" --records) || controller_records=''
records+=$'\n'"$controller_records"
if [[ ${1-} == --print || ${1-} == -p ]]; then
  cut -f1 <<<"$records"
  exit
fi
selection=$(cut -f1 <<<"$records" | omarchy-menu-select 'Keybindings' -- --width 800 --height 500) || exit 0
record=$(awk -F '\t' -v selection="$selection" '$1 == selection { print; exit }' <<<"$records")
[[ -n $record ]] || exit 0
dispatch_binding "$(cut -f2 <<<"$record")" "$(cut -f3- <<<"$record")"
