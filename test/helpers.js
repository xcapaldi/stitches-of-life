/** A rectangular map, for checking automaton behaviour without hat shaping. */
export function uniformPlan(rowCount, width, options = {}) {
  const rows = [];
  for (let index = 0; index < rowCount; index += 1) {
    rows.push({
      index,
      width,
      section: 'body',
      kind: 'plain',
      decreases: 0,
      inMap: options.inMap ? options.inMap(index) : true,
    });
  }
  return {
    rows,
    cuff: { ribbed: Boolean(options.ribbed) },
    crown: {},
    params: {
      stitchGauge: 5,
      rowGauge: 7,
      ribKnit: 2,
      ribPurl: 2,
      stitchMode: 'colorwork',
    },
    derived: {},
  };
}
