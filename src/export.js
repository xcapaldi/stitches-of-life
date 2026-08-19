/**
 * Turning a generation into something a knitter can work from.
 *
 * The chart is written in knitting order: round 1 is the cast-on round and
 * every round is listed with the stitches that exist once it has been worked,
 * so a decrease round is listed at its finished stitch count.
 */

const SYMBOLS = { off: '.', on: '#' };

/* ------------------------------------------------------------------ state */

/** Compact run-length text: counts of alternating runs starting with zeros. */
export function encodeCells(state) {
  const runs = [];
  let current = 0;
  let count = 0;
  for (let i = 0; i < state.length; i += 1) {
    const value = state[i] ? 1 : 0;
    if (value === current) {
      count += 1;
    } else {
      runs.push(count);
      current = value;
      count = 1;
    }
  }
  runs.push(count);
  return runs.join(',');
}

export function decodeCells(text, total) {
  const state = new Uint8Array(total);
  if (!text) return state;
  let at = 0;
  let value = 0;
  for (const part of String(text).split(',')) {
    const n = Number(part);
    if (!Number.isFinite(n) || n < 0) break;
    if (value) state.fill(1, at, Math.min(total, at + n));
    at += n;
    value ^= 1;
    if (at >= total) break;
  }
  return state;
}

/* ------------------------------------------------------------------ rounds */

/** Runs of like stitches in one round, in the order they are worked. */
export function roundRuns(state, layout, row) {
  const base = layout.offsets[row];
  const width = layout.widths[row];
  const runs = [];
  for (let i = 0; i < width; i += 1) {
    const value = state[base + i] ? 1 : 0;
    const last = runs[runs.length - 1];
    if (last && last.value === value) last.count += 1;
    else runs.push({ value, count: 1 });
  }
  return runs;
}

export function describeRound(state, layout, row, stitchMode) {
  const runs = roundRuns(state, layout, row);
  const width = layout.widths[row];
  if (runs.length === 1) {
    const solid = runs[0].value;
    if (stitchMode === 'texture') return solid ? `P${width}` : `K${width}`;
    return `${width} ${solid ? 'CC' : 'MC'}`;
  }
  if (stitchMode === 'texture') {
    return runs.map((run) => `${run.value ? 'P' : 'K'}${run.count}`).join(', ');
  }
  return runs.map((run) => `${run.count} ${run.value ? 'CC' : 'MC'}`).join(', ');
}

/** A monospace picture of the chart, top round first. */
export function asciiChart(plan, layout, state) {
  const lines = [];
  let maxWidth = 0;
  for (let r = 0; r < layout.rowCount; r += 1) maxWidth = Math.max(maxWidth, layout.widths[r]);
  const numberWidth = String(layout.rowCount).length;

  for (let r = layout.rowCount - 1; r >= 0; r -= 1) {
    const width = layout.widths[r];
    const base = layout.offsets[r];
    let cells = '';
    // Stitch 0 is worked first and sits at the right-hand edge.
    for (let i = width - 1; i >= 0; i -= 1) cells += state[base + i] ? SYMBOLS.on : SYMBOLS.off;
    const pad = ' '.repeat(Math.floor((maxWidth - width) / 2));
    lines.push(`${String(r + 1).padStart(numberWidth)} ${pad}${cells}`);
  }
  return lines.join('\n');
}

/* ------------------------------------------------------------ instructions */

const fmt = (n, digits = 2) => {
  const rounded = Number(n.toFixed(digits));
  return String(rounded);
};

function cuffInstructions(plan) {
  const { params, derived, cuff } = plan;
  const lines = [];
  lines.push(
    `Cast on **${derived.cuffStitches} stitches** (D) onto the smaller circular needle. Join, being careful not to twist.`,
  );
  if (params.cuffStyle === 'ribbed') {
    lines.push(
      `Work K${params.ribKnit}/P${params.ribPurl} ribbing every round for ${fmt(params.cuffInches)}" — ${derived.cuffRows} rounds (rounds 1–${derived.cuffRows}).`,
    );
  } else {
    lines.push(
      `Knit every round for ${fmt(params.cuffInches)}" — ${derived.cuffRows} rounds (rounds 1–${derived.cuffRows}). ${cuff.note}`,
    );
  }
  if (!params.cuffInMap) {
    lines.push('The cuff is not part of the charted design; work it plain.');
  }
  return lines;
}

