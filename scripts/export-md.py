#!/usr/bin/env python3
"""Export the current Claude Code session transcript to a markdown file.

Reads the session JSONL that Claude Code writes to
~/.claude/projects/<cwd-slug>/<session-id>.jsonl and renders it as markdown.

Usage:
    python3 ~/.claude/scripts/export-md.py [output-path] [options]

The output path may be relative (resolved against the current directory), absolute,
or ~-prefixed. Intermediate directories are created. With no path, the file is written
to the current directory as <date>-<session>.md.

Options:
    --session ID     Export a specific session id (default: most recent for this cwd)
    --with-thinking  Include the assistant's thinking blocks
    --no-tools       Omit tool calls entirely (default: one compact line per call)
    --full-tools     Include full tool inputs and result excerpts
    --list           List available sessions for this cwd and exit
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

RESULT_EXCERPT_CHARS = 800
TOOL_INPUT_CHARS = 300


def project_dir(cwd: Path) -> Path:
	"""Claude Code slugifies the cwd: every non-alphanumeric char becomes '-'."""
	slug = re.sub(r'[^a-zA-Z0-9]', '-', str(cwd))
	return Path.home() / '.claude' / 'projects' / slug


def find_session(cwd: Path, session_id: str | None) -> Path:
	d = project_dir(cwd)
	if not d.is_dir():
		sys.exit(f'No transcripts found for {cwd} (looked in {d})')
	if session_id:
		p = d / f'{session_id}.jsonl'
		if not p.is_file():
			sys.exit(f'Session {session_id} not found in {d}')
		return p
	files = sorted(d.glob('*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)
	if not files:
		sys.exit(f'No .jsonl transcripts in {d}')
	return files[0]


def read_records(path: Path) -> list[dict]:
	records = []
	for line in path.read_text(errors='replace').splitlines():
		line = line.strip()
		if not line:
			continue
		try:
			records.append(json.loads(line))
		except json.JSONDecodeError:
			continue
	return records


def strip_reminders(text: str) -> str:
	text = re.sub(r'<system-reminder>.*?</system-reminder>', '', text, flags=re.DOTALL)
	text = re.sub(r'<local-command-caveat>.*?</local-command-caveat>', '', text, flags=re.DOTALL)
	return text.strip()


def truncate(text: str, limit: int) -> str:
	text = text.strip()
	if len(text) <= limit:
		return text
	return text[:limit].rstrip() + f'\n… [truncated, {len(text) - limit} more chars]'


def blocks_of(message) -> list[dict]:
	"""Normalise a message's content into a list of typed blocks."""
	content = message.get('content') if isinstance(message, dict) else None
	if isinstance(content, str):
		return [{'type': 'text', 'text': content}]
	if isinstance(content, list):
		return [b for b in content if isinstance(b, dict)]
	return []


def render_tool_use(block: dict, mode: str) -> str:
	name = block.get('name', 'tool')
	raw = json.dumps(block.get('input', {}), indent=2, ensure_ascii=False)
	if mode == 'full':
		return f'> 🔧 **{name}**\n\n```json\n{truncate(raw, 4000)}\n```'
	flat = ' '.join(raw.split())
	return f'> 🔧 **{name}** — `{truncate(flat, TOOL_INPUT_CHARS)}`'


def render_tool_result(block: dict, mode: str) -> str | None:
	if mode != 'full':
		return None
	content = block.get('content')
	if isinstance(content, list):
		content = '\n'.join(b.get('text', '') for b in content if isinstance(b, dict))
	text = truncate(str(content or ''), RESULT_EXCERPT_CHARS)
	if not text:
		return None
	return f'<details><summary>tool result</summary>\n\n```\n{text}\n```\n\n</details>'


def format_time(ts: str | None) -> str:
	if not ts:
		return ''
	try:
		return datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone().strftime('%H:%M')
	except ValueError:
		return ''


