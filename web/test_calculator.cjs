"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { calculate } = require("./calculator.js");

test("RSBI and minute ventilation use correct units", () => {
  const r = calculate({ respiratory_rate: 18, tidal_volume_ml: 450 });
  assert.equal(r.rsbi, 40);
  assert.equal(r.minuteVentilation, 8.1);
  assert.equal(r.belowHistoricalRsbiThreshold, true);
  assert.equal(r.crop, null);
  assert.equal(r.assessed, 0);
});
test("CROP follows published compliance * MIP * oxygenation / rate equation", () => {
  const r = calculate({ respiratory_rate: 20, tidal_volume_ml: 500,
    mip: -30, peep: 5, peak_pressure: 25, plateau_pressure: 20,
    fio2: 0.3, paco2: 40, pao2: 80 });
  assert.equal(r.dynamicCompliance, 25);
  assert.equal(r.staticCompliance, 500 / 15);
  const alveolar = 0.3 * 713 - 40 / 0.8;
  assert.ok(Math.abs(r.crop - (25 * 30 * (80 / alveolar) / 20)) < 1e-9);
});
test("CROP unavailable when gas exchange inputs are incomplete", () => {
  const r = calculate({ respiratory_rate: 12, tidal_volume_ml: 400,
    mip: -30, peep: 5, peak_pressure: 25, pao2: 90 });
  assert.equal(r.crop, null);
});
test("CROP unavailable if estimated alveolar oxygen is nonpositive", () => {
  const r = calculate({ respiratory_rate: 12, tidal_volume_ml: 400,
    mip: -30, peep: 5, peak_pressure: 25, pao2: 90,
    fio2: 0, paco2: 40 });
  assert.equal(r.crop, null);
});
test("invalid inputs are rejected rather than coerced", () => {
  assert.throws(() => calculate({ respiratory_rate: 0, tidal_volume_ml: 400 }), /greater than 0/);
  assert.throws(() => calculate({ respiratory_rate: 10, tidal_volume_ml: "Infinity" }), /finite/);
  assert.throws(() => calculate({ respiratory_rate: 10, tidal_volume_ml: 400, fio2: 21 }), /at most 1/);
  assert.throws(() => calculate({ respiratory_rate: 10, tidal_volume_ml: 400,
    peep: 8, plateau_pressure: 8 }), /exceed PEEP/);
});
test("unassessed checklist items are not counted as failed", () => {
  const r = calculate({ respiratory_rate: 16, tidal_volume_ml: 450,
    adequate_oxygenation: "yes", hemodynamic_stability: "no" });
  assert.equal(r.assessed, 2);
  assert.equal(r.met, 1);
  assert.match(r.screenNote, /not met/);
});
test("no automated weaning or extubation verdict is produced", () => {
  const r = calculate({ respiratory_rate: 15, tidal_volume_ml: 500,
    adequate_oxygenation: "yes", hemodynamic_stability: "yes" });
  assert.equal(Object.hasOwn(r, "weaning_likely"), false);
  assert.match(r.interpretation, /separate clinical decisions/);
});
test("unknown checklist values are rejected", () => {
  assert.throws(() => calculate({ respiratory_rate: 15, tidal_volume_ml: 400,
    adequate_oxygenation: "sometimes" }), /Invalid checklist/);
});
