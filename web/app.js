(function () {
  "use strict";
  const form = document.getElementById("calc-form");
  const results = document.getElementById("results");
  const error = document.getElementById("error");
  const exportButton = document.getElementById("export");
  let lastResult = null;

  function create(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }
  function format(value, digits) {
    return value === null ? "Not calculated" : value.toFixed(digits);
  }
  function metric(label, value, detail) {
    const item = create("div", "metric");
    item.appendChild(create("div", "metric-label", label));
    item.appendChild(create("div", "metric-value", value));
    item.appendChild(create("div", "metric-detail", detail));
    return item;
  }
  function gather() {
    const data = {};
    const ids = [
      "respiratory_rate", "tidal_volume_ml", "mip", "plateau_pressure",
      "peak_pressure", "peep", "pao2", "fio2", "paco2",
      "adequate_oxygenation", "hemodynamic_stability", "no_active_infection",
      "adequate_mental_status", "no_sedation", "cough_reflex_present"
    ];
    ids.forEach(function (id) {
      data[id] = document.getElementById(id).value.trim();
    });
    return data;
  }
  function render(report) {
    results.replaceChildren();
    const tiles = create("div", "result-grid");
    tiles.appendChild(metric("RSBI", format(report.rsbi, 1) + " breaths/min/L",
      "Historic <105 threshold: " + (report.belowHistoricalRsbiThreshold ? "below" : "at or above")));
    tiles.appendChild(metric("Minute ventilation", format(report.minuteVentilation, 2) + " L/min",
      "Respiratory rate × tidal volume"));
    tiles.appendChild(metric("Static compliance",
      report.staticCompliance === null ? "—" : format(report.staticCompliance, 1) + " mL/cmH₂O",
      "VT / (plateau − PEEP)"));
    tiles.appendChild(metric("Dynamic compliance",
      report.dynamicCompliance === null ? "—" : format(report.dynamicCompliance, 1) + " mL/cmH₂O",
      "VT / (peak − PEEP)"));
    tiles.appendChild(metric("CROP index",
      report.crop === null ? "—" : format(report.crop, 2),
      "Cdyn × |MIP| × (PaO₂ / PAO₂) / rate; historical threshold >13"));
    tiles.appendChild(metric("Reported checklist", report.met + " / " + report.assessed + " met",
      (6 - report.assessed) + " item(s) not assessed"));
    results.appendChild(tiles);
    results.appendChild(create("p", "result-note", report.screenNote));
    results.appendChild(create("p", "result-disclaimer", report.interpretation));
    exportButton.disabled = false;
  }
  function csvCell(value) {
    const text = String(value === null || value === undefined ? "" : value);
    return '"' + text.replace(/"/g, '""') + '"';
  }
  exportButton.addEventListener("click", function () {
    if (!lastResult) return;
    const headers = ["rsbi", "minute_ventilation_l_min", "static_compliance_ml_cmh2o",
      "dynamic_compliance_ml_cmh2o", "crop", "checklist_met", "checklist_assessed"];
    const r = lastResult;
    const values = [r.rsbi, r.minuteVentilation, r.staticCompliance,
      r.dynamicCompliance, r.crop, r.met, r.assessed];
    const csv = headers.map(csvCell).join(",") + "\r\n" +
      values.map(csvCell).join(",") + "\r\n";
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "vent-weaning-indices.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  });
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    error.textContent = "";
    try {
      lastResult = window.VentCalc.calculate(gather());
      render(lastResult);
    } catch (exc) {
      lastResult = null;
      exportButton.disabled = true;
      results.replaceChildren(create("p", "empty-state", "Correct the inputs and calculate again."));
      error.textContent = exc.message || "Unable to calculate these values.";
      error.focus();
    }
  });
})();