def build(records: list[dict], opts) -> tuple[list[str], dict]:
	meta = {}
	out: list[str] = []
	tool_mode = 'none' if opts.no_tools else ('full' if opts.full_tools else 'compact')

	for rec in records:
		rtype = rec.get('type')
		if rtype in ('user', 'assistant') and not meta:
			meta = {
				'session': rec.get('sessionId', ''),
				'cwd': rec.get('cwd', ''),
				'branch': rec.get('gitBranch', ''),
				'started': rec.get('timestamp', '')
			}
		if rtype == 'assistant':
			meta.setdefault('model', rec.get('message', {}).get('model', ''))

		if rtype not in ('user', 'assistant'):
			continue
		if rec.get('isSidechain'):  # subagent transcripts, not the main thread
			continue
		if rec.get('isMeta'):
			continue

		blocks = blocks_of(rec.get('message', {}))
		parts: list[str] = []

		for b in blocks:
			btype = b.get('type')
			if btype == 'text':
				text = strip_reminders(b.get('text', ''))
				if text:
					parts.append(text)
			elif btype == 'thinking' and opts.with_thinking:
				thought = b.get('thinking', '').strip()
				if thought:
					parts.append(
						f'<details><summary>thinking</summary>\n\n{thought}\n\n</details>'
					)
			elif btype == 'tool_use' and tool_mode != 'none':
				parts.append(render_tool_use(b, tool_mode))
			elif btype == 'tool_result':
				rendered = render_tool_result(b, tool_mode)
				if rendered:
					parts.append(rendered)

		if not parts:
			continue

		# A user record carrying only tool_result blocks is tool output, not a real turn.
		only_results = all(b.get('type') == 'tool_result' for b in blocks) and bool(blocks)
		if rtype == 'user' and only_results:
			out.append('\n'.join(parts))
			continue

		stamp = format_time(rec.get('timestamp'))
		who = 'User' if rtype == 'user' else 'Claude'
		heading = f'## {who}' + (f' <sub>{stamp}</sub>' if stamp else '')
		out.append(heading + '\n\n' + '\n\n'.join(parts))

	return out, meta


def main() -> None:
	ap = argparse.ArgumentParser(add_help=True)
	ap.add_argument(
		'output', nargs='?', help='output path, relative to cwd (default: <date>-<session>.md)'
	)
	ap.add_argument('--session')
	ap.add_argument('--with-thinking', action='store_true')
	ap.add_argument('--no-tools', action='store_true')
	ap.add_argument('--full-tools', action='store_true')
	ap.add_argument('--list', action='store_true')
	opts = ap.parse_args()

	cwd = Path.cwd()

	if opts.list:
		d = project_dir(cwd)
		files = sorted(d.glob('*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)
		if not files:
			print(f'No sessions recorded for {cwd}')
			return
		for p in files:
			when = datetime.fromtimestamp(p.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
			print(f'{when}  {p.stem}  ({p.stat().st_size // 1024} KB)')
		return

	src = find_session(cwd, opts.session)
	records = read_records(src)
	sections, meta = build(records, opts)

	if not sections:
		sys.exit(f'Nothing to export from {src.name}')

	stamp = datetime.fromtimestamp(src.stat().st_mtime)
	if opts.output:
		dest = Path(opts.output).expanduser()
		if dest.suffix != '.md':
			dest = dest.with_suffix('.md')
		if not dest.is_absolute():
			dest = cwd / dest
	else:
		dest = cwd / f'{stamp:%Y-%m-%d-%H%M}-{src.stem[:8]}.md'
	dest.parent.mkdir(parents=True, exist_ok=True)

	header = [
		f'# Session {src.stem[:8]}',
		'',
		f'- **Date**: {stamp:%Y-%m-%d %H:%M}',
		f'- **Project**: `{meta.get("cwd") or cwd}`'
	]
	if meta.get('branch'):
		header.append(f'- **Branch**: `{meta["branch"]}`')
	if meta.get('model'):
		header.append(f'- **Model**: `{meta["model"]}`')
	header += [f'- **Session**: `{meta.get("session") or src.stem}`', '', '---', '']

	dest.write_text('\n'.join(header) + '\n\n---\n\n'.join(sections) + '\n')
	turns = sum(1 for s in sections if s.startswith('## '))
	print(f'Exported {turns} turns → {dest}')


if __name__ == '__main__':
	main()
