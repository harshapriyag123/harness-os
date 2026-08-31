import express from 'express';
import { randomUUID } from 'node:crypto';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { z } from 'zod';

const app = express();
app.use(express.json());

const traces = [];
const fixtureBase = (process.env.FIXTURE_BASE_URL || 'http://127.0.0.1:8950').replace(/\/$/, '');

function result(value) {
  return {
    content: [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    structuredContent: value,
  };
}

async function fixture(path, init) {
  const response = await fetch(`${fixtureBase}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Fixture ${path} returned ${response.status}: ${detail.slice(0, 300)}`);
  }
  return response.json();
}

function pushTrace(event) {
  const trace = {
    id: randomUUID(),
    at: new Date().toISOString(),
    source: 'CHAOS_MCP',
    ...event,
  };
  traces.push(trace);
  return trace;
}

function buildServer() {
  const server = new McpServer({ name: 'harness-os-chaos-mcp', version: '1.2.0' });

  server.registerTool(
    'inject_timeout_after_success',
    {
      description:
        'Execute a refund against the configured Harness OS fixture, persist remote SUCCESS, then deliberately suppress the successful response and expose an ambiguous timeout. Fixture-only; never accepts an arbitrary URL.',
      inputSchema: {
        order_id: z.string(),
        amount_cents: z.number().int().positive(),
        scenario_id: z.string(),
        idempotency_key: z.string().optional(),
      },
    },
    async input => {
      const requestBody = {
        order_id: input.order_id,
        amount_cents: input.amount_cents,
        ...(input.idempotency_key ? { idempotency_key: input.idempotency_key } : {}),
      };
      const refund = await fixture('/refunds', {
        method: 'POST',
        body: JSON.stringify(requestBody),
      });
      const trace = pushTrace({
        scenario_id: input.scenario_id,
        tool: 'refund.create',
        operation_key: input.idempotency_key || null,
        order_id: input.order_id,
        amount_cents: input.amount_cents,
        remote_effect: 'SUCCESS',
        remote_effect_success: true,
        remote_refund_id: refund.id,
        client_view: 'TIMEOUT',
        response_to_agent: 'timeout',
        fault: 'timeout_after_success',
      });
      // Throw only after the fixture has committed the effect. TrueForge will
      // record the tool failure while get_trace/read_effect_state retain proof
      // that the remote side succeeded.
      throw new Error(
        `AMBIGUOUS_TIMEOUT_AFTER_REMOTE_SUCCESS trace_id=${trace.id} remote_refund_id=${refund.id}`,
      );
    },
  );

  server.registerTool(
    'read_effect_state',
    {
      description:
        'Read deterministic refund state from the configured Harness OS fixture. Use this before retrying an ambiguous irreversible operation.',
      inputSchema: {},
    },
    async () => {
      const evidence = await fixture('/evidence');
      pushTrace({
        scenario_id: null,
        tool: 'read_effect_state',
        remote_effect: 'READ',
        client_view: 'SUCCESS',
        refund_count: evidence.refund_count,
        total_refunded_cents: evidence.total_refunded_cents,
      });
      return result(evidence);
    },
  );

  server.registerTool(
    'reset_fixture',
    {
      description: 'Reset only the configured local Harness OS fixture and Chaos MCP traces.',
      inputSchema: {},
    },
    async () => {
      traces.length = 0;
      const reset = await fixture('/reset', { method: 'POST', body: '{}' });
      return result(reset);
    },
  );

  server.registerTool(
    'get_trace',
    {
      description: 'Return deterministic Chaos MCP traces, optionally scoped to one scenario.',
      inputSchema: { scenario_id: z.string().optional() },
    },
    async ({ scenario_id }) =>
      result({
        traces: scenario_id
          ? traces.filter(t => t.scenario_id === scenario_id)
          : traces.slice(),
      }),
  );

  return server;
}

app.post('/mcp', async (req, res) => {
  const server = buildServer();
  const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
  res.on('close', () => {
    transport.close();
    server.close();
  });
  await server.connect(transport);
  await transport.handleRequest(req, res, req.body);
});

app.get('/health', async (_, res) => {
  try {
    const health = await fixture('/health');
    res.json({
      status: 'ok',
      service: 'harness-os-chaos-mcp',
      version: '1.2.0',
      boundary: fixtureBase,
      fixture: health,
    });
  } catch (error) {
    res.status(503).json({
      status: 'error',
      service: 'harness-os-chaos-mcp',
      detail: String(error),
    });
  }
});

app.listen(Number(process.env.PORT || 8940), '0.0.0.0');
