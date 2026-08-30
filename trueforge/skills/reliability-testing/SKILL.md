---
name: reliability-testing
description: Test ambiguous results, retries, idempotency, and partial failures against real fixtures.
---
# Reliability Testing

Reset the named fixture, record initial state, invoke the target workflow, inject only the configured fault through Chaos MCP, then read final effect state and trace. For H-005 capture first remote success, timeout delivered to the target, any state lookup, any repeated operation, and final refund count. Never target an arbitrary URL or production service.
