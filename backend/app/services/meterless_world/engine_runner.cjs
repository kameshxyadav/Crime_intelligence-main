/**
 * Meterless Engine Node Runner - H-MEM, Scout Intent, Markovian.
 *
 * Loads the real engine modules shipped in Nightshift.app (browser-style IIFEs
 * that attach to window.RT) into a vm sandbox and exposes their public
 * functions as JSON operations. Nothing here re-implements engine logic; the
 * only shims are the host services the engines expect from Nightshift:
 *   RT.storage   file-backed (H-MEM durable tier)
 *   RT.memory    audit ledger collector
 *   RT.data      setpoints (H-MEM confidence floor)
 *
 * Input (stdin JSON): { engine, op, args, engineDir, storeFile }
 * Output (stdout JSON): { ok, engine, op, result, audit }
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILES = { scout: 'scout-intents.js', hmem: 'hmem.js', markovian: 'markovian.js' };

function loadEngine(engine, engineDir, storeFile) {
  const file = path.join(engineDir, FILES[engine]);
  if (!fs.existsSync(file)) throw new Error(`engine file not found: ${file}`);
  const audit = [];
  const RT = {};
  let store = {};
  if (storeFile && fs.existsSync(storeFile)) {
    try { store = JSON.parse(fs.readFileSync(storeFile, 'utf8')); } catch (_) { store = {}; }
  }
  RT.storage = {
    load: async (key, dflt) => (key in store ? store[key] : dflt),
    save: (key, val) => {
      store[key] = val;
      if (storeFile) {
        fs.mkdirSync(path.dirname(storeFile), { recursive: true });
        fs.writeFileSync(storeFile, JSON.stringify(store));
      }
    },
  };
  RT.memory = { ledger: (action, subject, details) => audit.push({ action, subject, details }) };
  RT.data = { setpoints: { hmemMinConfidence: 0.6 } };
  const sandbox = {
    window: { RT }, console, performance,
    setTimeout: (fn) => setImmediate(fn), clearTimeout, // H-MEM persistSoon(): flush promptly
    Date, Math, JSON, Map, Set, Promise, Error,
  };
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(file, 'utf8'), sandbox, { filename: file });
  return { RT: sandbox.window.RT, audit };
}

const settle = () => new Promise((r) => setImmediate(() => setImmediate(r)));

async function handle(input) {
  const { engine, op, args = {}, engineDir, storeFile } = input;
  if (!FILES[engine]) throw new Error(`unknown engine: ${engine}`);
  const { RT, audit } = loadEngine(engine, engineDir, storeFile);
  let result;

  if (engine === 'scout') {
    if (op === 'detect') {
      const d = RT.detectIntent(args.text || '');
      result = { ...d, tierHint: RT.intentTierHint(d.mode), registrySize: RT.SCOUT_INTENTS.length };
    } else if (op === 'selftest') {
      result = { maxMs: RT.scoutSelfTest(), registrySize: RT.SCOUT_INTENTS.length };
    } else throw new Error(`unknown scout op: ${op}`);
  } else if (engine === 'hmem') {
    await RT.hmem.load();
    if (op === 'retrieve') {
      const hits = RT.hmem.retrieve({
        prompt: args.prompt, scope: args.scope, app: args.app || 'default', intent: args.intent || 'investigation',
        k: args.k || 3, minScore: args.minScore ?? 0.35, touch: args.touch !== false,
      });
      result = { hits: hits.map((h) => ({
        id: h.id, content: h.content, confidence: h.confidence, score: h.score, scope: h.scope, tags: h.tags,
        source: { kind: h.source && h.source.kind, model: h.source && h.source.model, receiptId: h.source && h.source.receiptId },
        timestamp: h.timestamp,
      })), reinjection: hits.length ? RT.hmem.reinjectionBlock(hits) : null };
    } else if (op === 'mine') {
      const rec = RT.hmem.mineAnswer({ ...args, answer: args.answer, prompt: args.prompt });
      await settle();
      result = { stored: !!rec, id: rec ? rec.id : null, domain: rec ? rec.domain : null, entities: rec ? rec.entities : [] };
    } else if (op === 'feedback') {
      if (args.kind === 'wrong') RT.hmem.noteWrong(args.id); else RT.hmem.noteHelpful(args.id);
      await settle();
      result = { ok: true };
    } else if (op === 'stats') {
      result = RT.hmem.stats();
    } else if (op === 'clear') {
      RT.hmem.clearAll();
      result = { cleared: true };
    } else throw new Error(`unknown hmem op: ${op}`);
  } else if (engine === 'markovian') {
    const M = RT.markovian;
    if (op === 'validate') {
      result = { config: M.validateForRun(M.clampConfig(args.config || {}), { contextWindow: args.contextWindow }) };
    } else if (op === 'build_prompt') {
      result = { prompt: M.buildPrompt({ mode: args.mode || 'RESEARCH', isFirst: !!args.isFirst, prompt: args.prompt,
        carryover: args.carryover, overlapText: args.overlapText, memoryContext: args.memoryContext }) };
    } else if (op === 'extract_carryover') {
      result = await M.extractCarryover({ chunkText: args.chunkText, prevCarryover: args.prevCarryover, budgetTokens: args.budgetTokens });
    } else if (op === 'detect_marker') {
      result = { marker: M.detectMarker(args.text), cleaned: M.cleanContent(args.text) };
    } else if (op === 'efficiency') {
      result = M.computeRunEfficiency(args.chunks || [], M.clampConfig(args.config || {}));
    } else if (op === 'constants') {
      result = { BOUNDS: M.BOUNDS, DEFAULT_CONFIG: M.DEFAULT_CONFIG, FINAL_MARKERS: M.FINAL_MARKERS, STATE_MARKERS: M.STATE_MARKERS };
    } else throw new Error(`unknown markovian op: ${op}`);
  }
  return { ok: true, engine, op, result, audit };
}

(async () => {
  const chunks = [];
  for await (const c of process.stdin) chunks.push(c);
  try {
    const out = await handle(JSON.parse(Buffer.concat(chunks).toString('utf8')));
    process.stdout.write(JSON.stringify(out));
  } catch (err) {
    const detail = err && err.code ? ` [${err.code}]` : '';
    process.stderr.write(JSON.stringify({ ok: false, error: (err.message || String(err)) + detail, code: err.code || null }));
    process.exit(1);
  }
})();
