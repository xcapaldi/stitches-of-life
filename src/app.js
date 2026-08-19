/**
 * Application wiring: form -> hat plan -> simulation -> chart -> exports.
 */

import { CROWN_STYLES, CUFF_STYLES, computeHatPlan } from './hat.js';
import { buildLayout } from './grid.js';
import { buildLineage, buildTopology } from './topology.js';
import { RULE_PRESETS_1D, RULE_PRESETS_2D, parseRule } from './rules.js';
import { SEED_TYPES } from './seeds.js';
import { Simulation } from './sim.js';
import { ChartView } from './render.js';
import { buildInstructions, buildProject, decodeCells, readProject } from './export.js';

const $ = (id) => document.getElementById(id);

const HAT_FIELDS = [
  'headCircumference',
  'earToEar',
  'ease',
  'stitchGauge',
  'rowGauge',
  'cuffInches',
  'ribKnit',
  'ribPurl',
];
const META_FIELDS = ['knitBy', 'knitFor', 'date', 'yarn', 'needles'];

const app = {
  plan: null,
  layout: null,
  sim: null,
  view: null,
  playing: false,
  lastFrame: 0,
  accumulator: 0,
};

/* ------------------------------------------------------------------ inputs */

function fillSelect(select, entries, value) {
  select.innerHTML = '';
  for (const entry of entries) {
    const option = document.createElement('option');
    option.value = entry.value;
    option.textContent = entry.label;
    select.append(option);
  }
  if (value !== undefined) select.value = value;
}

function populateSelects() {
  fillSelect(
    $('cuffStyle'),
    Object.entries(CUFF_STYLES).map(([value, style]) => ({ value, label: style.label })),
    'ribbed',
  );
  fillSelect(
    $('crownStyle'),
    Object.entries(CROWN_STYLES).map(([value, style]) => ({ value, label: style.label })),
    'round',
  );
  fillSelect(
    $('rulePreset2d'),
    [{ value: '', label: 'Custom' }, ...RULE_PRESETS_2D.map((p) => ({ value: p.rule, label: p.name }))],
    'B3/S23',
  );
  fillSelect(
    $('rulePreset1d'),
    [{ value: '', label: 'Custom' }, ...RULE_PRESETS_1D.map((p) => ({ value: String(p.rule), label: p.name }))],
    '30',
  );
  refreshSeedOptions();
}

function refreshSeedOptions() {
  const mode = $('simMode').value;
  const current = $('seedType').value;
  const available = SEED_TYPES.filter((seed) => seed.modes.includes(mode));
  fillSelect(
    $('seedType'),
    available.map((seed) => ({ value: seed.id, label: seed.label })),
  );
  $('seedType').value = available.some((seed) => seed.id === current) ? current : available[0].id;
}

function readHatParams() {
  const params = {};
  for (const id of HAT_FIELDS) params[id] = Number($(id).value);
  params.cuffStyle = $('cuffStyle').value;
  params.crownStyle = $('crownStyle').value;
  params.cuffInMap = $('cuffInMap').checked;
  params.crownInMap = $('crownInMap').checked;
  params.stitchMode = $('stitchMode').value;
  return params;
}

function readSimOptions() {
  return {
    mode: $('simMode').value,
    rule2d: $('rule2d').value,
    rule1d: Number($('rule1d').value),
    direction: $('direction1d').value,
    seedType: $('seedType').value,
    seedDensity: Number($('seedDensity').value),
    rngSeed: Number($('rngSeed').value),
  };
}

function readMeta() {
  const meta = {};
  for (const id of META_FIELDS) meta[id] = $(id).value;
  return meta;
}

function writeParams(params = {}, simOptions = {}, meta = {}) {
  for (const id of HAT_FIELDS) if (params[id] !== undefined) $(id).value = params[id];
  if (params.cuffStyle) $('cuffStyle').value = params.cuffStyle;
  if (params.crownStyle) $('crownStyle').value = params.crownStyle;
  if (params.stitchMode) $('stitchMode').value = params.stitchMode;
  if (params.cuffInMap !== undefined) $('cuffInMap').checked = params.cuffInMap;
  if (params.crownInMap !== undefined) $('crownInMap').checked = params.crownInMap;

  if (simOptions.mode) $('simMode').value = simOptions.mode;
  refreshSeedOptions();
  if (simOptions.rule2d) $('rule2d').value = simOptions.rule2d;
  if (simOptions.rule1d !== undefined) $('rule1d').value = simOptions.rule1d;
  if (simOptions.direction) $('direction1d').value = simOptions.direction;
  if (simOptions.seedType) $('seedType').value = simOptions.seedType;
  if (simOptions.seedDensity !== undefined) $('seedDensity').value = simOptions.seedDensity;
  if (simOptions.rngSeed !== undefined) $('rngSeed').value = simOptions.rngSeed;

  for (const id of META_FIELDS) if (meta[id] !== undefined) $(id).value = meta[id];
  syncModePanels();
}

