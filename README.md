# export-md

A `/export-md` slash command for [Claude Code](https://claude.com/claude-code) that saves the
current session as a clean, readable markdown file.

## Why this exists

I kept wanting to copy paste stuff from claude code — a debugging trail, some text, but Claude code is so annoying when working with text.

My only option was selecting text in the terminal and copy-pasting it somewhere, which
mangles the wrapping, loses the code blocks, or adds strange characters.

Claude Code ships a built-in `/export`, but it hands you the raw conversation in a txt. I wanted
something I could paste straight into notes, a PR description, or a docs page: proper
headings per turn, code fences intact, tool noise collapsed down to one line, and my own
choice of filename and folder.

So this reads the session transcript Claude Code already writes to disk and renders it as
markdown instead so you can copy paste easily.

## Install

Requires `python3` (3.6+, already present on macOS and most Linux distros).

**For all your projects:**

Replace `OWNER` with the repository owner.

```bash
git clone https://github.com/OWNER/export-md.git
cd export-md
./install.sh
```

**For one repo** (checks in alongside your code, so your whole team gets it):

```bash
./install.sh --project /path/to/your/repo
```

Then start a new Claude Code session and type `/export-md`.

To remove it: `./install.sh --uninstall` (add `--project PATH` to scope it).

<details>
<summary>Manual install, if you'd rather not run a script</summary>

Copy two files and fix one path.

1. `scripts/export-md.py` → `~/.claude/scripts/export-md.py`
2. `commands/export-md.md` → `~/.claude/commands/export-md.md`
3. In that second file, replace both occurrences of `__SCRIPT_PATH__` with the real,
   absolute path to the script — e.g. `/path/to/.claude/scripts/export-md.py`.

Slash commands don't expand `~` or `$HOME` inside `allowed-tools`, which is why step 3
needs a literal path. For a project-scoped install, put the files under `.claude/` in the
repo instead and use the relative path `.claude/scripts/export-md.py`, which stays portable
for anyone who clones it.

</details>

## Usage

```
/export-md                      # → ./2026-01-15-0812-a1b2c3d4.md
/export-md thread.md            # → ./thread.md
/export-md notes/deep/x.md      # nested dirs are created for you
/export-md ~/Desktop/chat.md    # absolute and ~ paths both work
/export-md mythread             # .md is appended if you leave it off
```

Paths are relative to whatever directory you're working in.

### Options

| Flag              | Effect                                                      |
| ----------------- | ----------------------------------------------------------- |
| `--with-thinking` | Include Claude's reasoning blocks, in collapsed `<details>` |
| `--full-tools`    | Full tool inputs plus an excerpt of each result             |
| `--no-tools`      | Prose only — no tool calls at all                           |

By default you get one compact line per tool call (`> 🔧 **Bash** — \`{...}\``) and no
results, which keeps the transcript readable without pretending the work didn't happen.

### Exporting an older session

The script also runs standalone, which is how you reach conversations that have already
ended:

```bash
python3 ~/.claude/scripts/export-md.py --list
# 2026-01-15 08:08  a1b2c3d4-0000-4000-8000-000000000000  (175 KB)
# 2026-01-14 16:38  e5f6a7b8-0000-4000-8000-000000000000  (4570 KB)

python3 ~/.claude/scripts/export-md.py --session a1b2c3d4-0000-4000-8000-000000000000 out.md
```

## What you get

```markdown
# Session a1b2c3d4

- **Date**: 2026-01-15 08:12
- **Project**: `/path/to/my-app`
- **Branch**: `main`
- **Model**: `claude-opus-5`
- **Session**: `a1b2c3d4-0000-4000-8000-000000000000`

---

## User <sub>07:31</sub>

Can you fix the failing test in auth.spec.ts?

---

## Claude <sub>07:31</sub>

> 🔧 **Read** — `{"file_path": "src/auth.spec.ts"}`

The assertion expects a 401, but the middleware now returns 403 ...
```

## How it works

Claude Code already records every session as JSONL under
`~/.claude/projects/<slugified-cwd>/<session-id>.jsonl`. The script finds the transcript
for your current directory, takes the most recently modified one, and renders the user and
assistant turns as markdown.

Along the way it drops the things you didn't write and don't want in a document: injected
`<system-reminder>` blocks, sub-agent side transcripts, and internal metadata records.

Nothing is sent anywhere. It reads local files and writes a local file.

## Caveats

- **Two sessions in one repo.** With no `--session`, it picks the most recently modified
  transcript for the current directory. If you have two Claude Code windows open on the
  same repo, the other one's writes can make it the newest. Use `--list` and `--session`
  when that matters.
- **Exports contain whatever you discussed.** If that included secrets, file contents, or
  customer data, the markdown file has them too. Think before committing one.
- **Format drift.** This depends on Claude Code's on-disk transcript format, which is
  internal and can change between releases. It's a small script — if a future version moves
  things around, the fix is usually a few lines. Issues and PRs welcome.

## License

MIT — see [LICENSE](LICENSE).