function bodyInstructions(plan) {
  const { params, derived } = plan;
  const increase = derived.bodyStitches - derived.cuffStitches;
  const firstBodyRound = derived.cuffRows + 1;
  const lastBodyRound = derived.cuffRows + derived.bodyRows;
  const lines = [];
  lines.push(
    `Round ${firstBodyRound} (increase round): increase evenly to **${derived.bodyStitches} stitches** (C)` +
      `${increase > 0 ? `, adding ${increase} stitch${increase === 1 ? '' : 'es'}` : ''}. Change to the larger circular needle.`,
  );
  if (params.cuffStyle === 'hemmed') {
    lines.push(`Round ${firstBodyRound + 1}: purl one round. This is the fold line for the hem.`);
  } else if (params.cuffStyle === 'rolled') {
    lines.push('Mark the increase round with a safety pin so you can find it again.');
  }
  lines.push(
    `Work the chart from round ${firstBodyRound} through round ${lastBodyRound} — ${fmt(derived.workedBodyInches)}"` +
      `${params.cuffStyle === 'ribbed' ? ' (E less 1")' : ' (E)'}, ${derived.bodyRows} rounds.`,
  );
  return lines;
}

function crownInstructions(plan) {
  const { derived, crown, params } = plan;
  const firstCrownRound = derived.cuffRows + derived.bodyRows + 1;
  const lines = [];
  lines.push(
    `Round ${firstCrownRound}: decrease to ${derived.crownStartStitches} stitches (a multiple of ${crown.multiple})` +
      ` and place a marker after each ${crown.multiple === 8 ? 'eighth' : 'quarter'} of the round.`,
  );
  const decreaseRounds = plan.rows.filter((row) => row.kind === 'decrease').length;
  if (params.crownStyle === 'pointed') {
    lines.push(`Round 1 of the repeat: ${crown.shaping} (${crown.markers} stitches decreased).`);
    lines.push('Rounds 2, 3 and 4 of the repeat: knit.');
  } else {
    lines.push(
      `Round 1 of the repeat: ${crown.shaping} (${crown.markers * crown.decreasesPerMarker} stitches decreased).`,
    );
    lines.push('Round 2 of the repeat: knit.');
  }
  lines.push(
    `Repeat the sequence until 8 stitches remain — ${decreaseRounds} decrease rounds, ${derived.crownRows} crown rounds in all (rounds ${firstCrownRound}–${plan.rows.length}).`,
  );
  lines.push('Break the yarn, thread it through the remaining 8 stitches, pull tight and fasten off on the inside.');
  return lines;
}

/** Collapse identical consecutive rounds so long plain stretches stay readable. */
function roundByRound(plan, layout, state) {
  const stitchMode = plan.params.stitchMode;
  const { ribKnit, ribPurl } = plan.params;
  const entries = [];
  for (let r = 0; r < layout.rowCount; r += 1) {
    const row = plan.rows[r];
    // A ribbed cuff left out of the map is ribbing, whatever the two states
    // mean in the rest of the hat.
    const plainRib = plan.cuff.ribbed && row.section === 'cuff' && !row.inMap;
    const text = plainRib
      ? `*K${ribKnit}, P${ribPurl}* to the end of the round`
      : describeRound(state, layout, r, stitchMode);
    const shaping =
      row.kind === 'decrease'
        ? `decrease round, −${row.decreases} sts`
        : row.kind === 'adjust'
          ? `adjust to ${row.width} sts, −${row.decreases} sts`
          : row.kind === 'increase'
            ? 'increase round'
            : row.kind === 'turn'
              ? 'purl round (hem fold)'
              : row.kind === 'cast-on'
                ? 'cast-on round'
                : '';
    const key = `${row.width}|${shaping}|${text}`;
    const last = entries[entries.length - 1];
    if (last && last.key === key) last.to = r + 1;
    else entries.push({ key, from: r + 1, to: r + 1, width: row.width, shaping, text });
  }

  return entries.map((entry) => {
    const label = entry.from === entry.to ? `Rnd ${entry.from}` : `Rnds ${entry.from}–${entry.to}`;
    const meta = [`${entry.width} sts`];
    if (entry.shaping) meta.unshift(entry.shaping);
    return `- **${label}** (${meta.join(', ')}): ${entry.text}`;
  });
}

/**
 * Full pattern as markdown.
 *
 * meta: { knitBy, knitFor, date, yarn, needles }
 * options: { includeChart, includeRounds, simulation }
 */
