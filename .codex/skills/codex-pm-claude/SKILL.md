---
name: codex-pm-claude
description: Use when Codex should act as a project manager that delegates bounded tasks to Claude CLI, reads structured Claude output, reviews results, and handles permissions or failures with the user as the approval gate.
---

# Codex PM Claude

Use this skill when the user wants Codex to manage work while Claude CLI acts as a delegated execution or analysis agent.

## Operating Model

- Codex is the project manager and remains accountable for the final result.
- Claude is a worker agent for scoped analysis, drafting, review, or implementation suggestions.
- Codex reads Claude's structured output, checks it against the repository state, and decides the next step.
- Claude output is never treated as authoritative without review.
- If Claude triggers extra permissions, dangerous actions, network/API failure, or an unclear state, stop and explain the exact command, purpose, and risk to the user before proceeding.

## Invocation

Always use structured output. Do not rely on bare `claude -p "task"` because default human-facing output may be buffered or hard to capture from Codex.

Default worker command:

```bash
claude --permission-mode auto -p "TASK" --output-format json
```

Verbose diagnostic command:

```bash
claude --permission-mode auto -p "TASK" --output-format stream-json --verbose
```

Preferred model behavior:

- Use the Claude default model unless the user asks for a specific model.
- Keep Claude tasks small and bounded.
- Ask Claude to avoid writes unless file modification is explicitly part of the task.
- Ask Claude to report the exact commands it needs when it cannot proceed.
- Treat Claude CLI work as potentially long-running, especially for multi-file writing, review, or large-context analysis. Prefer waiting for Claude to exit naturally instead of interrupting only because there has been no output for several minutes.
- While Claude is running, do not start a second Claude task against the same files and do not edit the same files yourself unless the Claude process has clearly failed, exited, or been explicitly cancelled.

## Sandbox Rule

Claude API calls may fail inside the Codex sandbox with:

```text
API Error: Unable to connect to API (FailedToOpenSocket)
```

When this happens, rerun the same Claude command outside the sandbox by requesting escalation through the terminal tool. Use the approved prefix when available:

```bash
claude --permission-mode auto ...
```

Do not reinterpret `FailedToOpenSocket` as a Claude permission denial. It indicates API/socket connectivity failure.

## Delegation Workflow

1. Restate the user's goal as task boundaries and acceptance criteria.
2. Inspect the repository yourself first when local context matters.
3. Send Claude one focused task using `--output-format json`.
4. Wait for Claude to exit naturally whenever practical. Long periods of no terminal output are acceptable for large tasks; poll periodically and keep the user informed instead of assuming the process is stuck.
5. If waiting becomes unreasonable, first check harmless local state such as `git status` or target-file timestamps without modifying files. Interrupt Claude only when there is strong evidence of a hang, the user asks to stop, or the command is blocking necessary progress indefinitely.
6. Parse the `.result` field or read the final JSON result directly.
7. Review Claude's answer against local files, git status, and command output.
8. Apply changes yourself with Codex tools when practical, or send Claude a narrower follow-up task.
9. Run verification commands appropriate to the task.
10. Summarize what Claude did, what Codex verified, and any residual risk.

## Permission Gate

If Claude requests or attempts any of the following, pause and ask the user through Codex's approval flow:

- Shell commands that require escalated sandbox permissions.
- Network access beyond the Claude API call.
- Dependency installation or downloads.
- File deletion, truncation, overwrites, or broad generated changes.
- Writes outside the current workspace.
- Git history rewrites, force pushes, branch deletion, or pushes to shared/default branches.
- Changes to Claude/Codex configuration or permission files.
- Any command whose purpose or target is unclear.

When requesting approval, include:

- The exact command.
- Why it is needed.
- What it may change.
- The consequence of denying it.

## Task Prompt Template

Use this shape for Claude worker prompts:

```text
You are a worker agent. Codex is the project manager.

Task:
<specific task>

Scope:
- Work only in the current repository.
- Do not modify files unless explicitly requested.
- Do not install dependencies, delete files, push, or rewrite git history.
- If you need a command that requires permission, report the exact command and reason instead of trying to bypass it.

Output:
- Summarize findings or proposed changes.
- List files inspected or commands you recommend.
- Note any blockers or uncertainty.
```

## Failure Handling

- Long-running Claude command with no output: keep waiting by default, especially if the task involves multi-file edits or large context. Provide periodic user updates. Do not interrupt solely because a few minutes have passed.
- Before cancelling a long-running Claude command, inspect non-invasive local evidence when possible and explain why continued waiting is no longer useful.
- No output from plain `claude -p`: rerun with `--output-format stream-json --verbose`.
- `FailedToOpenSocket`: rerun outside sandbox with escalation.
- Permission denial: summarize the denied action and request user approval only if the action is needed.
- Claude edits or recommendations look risky: do not apply them; narrow the prompt or handle the change directly.
- Claude result conflicts with local evidence: trust local evidence and either correct Claude or proceed without it.
