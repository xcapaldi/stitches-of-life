/**
 * Hat geometry.
 *
 * Turns body measurements + gauge into a stitch map: an ordered list of rounds,
 * each with the number of stitches that exist once that round has been worked.
 *
 * The arithmetic follows the "Hats That Fit" worksheet by Nancy Lindberg:
 *
 *   inches around = A - 1            (A = head circumference above the ears)
 *   C = inches around x gauge        (body stitches)
 *   D = C - 10% of C                 (cuff stitches)
 *   length = B / 4                   (B = ear lobe to ear lobe over the top)
 *   E = length + 1                   (body length from the increase round)
 *
 * A knitted stitch is wider than it is tall. The wale:course ratio depends on
 * yarn, needles and knitter and generally falls between 1:1 and 1:1.85
 * (stitches:rows), so row gauge is a separate input rather than a constant.
 */

export const CUFF_STYLES = {
  hemmed: {
    label: 'Hemmed',
    defaultInches: 3,
    ribbed: false,
    turningRound: true,
    bodyDelta: 0,
    note: 'Turns under to the inside of the hat. Knit every round.',
  },
  rolled: {
    label: 'Rolled',
    defaultInches: 3,
    ribbed: false,
    turningRound: false,
    bodyDelta: 0,
    note: 'Rolls to the outside revealing the purl side. Knit every round.',
  },
  ribbed: {
    label: 'Ribbed',
    defaultInches: 4.5,
    ribbed: true,
    turningRound: false,
    bodyDelta: -1,
    note: 'Worked in ribbing; the body is then 1" shorter than E.',
  },
};

export const CROWN_STYLES = {
  square: {
    label: 'Square',
    markers: 4,
    decreasesPerMarker: 2,
    roundsPerRepeat: 2,
    multiple: 4,
    shaping: '*K2tog before marker, slip marker, K1, SSK*, repeat at each marker',
  },
  pointed: {
    label: 'Pointed',
    markers: 4,
    decreasesPerMarker: 1,
    roundsPerRepeat: 4,
    multiple: 4,
    shaping: '*K2tog before each marker*',
  },
  round: {
    label: 'Round',
    markers: 8,
    decreasesPerMarker: 1,
    roundsPerRepeat: 2,
    multiple: 8,
    shaping: '*K2tog before each marker*',
  },
};

/** Stitches left on the needles when the crown is finished and sewn shut. */
export const CROWN_FINAL_STITCHES = 8;

export const DEFAULT_PARAMS = {
  headCircumference: 22, // A, inches
  earToEar: 14, // B, inches
  stitchGauge: 5, // stitches per inch
  rowGauge: 7, // rows per inch
  ease: 1, // inches subtracted from A for a custom fit
  cuffStyle: 'ribbed',
  cuffInches: null, // null => the style's default
  ribKnit: 2,
  ribPurl: 2,
  crownStyle: 'round',
  cuffInMap: true, // do the cuff rounds take part in the simulation?
  crownInMap: true, // do the crown rounds take part in the simulation?
  stitchMode: 'colorwork', // 'colorwork' (MC/CC) or 'texture' (knit/purl)
};

const clampNumber = (value, min, max, fallback) => {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(max, Math.max(min, n));
};

/** Fill in defaults and clamp everything to values that produce a knittable hat. */
export function resolveParams(input = {}) {
  const p = { ...DEFAULT_PARAMS, ...input };
  const cuffStyle = CUFF_STYLES[p.cuffStyle] ? p.cuffStyle : DEFAULT_PARAMS.cuffStyle;
  const crownStyle = CROWN_STYLES[p.crownStyle] ? p.crownStyle : DEFAULT_PARAMS.crownStyle;
  return {
    headCircumference: clampNumber(p.headCircumference, 6, 40, DEFAULT_PARAMS.headCircumference),
    earToEar: clampNumber(p.earToEar, 4, 30, DEFAULT_PARAMS.earToEar),
    stitchGauge: clampNumber(p.stitchGauge, 1, 20, DEFAULT_PARAMS.stitchGauge),
    rowGauge: clampNumber(p.rowGauge, 1, 30, DEFAULT_PARAMS.rowGauge),
    ease: clampNumber(p.ease, -4, 4, DEFAULT_PARAMS.ease),
    cuffStyle,
    cuffInches:
      p.cuffInches === null || p.cuffInches === undefined || p.cuffInches === ''
        ? CUFF_STYLES[cuffStyle].defaultInches
        : clampNumber(p.cuffInches, 0.25, 12, CUFF_STYLES[cuffStyle].defaultInches),
    ribKnit: Math.round(clampNumber(p.ribKnit, 1, 8, DEFAULT_PARAMS.ribKnit)),
    ribPurl: Math.round(clampNumber(p.ribPurl, 1, 8, DEFAULT_PARAMS.ribPurl)),
    crownStyle,
    cuffInMap: Boolean(p.cuffInMap),
    crownInMap: Boolean(p.crownInMap),
    stitchMode: p.stitchMode === 'texture' ? 'texture' : 'colorwork',
  };
}