export function buildInstructions({ plan, layout, state, meta = {}, options = {} }) {
  const { params, derived } = plan;
  const includeChart = options.includeChart !== false;
  const includeRounds = options.includeRounds !== false;
  const colorwork = params.stitchMode === 'colorwork';

  const out = [];
  out.push('# Hats That Fit');
  out.push('');
  out.push('Generated by Stitches of Life. Hat arithmetic after the worksheet by Nancy Lindberg.');
  out.push('');
  out.push('| | |');
  out.push('|---|---|');
  out.push(`| Knit by | ${meta.knitBy || ''} |`);
  out.push(`| Knit for | ${meta.knitFor || ''} |`);
  out.push(`| Date | ${meta.date || ''} |`);
  out.push(`| Yarn | ${meta.yarn || ''} |`);
  out.push(`| Needles | ${meta.needles || ''} |`);
  out.push(`| Gauge | ${fmt(params.stitchGauge)} sts/inch, ${fmt(params.rowGauge)} rounds/inch |`);
  out.push('');

  out.push('## Measurements');
  out.push('');
  out.push(`- **A** (thickest part of the head above the ears): ${fmt(params.headCircumference)}"`);
  out.push(`- **B** (ear lobe to ear lobe over the top): ${fmt(params.earToEar)}"`);
  out.push(`- **C** (body stitches): ${derived.bodyStitches}`);
  out.push(`- **D** (cuff stitches): ${derived.cuffStitches}`);
  out.push(`- **E** (body length from the increase round): ${fmt(derived.bodyLength)}"`);
  out.push('');

  out.push('## Calculations');
  out.push('');
  out.push(
    `- ${fmt(params.headCircumference)}" (A) − ${fmt(params.ease)}" for a custom fit = ${fmt(derived.inchesAround)}" around`,
  );
  out.push(
    `- ${fmt(derived.inchesAround)}" × ${fmt(params.stitchGauge)} sts/inch = **${derived.bodyStitches} stitches** (C)`,
  );
  out.push(
    `- C − 10% of C = **${derived.cuffStitches} stitches** (D)` +
      (params.cuffStyle === 'ribbed'
        ? `, adjusted to a multiple of ${derived.ribRepeat} for the ribbing`
        : ''),
  );
  out.push(`- ${fmt(params.earToEar)}" (B) ÷ 4 = ${fmt(derived.crownLength)}" + 1" = **${fmt(derived.bodyLength)}"** (E)`);
  out.push('');
  out.push(
    `Finished hat: ${fmt(derived.finishedCircumference)}" around, ${fmt(derived.finishedHeight)}" tall, ` +
      `${derived.totalRows} rounds, ${derived.totalStitches.toLocaleString()} stitches in all.`,
  );
  out.push('');

  out.push('## Design');
  out.push('');
  out.push(`- Cuff: ${plan.cuff.label}${params.cuffStyle === 'ribbed' ? ` (K${params.ribKnit}/P${params.ribPurl})` : ''}`);
  out.push(`- Crown: ${plan.crown.label}`);
  out.push(
    `- Worked as: ${colorwork ? 'stranded colourwork — MC is the main colour, CC the contrast' : 'texture — knit and purl on one colour'}`,
  );
  out.push(`- Cuff rounds ${params.cuffInMap ? 'are' : 'are not'} part of the charted design.`);
  out.push(`- Crown rounds ${params.crownInMap ? 'are' : 'are not'} part of the charted design.`);
  if (options.simulation) out.push(`- Pattern source: ${options.simulation}`);
  out.push('');

  out.push('## Working the hat');
  out.push('');
  out.push('### Cuff');
  out.push('');
  for (const line of cuffInstructions(plan)) out.push(`${line}`);
  out.push('');
  out.push('### Body');
  out.push('');
  for (const line of bodyInstructions(plan)) out.push(`${line}`);
  out.push('');
  out.push('### Crown');
  out.push('');
  for (const line of crownInstructions(plan)) out.push(`${line}`);
  out.push('');
  out.push(
    'Crown decreases and the charted design are worked at the same time. Where a decrease eats into the chart, ' +
      'work the decrease in whichever colour keeps the line of the motif.',
  );
  out.push('');

  if (includeRounds) {
    out.push('## Round by round');
    out.push('');
    out.push(
      colorwork
        ? 'Stitches are listed in the order they are worked, starting at the beginning-of-round marker. All stitches are knitted; only the colour changes.'
        : 'Stitches are listed in the order they are worked, starting at the beginning-of-round marker.',
    );
    out.push('');
    for (const line of roundByRound(plan, layout, state)) out.push(line);
    out.push('');
  }

  if (includeChart) {
    out.push('## Chart');
    out.push('');
    out.push(
      `Read each round from right to left, bottom round first. \`${SYMBOLS.off}\` = ${colorwork ? 'MC' : 'knit'}, ` +
        `\`${SYMBOLS.on}\` = ${colorwork ? 'CC' : 'purl'}. Rounds are centred on each other, so the taper is the crown shaping.`,
    );
    out.push('');
    out.push('```');
    out.push(asciiChart(plan, layout, state));
    out.push('```');
    out.push('');
  }

  return out.join('\n');
}

/* ---------------------------------------------------------------- project */

export const PROJECT_VERSION = 2;

export function buildProject({ plan, state, simOptions, generation, meta }) {
  return {
    format: 'stitches-of-life',
    version: PROJECT_VERSION,
    savedAt: new Date().toISOString(),
    meta,
    hat: plan.params,
    simulation: simOptions,
    generation,
    cells: encodeCells(state),
  };
}

export function readProject(text) {
  const data = typeof text === 'string' ? JSON.parse(text) : text;
  if (!data || data.format !== 'stitches-of-life') {
    throw new Error('Not a Stitches of Life project file.');
  }
  return data;
}
