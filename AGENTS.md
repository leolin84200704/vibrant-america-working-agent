# Subagent Patterns

How the work loop (CLAUDE.md) uses Claude Code subagents. These are patterns, not runtime-registered agent types.

## explore (Work Loop Step 2)
Read-only Explore subagent: given a ticket, sweep the relevant LIS repos for the files, configs, and existing patterns the change will touch. Returns conclusions, not file dumps. Always used before proposing a solution.

## debate pair (Work Loop Step 3 — gated)
Two subagents launched in parallel, only for non-routine work (code changes, new patterns, incidents, prod-data impact):
- **正方**: defends the recommended approach — merits, feasibility
- **反方**: attacks it — risks, edge cases, simpler alternatives

Routine config/integration tickets (add provider, MSH value change, integration toggle) skip the debate and cite the past ticket whose pattern they follow.

## scan (on request)
Scans Jira for assigned tickets via Atlassian MCP and produces a prioritized summary (priority + deadline, per Leo's preference). Read-only; does not create STM files — STM is created only when work on a ticket actually starts.

## Domain knowledge
Business rules for EMR integration tickets: `long-term-memory/emr-integration.md`. Ticket-type routing: `long-term-memory/ticket-routing.md`.
