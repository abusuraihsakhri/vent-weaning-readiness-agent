/* Respiratory index calculations; no data is transmitted or stored.
   Reference: Yang & Tobin, NEJM 1991, doi:10.1056/NEJM199105233242101.
   The AARC 2024 guideline does not require RSBI to decide SBT readiness.
*/
(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.VentCalc = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function numberValue(value, label, required, min, max, strictMin) {
    if (value === "" || value === undefined || value === null) {
      if (required) throw new Error(label + " is required.");
      return null;
    }
    const n = typeof value === "number" ? value : Number(value);
    if (!Number.isFinite(n)) throw new Error(label + " must be a finite number.");
    if ((strictMin ? n <= min : n < min) || (max !== null && n > max)) {
      throw new Error(label + " must be " + (strictMin ? "greater than " : "at least ") + min +
        (max !== null ? " and at most " + max : "") + ".");
    }
    return n;
  }

  const checklistLabels = {
    adequate_oxygenation: "Adequate oxygenation",
    hemodynamic_stability: "Hemodynamic stability",
    no_active_infection: "No active or severe infection",
    adequate_mental_status: "Adequate mental status",
    no_sedation: "Off or minimal sedation",
    cough_reflex_present: "Effective cough and secretion management"
  };

  function calculate(input) {
    const rr = numberValue(input.respiratory_rate, "Respiratory rate", true, 0, null, true);
    const vt = numberValue(input.tidal_volume_ml, "Tidal volume", true, 0, null, true);
    const mip = numberValue(input.mip, "MIP", false, -300, 300, false);
    const pplat = numberValue(input.plateau_pressure, "Plateau pressure", false, 0, null, false);
    const ppeak = numberValue(input.peak_pressure, "Peak pressure", false, 0, null, false);
    const peep = numberValue(input.peep, "PEEP", false, 0, null, false);
    const pao2 = numberValue(input.pao2, "PaO2", false, 0, null, false);
    const fio2 = numberValue(input.fio2, "FiO2", false, 0, 1, false);
    const paco2 = numberValue(input.paco2, "PaCO2", false, 0, null, false);
    if (peep !== null && pplat !== null && pplat <= peep) {
      throw new Error("Plateau pressure must exceed PEEP.");
    }
    if (peep !== null && ppeak !== null && ppeak <= peep) {
      throw new Error("Peak pressure must exceed PEEP.");
    }

    const rsbi = rr / (vt / 1000);
    const minuteVentilation = rr * vt / 1000;
    const staticCompliance = peep !== null && pplat !== null ? vt / (pplat - peep) : null;
    const dynamicCompliance = peep !== null && ppeak !== null ? vt / (ppeak - peep) : null;
    const alveolarPao2 = fio2 !== null && paco2 !== null ?
      fio2 * (760 - 47) - paco2 / 0.8 : null;
    const crop = dynamicCompliance !== null && mip !== null && pao2 !== null &&
      alveolarPao2 !== null && alveolarPao2 > 0 ?
      dynamicCompliance * Math.abs(mip) * (pao2 / alveolarPao2) / rr : null;

    const checklist = Object.keys(checklistLabels).map(function (key) {
      const value = input[key];
      if (value !== "" && value !== "yes" && value !== "no" &&
          value !== null && value !== undefined) {
        throw new Error("Invalid checklist value for " + key + ".");
      }
      return { key: key, label: checklistLabels[key],
        status: value === "yes" ? true : value === "no" ? false : null };
    });
    const assessed = checklist.filter(function (item) { return item.status !== null; });
    const met = assessed.filter(function (item) { return item.status === true; }).length;
    let screenNote = "Bedside criteria were not assessed. Indices alone cannot determine SBT readiness.";
    if (assessed.length > 0) {
      screenNote = assessed.some(function (item) { return item.status === false; }) ?
        "At least one reported consideration is not met. Review before any SBT decision." :
        "Reported considerations are met, but this partial checklist is not a validated readiness score.";
    }
    return {
      rsbi: rsbi,
      belowHistoricalRsbiThreshold: rsbi < 105,
      minuteVentilation: minuteVentilation,
      staticCompliance: staticCompliance,
      dynamicCompliance: dynamicCompliance,
      mip: mip,
      alveolarPao2: alveolarPao2 !== null && alveolarPao2 > 0 ? alveolarPao2 : null,
      crop: crop,
      assessed: assessed.length,
      met: met,
      checklist: checklist,
      screenNote: screenNote,
      interpretation: "Historical thresholds are descriptive. SBT eligibility, SBT performance and extubation assessment are separate clinical decisions."
    };
  }

  return { calculate: calculate };
});
