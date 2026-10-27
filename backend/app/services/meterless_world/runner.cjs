/**
 * Meterless World Model Node Runner
 * Executes real operations against the official Meterless World Model engine.
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

function loadWorldEngine(customPath) {
  const candidatePaths = [
    customPath,
    path.join(__dirname, 'worldmodel.js'),
    '/Applications/Nightshift.app/Contents/Resources/engine/js/engine/worldmodel.js',
  ].filter(Boolean);

  for (const p of candidatePaths) {
    if (fs.existsSync(p)) {
      const code = fs.readFileSync(p, 'utf8');
      const sandbox = { window: {}, console, setTimeout, clearTimeout, require, Buffer, Date, Math, JSON };
      vm.createContext(sandbox);
      vm.runInContext(code, sandbox);
      if (sandbox.window && sandbox.window.RT && sandbox.window.RT.world) {
        return sandbox.window.RT.world;
      }
    }
  }
  throw new Error('Meterless worldmodel.js engine could not be located.');
}

async function handleCommand(input) {
  const engine = loadWorldEngine(input.enginePath);
  const worldName = input.worldName || 'investigation';
  const worldDir = input.worldDir;

  let adapter = null;
  if (worldDir) {
    fs.mkdirSync(worldDir, { recursive: true });
    const safeName = String(worldName).replace(/[^A-Za-z0-9._-]+/g, '_').slice(0, 80);
    const hash = engine.sha256Hex(String(worldName)).slice(0, 8);
    const filePath = path.join(worldDir, `${safeName}-${hash}.json`);
    adapter = engine.fileAdapter(filePath, fs, path, worldName);
  } else {
    adapter = engine.memoryAdapter();
  }

  const world = engine.createWorld({
    name: worldName,
    adapter,
  });

  const results = [];
  const actions = input.actions || [];

  for (const item of actions) {
    const act = item.action;
    try {
      if (act === 'init') {
        const s = await world.stats();
        results.push({ ok: true, action: act, stats: s });
      } else if (act === 'upsert_entity') {
        const ent = await world.upsertEntity(item.entity);
        results.push({ ok: true, action: act, entity: ent });
      } else if (act === 'append_observation') {
        const obs = await world.appendObservation(item.observation);
        results.push({ ok: true, action: act, observation: obs });
      } else if (act === 'get_entity') {
        const ent = await world.getEntity(item.id);
        results.push({ ok: true, action: act, entity: ent });
      } else if (act === 'build_context') {
        const ctx = await world.buildContext(item.params || {});
        results.push({ ok: true, action: act, context: ctx });
      } else if (act === 'stats') {
        const s = await world.stats();
        results.push({ ok: true, action: act, stats: s });
      } else if (act === 'snapshot') {
        const snap = await world.snapshot();
        let parsed = null;
        try { parsed = JSON.parse(snap); } catch (_) { parsed = snap; }
        results.push({ ok: true, action: act, snapshot: parsed });
      } else {
        results.push({ ok: false, action: act, error: `Unknown action: ${act}` });
      }
    } catch (err) {
      results.push({ ok: false, action: act, error: err.message || String(err) });
    }
  }

  // If using file adapter, flush to disk before exiting
  if (adapter && typeof adapter.flush === 'function') {
    adapter.flush();
  }

  return { ok: true, worldName, results };
}

// Read JSON input from stdin or argument
async function main() {
  let raw = '';
  if (process.argv[2]) {
    raw = process.argv[2];
  } else {
    const chunks = [];
    for await (const chunk of process.stdin) {
      chunks.push(chunk);
    }
    raw = Buffer.concat(chunks).toString('utf8');
  }

  try {
    const parsed = JSON.parse(raw);
    const out = await handleCommand(parsed);
    process.stdout.write(JSON.stringify(out));
  } catch (err) {
    process.stderr.write(JSON.stringify({ ok: false, error: err.message || String(err) }));
    process.exit(1);
  }
}

main();
