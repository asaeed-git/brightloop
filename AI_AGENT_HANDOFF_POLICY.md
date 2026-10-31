# Reusable AI Agent Instruction: Continuous Project Handoff

> **How to use:** Place this file in any software project or paste its contents into an AI coding agent's project instructions. It applies to projects of any size, language, framework, or development stage.

## Role and objective

You are an AI coding agent assisting with a software project. Maintain a reliable, continuously usable handoff document so another developer or AI agent can take over without depending on your chat history.

## Required file

Create and maintain **`HANDOFF_INSTRUCTIONS.md`** at the repository or project root. If one already exists, review and update it rather than replacing useful information. Create it **as soon as you begin work**, even if the project is only being planned.

The handoff file describes the **actual current state**, not an aspirational plan. It must be accurate enough for another agent to identify the next step and safely resume work.

## Required contents of `HANDOFF_INSTRUCTIONS.md`

Use this structure, adapting sections only when genuinely irrelevant:

1. **Project snapshot:** Purpose, current objective, stack, architecture summary, development stage.
2. **Ownership and scope:** Your assigned work, collaborators or module owners, files or components outside your scope.
3. **Repository map:** Important directories, entry points, key configuration files, and relevant source locations.
4. **Current status:** Completed and verified work; in-progress work; unstarted work; known limitations. Keep these categories distinct.
5. **Technical contracts and decisions:** Data models, API contracts, interfaces, permissions, key dependencies, conventions, and reasons for non-obvious decisions.
6. **Recent meaningful changes:** What changed, why, key affected files, and relevant commit or branch identifiers when available.
7. **Open issues and risks:** Bugs, failing checks, unresolved decisions, blockers, integration dependencies, security concerns, and data-migration risks.
8. **Next actions:** A short, ordered, actionable checklist with prerequisites, relevant files, expected outcome, and how to verify completion.
9. **Run and verification instructions:** Setup, install, run, build, test, lint, type-check, and migration commands as applicable; environment-variable **names only**; last-known results and outstanding untested areas.
10. **Handoff checkpoint:** Current branch, working-tree status if known, uncommitted work, last review/update context, and any precautions for the next agent.

Do not paste passwords, private keys, access tokens, connection strings containing secrets, or sensitive user data into the handoff file.

## Continuous-update rules

Update the handoff file:

- At the beginning of the engagement, after inspecting the project.
- Before substantial new work, to record the current goal and expected scope.
- After meaningful feature, schema, interface, dependency, or configuration changes.
- Immediately when a significant bug, blocker, design decision, or integration risk arises.
- After relevant tests, builds, or other verification steps change the known status.
- Before significant commits, pull requests, merges, pauses, session endings, or transfers to another agent.

Keep it current **throughout development**, not as a one-time end-of-session report. If you cannot write to the file in the current environment, provide a precise proposed update and state that the file itself has not been modified.

## Accuracy and brevity

- Inspect source files and repository state before making factual status claims.
- Clearly distinguish **verified**, **implemented but unverified**, **planned**, and **blocked** work.
- Never state that a test passed unless it actually ran and passed.
- Include exact paths and commands wherever they help the next developer act.
- Replace superseded details rather than accumulating contradictory or repetitive logs.
- Keep a compact status summary near the top; preserve important decisions and unresolved issues.
- Do not assume another agent can read your conversation history.

## Multi-agent and multi-branch projects

Each active developer or agent must keep handoff information accurate for **its branch and assigned scope**. Agree on ownership of shared files and interfaces. Where multiple branches edit the root handoff file, reconcile the content during merging rather than overwriting another contributor's notes. For larger projects, use additional scoped files such as `docs/handoffs/<module>.md` and keep the root document as the entry point.

## Transfer checklist

When work moves to another agent or developer:

1. Inspect the real working tree and relevant files.
2. Update status, unfinished work, blockers, branch/commit details, and validation results.
3. Note any uncommitted modifications and commands the successor must run.
4. Identify the **first recommended next action** and how to validate it.
5. Tell the incoming agent to read `HANDOFF_INSTRUCTIONS.md` and verify the repository state before changing code.

**Non-negotiable:** Keeping an accurate, actionable handoff file is part of the engineering task. At every normal checkpoint, the project must be ready for a responsible transfer without requiring the previous agent's memory.
