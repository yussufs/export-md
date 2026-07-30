#!/usr/bin/env bash
# Install the /export-md slash command for Claude Code.
#
#   ./install.sh                 install for every project (~/.claude)
#   ./install.sh --project       install into the current repo (./.claude)
#   ./install.sh --project PATH  install into a specific repo
#   ./install.sh --uninstall     remove a previous install (add --project to scope it)

set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCOPE="user"
TARGET_REPO=""
UNINSTALL=0

while [ $# -gt 0 ]; do
	case "$1" in
		--project|-p)
			SCOPE="project"
			if [ $# -gt 1 ] && [ "${2#-}" = "$2" ]; then
				TARGET_REPO="$2"
				shift
			fi
			;;
		--uninstall) UNINSTALL=1 ;;
		-h|--help) sed -n '2,8p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
		*) echo "Unknown option: $1" >&2; exit 1 ;;
	esac
	shift
done

if [ "$SCOPE" = "user" ]; then
	CLAUDE_DIR="$HOME/.claude"
	# Slash commands cannot expand ~ or $HOME in allowed-tools, so bake in a real path.
	SCRIPT_PATH="$CLAUDE_DIR/scripts/export-md.py"
else
	CLAUDE_DIR="$(cd "${TARGET_REPO:-$PWD}" && pwd)/.claude"
	# Project installs run with the repo root as cwd, so a relative path stays portable
	# for everyone who clones the repo.
	SCRIPT_PATH=".claude/scripts/export-md.py"
fi

CMD_FILE="$CLAUDE_DIR/commands/export-md.md"
DEST_SCRIPT="$CLAUDE_DIR/scripts/export-md.py"

if [ "$UNINSTALL" = "1" ]; then
	rm -f "$CMD_FILE" "$DEST_SCRIPT"
	rmdir "$CLAUDE_DIR/commands" "$CLAUDE_DIR/scripts" 2>/dev/null || true
	echo "Removed /export-md from $CLAUDE_DIR"
	exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
	echo "Error: python3 is required but was not found on PATH." >&2
	exit 1
fi

mkdir -p "$CLAUDE_DIR/commands" "$CLAUDE_DIR/scripts"
cp "$SRC_DIR/scripts/export-md.py" "$DEST_SCRIPT"
chmod +x "$DEST_SCRIPT"
sed "s|__SCRIPT_PATH__|$SCRIPT_PATH|g" "$SRC_DIR/commands/export-md.md" > "$CMD_FILE"

echo "Installed /export-md ($SCOPE scope)"
echo "  command: $CMD_FILE"
echo "  script:  $DEST_SCRIPT"
echo
echo "Start a new Claude Code session (or run /doctor) and type /export-md"
