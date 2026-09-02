import net from 'node:net';

function parseTarget(value, fallbackPort) {
  if (!value) return null;
  try {
    const u = new URL(value);
    return { host: u.hostname, port: Number(u.port || fallbackPort) };
  } catch {
    return null;
  }
}

async function waitForTcp(name, target, attempts = 60, delayMs = 2000) {
  if (!target) return;
  for (let i = 1; i <= attempts; i++) {
    const ok = await new Promise((resolve) => {
      const socket = net.createConnection(target, () => {
        socket.end();
        resolve(true);
      });
      socket.setTimeout(2500);
      socket.on('error', () => resolve(false));
      socket.on('timeout', () => {
        socket.destroy();
        resolve(false);
      });
    });
    if (ok) {
      console.log(`[startup] ${name} reachable at ${target.host}:${target.port}`);
      return;
    }
    console.log(`[startup] waiting for ${name} (${i}/${attempts}) ${target.host}:${target.port}`);
    await new Promise((r) => setTimeout(r, delayMs));
  }
  throw new Error(`${name} did not become reachable at ${target.host}:${target.port}`);
}

const standalone = String(process.env.STANDALONE || '').toLowerCase() === 'true';
if (!standalone) {
  const redis = parseTarget(process.env.REDIS_URL, 6379);
  const postgres = process.env.POSTGRES_HOST
    ? { host: process.env.POSTGRES_HOST, port: Number(process.env.POSTGRES_PORT || 5432) }
    : parseTarget(process.env.DATABASE_URL, 5432);
  await waitForTcp('postgres', postgres);
  await waitForTcp('redis', redis);
}

await import('./node_modules/@truefoundry/trueforge/dist/main.js');