function syncModePanels() {
  const mode = $('simMode').value;
  $('panel2d').hidden = mode !== '2d';
  $('panel1d').hidden = mode !== '1d';
}

/* ------------------------------------------------------------------- build */

function rebuild({ keepCamera = true } = {}) {
  const plan = computeHatPlan(readHatParams());
  const layout = buildLayout(plan);
  const topology = buildTopology(layout);
  const lineage = buildLineage(layout);
  const sim = new Simulation({ plan, layout, topology, lineage, options: readSimOptions() });

  app.plan = plan;
  app.layout = layout;
  app.sim = sim;

  const hadCamera = keepCamera && app.view && app.view.plan;
  const camera = hadCamera ? { ...app.view.camera } : null;
  app.view.setPlan(plan, layout);
  if (camera) app.view.camera = camera;
  else app.view.fit();

  refresh();
}

function reseed() {
  app.sim.setOptions(readSimOptions());
  app.sim.reset();
  refresh();
}

/** Rule and direction changes only affect what comes next, so drop the future. */
function reconfigure() {
  app.sim.setOptions(readSimOptions());
  app.sim.truncate();
  refresh();
}

/* ------------------------------------------------------------------ output */

function refresh() {
  const sim = app.sim;
  app.view.setState(sim.state);
  app.view.requestDraw();

  const slider = $('genSlider');
  const reachable = Number.isFinite(sim.maxGeneration) ? sim.maxGeneration : sim.lastGeneration;
  slider.max = String(Math.max(reachable, sim.lastGeneration, sim.generation));
  slider.value = String(sim.generation);

  $('status').textContent = sim.status();
  $('btnPlay').textContent = app.playing ? '❚❚' : '▶';
  drawTimeline();
  drawStats();
}

function drawStats() {
  const { derived, params } = app.plan;
  const inMapRows = Array.from(app.layout.inMap).filter(Boolean).length;
  const rows = [
    ['C — body stitches', derived.bodyStitches],
    ['D — cuff stitches', derived.cuffStitches],
    ['E — body length', `${derived.bodyLength.toFixed(2)}"`],
    ['Cuff rounds', derived.cuffRows],
    ['Body rounds', derived.bodyRows],
    ['Crown rounds', derived.crownRows],
    ['Total rounds', derived.totalRows],
    ['Rounds in the map', inMapRows],
    ['Stitches in the map', derived.totalStitches.toLocaleString()],
    ['Finished circumference', `${derived.finishedCircumference.toFixed(2)}"`],
    ['Finished height', `${derived.finishedHeight.toFixed(2)}"`],
    ['Gauge', `${params.stitchGauge} st × ${params.rowGauge} rnd / in`],
  ];
  $('stats').innerHTML = rows
    .map(([term, value]) => `<dt>${term}</dt><dd>${value}</dd>`)
    .join('');
}

function drawTimeline() {
  const canvas = $('timeline');
  const dpr = devicePixelRatio || 1;
  const width = canvas.clientWidth || 220;
  const height = canvas.clientHeight || 34;
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  const pops = app.sim.populations;
  const peak = Math.max(1, ...pops);
  const step = width / Math.max(1, pops.length);
  const styles = getComputedStyle(document.body);
  ctx.fillStyle = styles.getPropertyValue('--muted').trim() || '#888';
  for (let i = 0; i < pops.length; i += 1) {
    const h = (pops[i] / peak) * (height - 4);
    ctx.fillRect(i * step, height - h - 2, Math.max(1, step - 0.5), h);
  }
  ctx.fillStyle = styles.getPropertyValue('--accent').trim() || '#b4573a';
  ctx.fillRect(app.sim.generation * step, 0, Math.max(1.5, step), height);
}

/* ---------------------------------------------------------------- playback */

function setPlaying(playing) {
  app.playing = playing;
  $('btnPlay').textContent = playing ? '❚❚' : '▶';
  if (playing) {
    app.lastFrame = performance.now();
    app.accumulator = 0;
    requestAnimationFrame(tick);
  }
}

