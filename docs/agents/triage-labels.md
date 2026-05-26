# Triage Labels

Three-dimensional label system: **Type** + **Priority** + **Module**, plus Triage flow and Lifecycle labels.

## Type Labels

| Label | Color | Description |
|-------|-------|-------------|
| `bug` | red | Something isn't working |
| `feature` | green | New feature or request |
| `refactor` | blue | Code restructuring without behavior change |
| `test` | light blue | Adding or fixing tests |
| `docs` | dark blue | Documentation improvements |
| `performance` | salmon | Performance optimization |
| `security` | dark red | Security related |
| `chore` | light yellow | Maintenance, config, tooling |

## Priority Labels

| Label | Color | Description |
|-------|-------|-------------|
| `P0` | dark red | Critical: blocks production or data loss risk |
| `P1` | orange | High: needed for next release |
| `P2` | yellow | Medium: should do this quarter |
| `P3` | light blue | Low: nice to have |

## Module Labels

| Label | Color | Scope |
|-------|-------|-------|
| `mod:data` | teal | Data layer (CRUD, services, sources) |
| `mod:trading` | light blue | Trading (engines, strategies, risk, brokers) |
| `mod:api` | lavender | FastAPI web API layer |
| `mod:cli` | lavender | CLI (typer commands) |
| `mod:core` | light purple | Core libs (config, logger, DI container, enums) |
| `mod:live` | teal | Live trading (livecore, broker, gateway) |
| `mod:logging` | light yellow | Logging pipeline (structlog, ingester, ClickHouse) |
| `mod:webui` | lavender | Web UI (Vue 3 frontend) |

## Triage Flow Labels

| Label in mattpocock/skills | Label in our tracker | Meaning |
|----------------------------|----------------------|---------|
| `needs-triage` | `needs-triage` | Maintainer needs to evaluate this issue |
| `needs-info` | `needs-info` | Waiting on reporter for more information |
| `ready-for-agent` | `ready-for-agent` | Fully specified, ready for an AFK agent |
| `ready-for-human` | `ready-for-human` | Requires human implementation |
| `wontfix` | `wontfix` | Will not be actioned |

## Lifecycle Labels

| Label | Color | Meaning |
|-------|-------|---------|
| `in-progress` | green | Claimed and actively being worked on |
| `in-review` | light blue | PR submitted, waiting for code review |
| `blocked` | dark red | Blocked by another issue or external dependency |

## Suppression Labels

| Label | Color | Meaning |
|-------|-------|---------|
| `strategy-recommendation` | light purple | AI-generated strategy recommendation (not engineering work) |

查看 issue 时排除策略推荐：`gh issue list --label strategy-recommendation` 或排除 `--search "-label:strategy-recommendation"`

## Usage

- Every issue should have at least one **Type** label and one **Priority** label
- Add **Module** labels to indicate affected area
- Add **Triage** labels during triage workflow
- Multiple labels from each dimension are allowed (e.g., `test` + `refactor` + `mod:trading` + `mod:live`)
