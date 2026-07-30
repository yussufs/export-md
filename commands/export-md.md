---
description: Export this session's conversation to a markdown file
argument-hint: [output-path] [--with-thinking] [--full-tools] [--no-tools]
allowed-tools: Bash(python3 __SCRIPT_PATH__:*)
---

!`python3 __SCRIPT_PATH__ $ARGUMENTS`

The export has been written. Tell the user the output path in one short line. Do not
summarise the conversation or read the exported file back.