function tick(now) {
  if (!app.playing) return;
  const dt = Math.min(0.25, (now - app.lastFrame) / 1000);
  app.lastFrame = now;
  app.accumulator += dt * Number($('speed').value);
  let steps = 0;
  while (app.accumulator >= 1 && steps < 200) {
    app.accumulator -= 1;
    steps += 1;
    if (!app.sim.stepForward()) {
      setPlaying(false);
      refresh();
      return;
    }
    if (app.sim.cycle) {
      setPlaying(false);
      break;
    }
  }
  if (steps) refresh();
  if (app.playing) requestAnimationFrame(tick);
}

/* ----------------------------------------------------------------- exports */

function download(filename, content, type) {
  const blob = content instanceof Blob ? content : new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function slug() {
  const who = $('knitFor').value.trim() || 'hat';
  return who.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'hat';
}

function describeSimulation() {
  const options = app.sim.options;
  if (options.mode === '1d') {
    return `1D rule ${options.rule1d}, first generation at the ${options.direction === 'up' ? 'cuff' : 'crown'}, generation ${app.sim.generation}`;
  }
  const rule = parseRule(options.rule2d);
  return `2D rule ${rule ? rule.text : options.rule2d}, generation ${app.sim.generation}`;
}

function exportInstructions() {
  const text = buildInstructions({
    plan: app.plan,
    layout: app.layout,
    state: app.sim.state,
    meta: readMeta(),
    options: { simulation: describeSimulation() },
  });
  download(`${slug()}-pattern.md`, text, 'text/markdown;charset=utf-8');
}

function exportChart() {
  const canvas = app.view.toCanvas(120);
  canvas.toBlob((blob) => {
    if (blob) download(`${slug()}-chart.png`, blob, 'image/png');
  });
}

function exportProject() {
  const project = buildProject({
    plan: app.plan,
    state: app.sim.state,
    simOptions: app.sim.options,
    generation: app.sim.generation,
    meta: readMeta(),
  });
  download(`${slug()}-project.json`, JSON.stringify(project, null, 2), 'application/json');
}

async function importProject(file) {
  try {
    const data = readProject(await file.text());
    writeParams(data.hat || {}, data.simulation || {}, data.meta || {});
    rebuild({ keepCamera: false });

    const target = Number(data.generation) || 0;
    app.sim.goto(target);

    // Everything is deterministic, so replaying the seed usually reproduces the
    // saved design exactly. Hand-edited designs will not match; paste them in.
    const saved = decodeCells(data.cells, app.layout.total);
    const current = app.sim.state;
    let same = saved.length === current.length;
    for (let i = 0; same && i < saved.length; i += 1) same = saved[i] === current[i];
    if (!same) {
      current.set(saved);
      app.sim.refreshCurrent();
    }
    refresh();
  } catch (error) {
    alert(`Could not open that project: ${error.message}`);
  }
}

/* ------------------------------------------------------------------ events */

function debounce(fn, wait = 150) {
  let handle = null;
  return (...args) => {
    clearTimeout(handle);
    handle = setTimeout(() => fn(...args), wait);
  };
}

function wire() {
  const rebuildSoon = debounce(() => rebuild());

  for (const id of HAT_FIELDS) $(id).addEventListener('input', rebuildSoon);
  for (const id of ['cuffInMap', 'crownInMap', 'crownStyle']) {
    $(id).addEventListener('change', () => rebuild());
  }
  // Colourwork or texture only changes how the pattern is written up, so there
  // is no reason to throw the design away.
  $('stitchMode').addEventListener('change', () => {
    app.plan.params.stitchMode = $('stitchMode').value;
  });
  $('cuffStyle').addEventListener('change', () => {
    $('cuffInches').value = CUFF_STYLES[$('cuffStyle').value].defaultInches;
    rebuild();
  });

  $('simMode').addEventListener('change', () => {
    syncModePanels();
    refreshSeedOptions();
    reseed();
  });
  $('rulePreset2d').addEventListener('change', (event) => {
    if (!event.target.value) return;
    $('rule2d').value = event.target.value;
    reconfigure();
  });
  $('rulePreset1d').addEventListener('change', (event) => {
    if (!event.target.value) return;
    $('rule1d').value = event.target.value;
    reconfigure();
  });
  $('rule2d').addEventListener('input', () => {
    const ok = Boolean(parseRule($('rule2d').value));
    $('rule2d').style.borderColor = ok ? '' : 'var(--accent)';
    if (ok) {
      $('rulePreset2d').value = RULE_PRESETS_2D.some((p) => p.rule === $('rule2d').value)
        ? $('rule2d').value
        : '';
      reconfigure();
    }
  });
  $('rule1d').addEventListener('input', () => reconfigure());
  $('direction1d').addEventListener('change', () => reseed());
  for (const id of ['seedType', 'seedDensity', 'rngSeed']) {
    $(id).addEventListener('change', () => reseed());
  }
  $('btnReseed').addEventListener('click', () => {
    $('rngSeed').value = String(Math.floor(Math.random() * 100000));
    reseed();
  });

  for (const id of ['showGrid', 'showGlyphs', 'showSections']) {
    $(id).addEventListener('change', () => {
      app.view.setOptions({
        showGrid: $('showGrid').checked,
        showGlyphs: $('showGlyphs').checked,
        showSections: $('showSections').checked,
      });
      app.view.requestDraw();
    });
  }
  for (const id of ['colorMC', 'colorCC']) {
    $(id).addEventListener('input', () => {
      app.view.setOptions({ colorMC: $('colorMC').value, colorCC: $('colorCC').value });
      app.view.requestDraw();
    });
  }
  $('paintMode').addEventListener('change', () => {
    app.view.paintMode = $('paintMode').value;
    document.querySelector('.stage').classList.toggle('panning', app.view.paintMode === 'pan');
  });
  $('btnFit').addEventListener('click', () => {
    app.view.fit();
    app.view.requestDraw();
  });

  $('btnReset').addEventListener('click', () => {
    setPlaying(false);
    app.sim.goto(0);
    refresh();
  });
  $('btnBack').addEventListener('click', () => {
    setPlaying(false);
    app.sim.stepBackward();
    refresh();
  });
  $('btnForward').addEventListener('click', () => {
    setPlaying(false);
    app.sim.stepForward();
    refresh();
  });
  $('btnRun').addEventListener('click', () => {
    setPlaying(false);
    app.sim.runAhead(100);
    refresh();
  });
  $('btnPlay').addEventListener('click', () => setPlaying(!app.playing));
  $('genSlider').addEventListener('input', (event) => {
    setPlaying(false);
    app.sim.goto(Number(event.target.value));
    refresh();
  });

  const scrub = (event) => {
    if (event.buttons === 0 && event.type === 'pointermove') return;
    const rect = $('timeline').getBoundingClientRect();
    const fraction = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
    setPlaying(false);
    app.sim.goto(Math.round(fraction * app.sim.lastGeneration));
    refresh();
  };
  $('timeline').addEventListener('pointerdown', scrub);
  $('timeline').addEventListener('pointermove', scrub);

  $('btnExportMd').addEventListener('click', exportInstructions);
  $('btnExportPng').addEventListener('click', exportChart);
  $('btnExportJson').addEventListener('click', exportProject);
  $('fileImport').addEventListener('change', (event) => {
    const file = event.target.files[0];
    if (file) importProject(file);
    event.target.value = '';
  });

  window.addEventListener('resize', debounce(() => app.view.requestDraw(), 80));

  window.addEventListener('keydown', (event) => {
    const tag = document.activeElement && document.activeElement.tagName;
    if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return;
    if (event.key === ' ') {
      event.preventDefault();
      setPlaying(!app.playing);
    } else if (event.key === 'ArrowRight') {
      setPlaying(false);
      app.sim.stepForward();
      refresh();
    } else if (event.key === 'ArrowLeft') {
      setPlaying(false);
      app.sim.stepBackward();
      refresh();
    } else if (event.key === 'r' || event.key === 'R') {
      setPlaying(false);
      app.sim.goto(0);
      refresh();
    } else if (event.key === 'f' || event.key === 'F') {
      app.view.fit();
      app.view.requestDraw();
    }
  });
}

/* -------------------------------------------------------------------- boot */

/** Let the chart pick up the page's light or dark palette. */
function applyTheme() {
  const styles = getComputedStyle(document.body);
  const value = (name, fallback) => styles.getPropertyValue(name).trim() || fallback;
  app.view.setOptions({
    background: value('--bg', '#ffffff'),
    accent: value('--accent', '#b4573a'),
    textColor: value('--muted', '#6b7480'),
  });
}

function start() {
  populateSelects();
  syncModePanels();
  $('date').value = new Date().toISOString().slice(0, 10);

  app.view = new ChartView($('chart'), {
    colorMC: $('colorMC').value,
    colorCC: $('colorCC').value,
  });
  applyTheme();
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      applyTheme();
      app.view.requestDraw();
      drawTimeline();
    });
  }
  app.view.onPaint = (cell, value) => {
    if (app.sim.editCell(cell, value)) refresh();
  };

  wire();
  rebuild({ keepCamera: false });
}

start();
