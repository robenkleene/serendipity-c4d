#!/usr/bin/env bash
# Install the Serendipity plugin into every Cinema 4D version's plugins folder.
#
#   ./install.sh              link to this repo, so edits apply on restart
#   ./install.sh --copy       copy instead, a frozen snapshot
#   ./install.sh --uninstall  remove it again

set -euo pipefail

mode="link"
case "${1:-}" in
  "") ;;
  --copy) mode="copy" ;;
  --uninstall) mode="uninstall" ;;
  *)
    echo "usage: $0 [--copy | --uninstall]" >&2
    exit 1
    ;;
esac

source_dir="$(cd "$(dirname "$0")" && pwd)/serendipity"
prefs_root="$HOME/Library/Preferences/Maxon"

found=0
for prefs in "$prefs_root"/Maxon\ Cinema\ 4D\ *_*; do
  [[ -d "$prefs" ]] || continue
  # Suffixed folders belong to other Maxon tools, e.g., `_p` to `c4dpy` and
  # `_s` to Team Render Server. The app, GUI or `-nogui`, uses the unsuffixed
  # `<version>_<hash>` folder.
  [[ "$(basename "$prefs")" =~ ^Maxon\ Cinema\ 4D\ [0-9]+_[0-9A-F]+$ ]] || continue
  found=1
  target="$prefs/plugins/serendipity"

  existed=0
  if [[ -L "$target" || -e "$target" ]]; then
    existed=1
    rm -rf "$target"
  fi
  case "$mode" in
    link)
      # Cinema 4D skips a plugin folder that is itself a symlink, so the folder
      # is real and only its contents link back to this repo.
      mkdir -p "$target"
      for item in "$source_dir"/*; do
        [[ "$(basename "$item")" == "__pycache__" ]] && continue
        ln -s "$item" "$target/"
      done
      echo "linked: $target"
      ;;
    copy)
      mkdir -p "$prefs/plugins"
      # `--exclude` keeps bytecode from this machine out of the copy.
      rsync -a --exclude __pycache__ "$source_dir/" "$target/"
      echo "copied: $target"
      ;;
    uninstall)
      [[ "$existed" -eq 1 ]] && echo "removed: $target"
      ;;
  esac
done

if [[ "$found" -eq 0 ]]; then
  echo "error: no Cinema 4D preferences folders in $prefs_root" >&2
  echo "       launch Cinema 4D once to create one" >&2
  exit 1
fi
