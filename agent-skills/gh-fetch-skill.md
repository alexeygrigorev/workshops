---
name: gh-fetch
description: Fetch content from GitHub repos using gh CLI
---

# GitHub Fetch Skill

Use this skill when the user wants to:
- Get files from a GitHub repo
- List files in a repo
- Explore repo structure
- Fetch command definitions from repos
- Save files from a repo locally

## Working gh Commands

List repo root contents:
```bash
gh api repos/owner/repo/contents/
```

List subdirectory contents:
```bash
gh api repos/owner/repo/contents/.claude/commands
gh api repos/owner/repo/contents/path/to/dir
```

Get file content (decoded):
```bash
gh api repos/owner/repo/contents/path/file.md --jq '.content' | base64 -d
```

Save file content locally:
```bash
gh api repos/owner/repo/contents/path/file.md --jq '.content' | base64 -d > local/path/file.md
```

Get repo info:
```bash
gh api repos/owner/repo --jq '.name, .description, .default_branch_name'
```

## Usage Pattern

1. Parse repo from user input (owner/name format)
2. Use `gh api` to explore structure
3. Use `base64 -d` to decode file contents
4. If user wants to save files, redirect output using `> path/to/file`
5. Present results clearly to user
