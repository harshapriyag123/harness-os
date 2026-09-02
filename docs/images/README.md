# Harness OS screenshot assets

The root README no longer embeds screenshot filenames that do not exist. That was the cause of the broken image boxes in earlier revisions.

The README now uses GitHub-native Mermaid diagrams and status badges, which render without repository image assets.

When real judge-facing screenshots are captured, add them here first and only then embed them in the README.

Recommended filenames:

- `01-mission-control.png` — active target, TrueForge state, current stage and operator summary
- `02-trueforge-agent.png` — `harness-os` agent with model and attached connectors; hide all secrets
- `03-github-mcp.png` — real GitHub MCP tool list / successful read-only call
- `04-h005-fail.png` — expected $249, actual $498, two committed effects
- `05-flight-recorder.png` — causal trace showing remote effect → timeout → repeated operation → duplicate effect
- `06-approval-gate.png` — TrueForge paused before the exact consequential GitHub MCP action
- `07-safety-case.png` — scoped `ALLOW_FOR_TESTED_CONDITION` recommendation with real evidence gates

## Capture guidance

Use wide desktop screenshots (16:9 works well). Crop distracting browser chrome, but keep enough context to prove target, runtime state, source and evidence.

Never include API keys, GitHub PATs, OAuth tokens, `.env` contents, private repository information, password-manager UI or unrelated personal data.

## Before adding an image to README

1. Commit the image to this directory.
2. Open the image URL on the branch and verify GitHub renders it.
3. Add the Markdown image reference to the README.
4. Re-open the README and confirm there is no broken placeholder.

Do not add placeholder image links for screenshots that have not been captured yet.