/**
 * Build the full round-by-round plan for a hat.
 *
 * Every entry of `rows` is one round, ordered as it is knitted: index 0 is the
 * cast-on round and the last entry is the final crown round. `width` is the
 * stitch count *after* the round is worked, so a decrease round is one stitch
 * narrower per decrease than the round below it.
 */
export function computeHatPlan(input = {}) {
  const params = resolveParams(input);
  const cuff = CUFF_STYLES[params.cuffStyle];
  const crown = CROWN_STYLES[params.crownStyle];

  const inchesAround = params.headCircumference - params.ease;
  const bodyStitches = Math.max(16, Math.round(inchesAround * params.stitchGauge)); // C

  const ribRepeat = params.ribKnit + params.ribPurl;
  let cuffStitches = Math.round(bodyStitches * 0.9); // D = C - 10% of C
  if (cuff.ribbed) {
    // The ribbing has to divide evenly into the round.
    cuffStitches = Math.max(ribRepeat, Math.round(cuffStitches / ribRepeat) * ribRepeat);
  }
  cuffStitches = Math.min(cuffStitches, bodyStitches);

  const crownLength = params.earToEar / 4; // "length" on the worksheet
  const bodyLength = crownLength + 1; // E
  const workedBodyInches = Math.max(0.5, bodyLength + cuff.bodyDelta);

  const cuffRows = Math.max(1, Math.round(params.cuffInches * params.rowGauge));
  const bodyRows = Math.max(2, Math.round(workedBodyInches * params.rowGauge));

  const rows = [];
  const push = (row) => {
    rows.push({ index: rows.length, ...row });
  };

  for (let r = 0; r < cuffRows; r += 1) {
    push({
      width: cuffStitches,
      section: 'cuff',
      kind: r === 0 ? 'cast-on' : cuff.ribbed ? 'rib' : 'plain',
      decreases: 0,
      inMap: params.cuffInMap,
    });
  }

  for (let r = 0; r < bodyRows; r += 1) {
    let kind = 'plain';
    if (r === 0) kind = 'increase';
    else if (r === 1 && cuff.turningRound) kind = 'turn';
    push({
      width: bodyStitches,
      section: 'body',
      kind,
      decreases: 0,
      inMap: true,
    });
  }

  // Crown. The first crown round brings the stitch count to a multiple of the
  // number of decrease points, then the decrease repeat runs until 8 remain.
  const adjusted = Math.floor(bodyStitches / crown.multiple) * crown.multiple;
  let live = bodyStitches;
  if (adjusted !== live && adjusted >= CROWN_FINAL_STITCHES) {
    push({
      width: adjusted,
      section: 'crown',
      kind: 'adjust',
      decreases: live - adjusted,
      inMap: params.crownInMap,
    });
    live = adjusted;
  }

  const decreasesPerRound = crown.markers * crown.decreasesPerMarker;
  let guard = 0;
  while (live > CROWN_FINAL_STITCHES && guard < 5000) {
    guard += 1;
    for (let step = 0; step < crown.roundsPerRepeat; step += 1) {
      if (live <= CROWN_FINAL_STITCHES) break;
      if (step === 0) {
        const next = Math.max(CROWN_FINAL_STITCHES, live - decreasesPerRound);
        push({
          width: next,
          section: 'crown',
          kind: 'decrease',
          decreases: live - next,
          inMap: params.crownInMap,
        });
        live = next;
      } else {
        push({ width: live, section: 'crown', kind: 'plain', decreases: 0, inMap: params.crownInMap });
      }
    }
  }

  const sectionRows = (name) => rows.filter((row) => row.section === name).length;
  const totalStitches = rows.reduce((sum, row) => sum + row.width, 0);

  return {
    params,
    cuff,
    crown,
    derived: {
      inchesAround,
      bodyStitches, // C
      cuffStitches, // D
      crownLength, // B / 4
      bodyLength, // E
      workedBodyInches,
      ribRepeat,
      cuffRows,
      bodyRows,
      crownRows: sectionRows('crown'),
      crownStartStitches: adjusted,
      finishedCircumference: bodyStitches / params.stitchGauge,
      cuffCircumference: cuffStitches / params.stitchGauge,
      finishedHeight: rows.length / params.rowGauge,
      totalRows: rows.length,
      totalStitches,
    },
    rows,
  };
}

/** True when a round is worked over the ribbing of a ribbed cuff. */
export function isRibRound(plan, rowIndex) {
  const row = plan.rows[rowIndex];
  return Boolean(row && row.section === 'cuff' && plan.cuff.ribbed);
}

/** The value a fixed (non-simulated) cell should hold, 1 = contrast / purl. */
export function fixedCellValue(plan, rowIndex, stitchIndex) {
  if (!isRibRound(plan, rowIndex)) return 0;
  const { ribKnit, ribPurl } = plan.params;
  const repeat = ribKnit + ribPurl;
  return stitchIndex % repeat < ribKnit ? 0 : 1;
}
