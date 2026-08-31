# Hackathon Screenshot Guide

Use these filenames so the project README and demo deck can tell one consistent story.

| File | What it should show | Judge takeaway |
|---|---|---|
| `01-agent-registry.png` | TrueFoundry Agent Registry for `harness-os`, Gemini model, FaultLine H-005 MCP, GitHub MCP, sandbox enabled | Harness OS is running as a real tool-using agent, not a mocked chat |
| `02-live-h005-baseline.png` | Live H-005 result showing 2 refunds / 49,800 cents and no state verification | The dangerous failure is reproducible with real evidence |
| `03-human-approval.png` | Agent stopped before GitHub mutation and explicitly requesting approval | Human control exists at the irreversible repository-mutation boundary |
| `04-github-evidence.png` | Exact GitHub branch/commit/PR evidence | Remediation provenance is auditable |
| `05-safety-case.png` | Post-remediation replay and final Safety Case | Release decision is tied to replayed evidence |

## Recommended README gallery

After the PNGs are uploaded, add this directly under the `## Demo screenshots` heading in the root README:

```html
<p align="center">
  <img src="docs/screenshots/01-agent-registry.png" width="49%" alt="Harness OS agent registry with FaultLine and GitHub MCP" />
  <img src="docs/screenshots/02-live-h005-baseline.png" width="49%" alt="Live H-005 duplicate-refund evidence" />
</p>
<p align="center">
  <img src="docs/screenshots/03-human-approval.png" width="49%" alt="Human approval checkpoint" />
  <img src="docs/screenshots/04-github-evidence.png" width="49%" alt="GitHub remediation evidence" />
</p>
<p align="center">
  <img src="docs/screenshots/05-safety-case.png" width="70%" alt="Harness OS final Safety Case" />
</p>
```

## Screenshot hygiene

- Crop browser chrome unless the URL proves an important integration boundary.
- Never expose API keys, bearer tokens, provider credentials, personal email addresses, or secrets.
- Keep the project/agent name visible.
- Prefer one clear result per screenshot.
- For H-005 evidence, keep the actual `refund_count`, `total_refunded_cents`, refund IDs, timeout trace IDs, and `state verification between attempts: NO` visible.
- For approval evidence, show that no branch/file/PR mutation happened before approval.
- For the final Safety Case, show the exact PR and replay evidence rather than a purely narrative summary.
