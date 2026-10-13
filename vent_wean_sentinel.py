#!/usr/bin/env python3
"""
VentWean Sentinel: Ventilator Weaning Readiness Calculator
==========================================================
Real clinical calculators for mechanical ventilation liberation:

- Rapid Shallow Breathing Index (RSBI) = f / VT (breaths/min/L).
  The historical 105 cutoff is descriptive, not an SBT gatekeeper.
- CROP Index = Cdyn * abs(PImax) * (PaO2 / PAO2_alveolar) / respiratory_rate.
  A historical threshold of >13 is descriptive, not an extubation decision.
- Minute Ventilation (VE) = f * VT. Normal: 5-10 L/min
- Maximum Inspiratory Pressure (MIP/PImax):
    More negative = stronger. MIP < -20 cmH2O: Adequate strength
- Static Compliance = VT / (Pplat - PEEP)
- Dynamic Compliance = VT / (Ppeak - PEEP)
- Weaning criteria checklist (SBT readiness)

Stdlib only. Author: Dr. Abu Suraih Sakhri. License: MIT.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def _require_finite(**values: float) -> None:
    for name, value in values.items():
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")


def rsbi(respiratory_rate: float, tidal_volume_ml: float) -> float:
    """Calculate Rapid Shallow Breathing Index (RSBI).

    RSBI = respiratory_rate / tidal_volume_in_liters

    Args:
        respiratory_rate: Breaths per minute.
        tidal_volume_ml: Tidal volume in millilitres.

    Returns:
        RSBI in breaths/min/L.

    Raises:
        ValueError: If tidal_volume_ml <= 0.
    """
    _require_finite(respiratory_rate=respiratory_rate, tidal_volume_ml=tidal_volume_ml)
    if tidal_volume_ml <= 0:
        raise ValueError("Tidal volume must be > 0")
    if respiratory_rate < 0:
        raise ValueError("Respiratory rate must be >= 0")
    vt_liters = tidal_volume_ml / 1000.0
    return respiratory_rate / vt_liters


def minute_ventilation(respiratory_rate: float, tidal_volume_ml: float) -> float:
    """Calculate Minute Ventilation (VE).

    VE = respiratory_rate * tidal_volume (in L/min)

    Args:
        respiratory_rate: Breaths per minute.
        tidal_volume_ml: Tidal volume in millilitres.

    Returns:
        Minute ventilation in L/min.
    """
    _require_finite(respiratory_rate=respiratory_rate, tidal_volume_ml=tidal_volume_ml)
    if respiratory_rate < 0:
        raise ValueError("Respiratory rate must be >= 0")
    if tidal_volume_ml < 0:
        raise ValueError("Tidal volume must be >= 0")
    return respiratory_rate * (tidal_volume_ml / 1000.0)


def static_compliance(tidal_volume_ml: float, plateau_pressure: float, peep: float) -> float:
    """Calculate static respiratory compliance.

    Cstat = VT / (Pplat - PEEP)

    Normal: 60-100 mL/cmH2O.

    Args:
        tidal_volume_ml: Tidal volume in mL.
        plateau_pressure: Plateau pressure in cmH2O.
        peep: Positive end-expiratory pressure in cmH2O.

    Returns:
        Static compliance in mL/cmH2O.

    Raises:
        ValueError: If (Pplat - PEEP) <= 0.
    """
    _require_finite(tidal_volume_ml=tidal_volume_ml, plateau_pressure=plateau_pressure, peep=peep)
    driving = plateau_pressure - peep
    if driving <= 0:
        raise ValueError("(Pplat - PEEP) must be > 0")
    if tidal_volume_ml < 0:
        raise ValueError("Tidal volume must be >= 0")
    return tidal_volume_ml / driving


def dynamic_compliance(tidal_volume_ml: float, peak_pressure: float, peep: float) -> float:
    """Calculate dynamic respiratory compliance.

    Cdyn = VT / (Ppeak - PEEP)

    Normal: 40-80 mL/cmH2O (lower than static due to airway resistance).

    Args:
        tidal_volume_ml: Tidal volume in mL.
        peak_pressure: Peak inspiratory pressure in cmH2O.
        peep: PEEP in cmH2O.

    Returns:
        Dynamic compliance in mL/cmH2O.
    """
    _require_finite(tidal_volume_ml=tidal_volume_ml, peak_pressure=peak_pressure, peep=peep)
    driving = peak_pressure - peep
    if driving <= 0:
        raise ValueError("(Ppeak - PEEP) must be > 0")
    if tidal_volume_ml < 0:
        raise ValueError("Tidal volume must be >= 0")
    return tidal_volume_ml / driving


def mip_interpretation(mip: float) -> str:
    """Interpret Maximum Inspiratory Pressure (MIP / PImax).

    MIP is measured as a negative value (inspiratory effort against occlusion).
    More negative = stronger inspiratory effort.

    Args:
        mip: MIP in cmH2O (typically negative, e.g. -30).

    Returns:
        Interpretation string.
    """
    _require_finite(mip=mip)
    # MIP is often reported as a negative number
    abs_mip = abs(mip)
    if abs_mip >= 30:
        return "Strong inspiratory effort (adequate for weaning)"
    elif abs_mip >= 20:
        return "Borderline inspiratory effort (weaning may be attempted)"
    else:
        return "Weak inspiratory effort (weaning unlikely to succeed)"


def crop_index(
    dynamic_compliance_ml: float,
    mip: float,
    respiratory_rate: float,
    tidal_volume_ml: float,
    pao2: float,
    pao2_alveolar: float,
) -> float:
    """Calculate CROP Index for weaning prediction.

    CROP = Cdyn * abs(PImax) * (PaO2 / PAO2_alveolar) / respiratory_rate

    Cdyn is dynamic compliance (mL/cmH2O), PImax is maximum inspiratory
    pressure (cmH2O), and PaO2 / PAO2_alveolar is the oxygenation ratio.
    The historical cutoff >13 is not an extubation decision rule.

    Note: PImax is used as its absolute value in the formula.

    Args:
        dynamic_compliance_ml: Dynamic compliance in mL/cmH2O.
        mip: Maximum inspiratory pressure (negative value, cmH2O).
        respiratory_rate: Breaths per minute.
        tidal_volume_ml: Tidal volume in mL.
        pao2: Arterial O2 partial pressure (mmHg).
        pao2_alveolar: Alveolar O2 partial pressure (mmHg).

    Returns:
        CROP index value.
    """
    _require_finite(
        dynamic_compliance_ml=dynamic_compliance_ml, mip=mip,
        respiratory_rate=respiratory_rate, tidal_volume_ml=tidal_volume_ml,
        pao2=pao2, pao2_alveolar=pao2_alveolar,
    )
    if pao2_alveolar <= 0:
        raise ValueError("PAO2 must be > 0")
    if respiratory_rate <= 0:
        raise ValueError("Respiratory rate must be > 0 for CROP")
    if dynamic_compliance_ml <= 0 or tidal_volume_ml <= 0 or pao2 < 0:
        raise ValueError("Compliance and tidal volume must be > 0; PaO2 must be >= 0")
    return dynamic_compliance_ml * abs(mip) * (pao2 / pao2_alveolar) / respiratory_rate


def calculate_alveolar_pao2(fio2: float, paco2: float, patm: float = 760.0, ph2o: float = 47.0, rq: float = 0.8) -> float:
    """Calculate alveolar PAO2.

    PAO2 = FiO2 * (Patm - PH2O) - PaCO2 / RQ

    Args:
        fio2: Fraction of inspired oxygen (0.0-1.0).
        paco2: Arterial CO2 partial pressure (mmHg).
        patm: Atmospheric pressure (mmHg).
        ph2o: Water vapour pressure (mmHg).
        rq: Respiratory quotient.

    Returns:
        Alveolar PAO2 in mmHg.
    """
    _require_finite(fio2=fio2, paco2=paco2, patm=patm, ph2o=ph2o, rq=rq)
    if not 0 <= fio2 <= 1 or paco2 < 0 or rq <= 0 or patm <= ph2o:
        raise ValueError("Invalid alveolar gas equation parameters")
    return fio2 * (patm - ph2o) - (paco2 / rq)


# ---------------------------------------------------------------------------
# Weaning readiness assessment
# ---------------------------------------------------------------------------

@dataclass
class WeaningAssessment:
    """Complete weaning readiness assessment result."""
    rsbi_value: float
    rsbi_interpretation: str
    minute_ventilation_value: float
    minute_ventilation_interpretation: str
    static_compliance_value: Optional[float] = None
    dynamic_compliance_value: Optional[float] = None
    mip_value: Optional[float] = None
    mip_interpretation: Optional[str] = None
    crop_value: Optional[float] = None
    crop_interpretation: Optional[str] = None
    sbt_criteria: Dict[str, bool] = field(default_factory=dict)
    sbt_criteria_met: int = 0
    sbt_criteria_total: int = 0
    weaning_likely: Optional[bool] = None
    overall_recommendation: str = ""


def assess_weaning(
    respiratory_rate: float,
    tidal_volume_ml: float,
    mip: Optional[float] = None,
    plateau_pressure: Optional[float] = None,
    peak_pressure: Optional[float] = None,
    peep: Optional[float] = None,
    pao2: Optional[float] = None,
    fio2: Optional[float] = None,
    paco2: Optional[float] = None,
    pao2_alveolar: Optional[float] = None,
    # SBT criteria
    adequate_oxygenation: Optional[bool] = None,
    hemodynamic_stability: Optional[bool] = None,
    no_active_infection: Optional[bool] = None,
    adequate_mental_status: Optional[bool] = None,
    no_sedation: Optional[bool] = None,
    cough_reflex_present: Optional[bool] = None,
) -> WeaningAssessment:
    """Perform comprehensive weaning readiness assessment.

    Args:
        respiratory_rate: Breaths per minute.
        tidal_volume_ml: Tidal volume in mL.
        mip: Maximum inspiratory pressure (negative, cmH2O).
        plateau_pressure: Plateau pressure (cmH2O).
        peak_pressure: Peak inspiratory pressure (cmH2O).
        peep: PEEP (cmH2O).
        pao2: PaO2 (mmHg).
        fio2: FiO2 (0.0-1.0).
        paco2: PaCO2 (mmHg).
        pao2_alveolar: Pre-calculated PAO2 (mmHg).
        adequate_oxygenation: SpO2 >= 90% on FiO2 <= 0.4 or PaO2 >= 60.
        hemodynamic_stability: No vasopressors or low-dose only.
        no_active_infection: No active/severe infection.
        adequate_mental_status: Alert, follows commands.
        no_sedation: Off or minimal sedation.
        cough_reflex_present: Able to cough/clear secretions.

    Returns:
        WeaningAssessment dataclass.
    """
    # Validate all supplied measurements before computing or rounding results.
    measurements = {
        "respiratory_rate": respiratory_rate,
        "tidal_volume_ml": tidal_volume_ml,
        "mip": mip,
        "plateau_pressure": plateau_pressure,
        "peak_pressure": peak_pressure,
        "peep": peep,
        "pao2": pao2,
        "fio2": fio2,
        "paco2": paco2,
        "pao2_alveolar": pao2_alveolar,
    }
    _require_finite(**{k: v for k, v in measurements.items() if v is not None})
    if respiratory_rate <= 0:
        raise ValueError("Respiratory rate must be > 0")
    if tidal_volume_ml <= 0:
        raise ValueError("Tidal volume must be > 0")
    if fio2 is not None and not (0.0 <= fio2 <= 1.0):
        raise ValueError("FiO2 must be between 0.0 and 1.0")
    if peep is not None and peep < 0:
        raise ValueError("PEEP must be >= 0")
    if pao2 is not None and pao2 < 0:
        raise ValueError("PaO2 must be >= 0")
    if paco2 is not None and paco2 < 0:
        raise ValueError("PaCO2 must be >= 0")

    # RSBI
    rsbi_val = rsbi(respiratory_rate, tidal_volume_ml)
    if rsbi_val < 105:
        rsbi_interp = "RSBI < 105: historically associated with successful weaning; does not establish that weaning will succeed"
    else:
        rsbi_interp = "RSBI >= 105: historical risk marker for weaning failure; does not mean an SBT must fail"

    # Minute ventilation
    ve = minute_ventilation(respiratory_rate, tidal_volume_ml)
    if 5.0 <= ve <= 10.0:
        ve_interp = "Normal minute ventilation (5-10 L/min)"
    elif ve < 5.0:
        ve_interp = "Low minute ventilation (< 5 L/min) — possible hypoventilation"
    else:
        ve_interp = "Elevated minute ventilation (> 10 L/min) — increased work of breathing"

    assessment = WeaningAssessment(
        rsbi_value=round(rsbi_val, 1),
        rsbi_interpretation=rsbi_interp,
        minute_ventilation_value=round(ve, 2),
        minute_ventilation_interpretation=ve_interp,
    )

    # Compliance
    if plateau_pressure is not None and peep is not None:
        cstat = static_compliance(tidal_volume_ml, plateau_pressure, peep)
        assessment.static_compliance_value = round(cstat, 1)

    if peak_pressure is not None and peep is not None:
        cdyn = dynamic_compliance(tidal_volume_ml, peak_pressure, peep)
        assessment.dynamic_compliance_value = round(cdyn, 1)

    # MIP
    if mip is not None:
        assessment.mip_value = mip
        assessment.mip_interpretation = mip_interpretation(mip)

    # CROP index
    if (assessment.dynamic_compliance_value is not None and mip is not None
            and pao2 is not None):
        if pao2_alveolar is None and fio2 is not None and paco2 is not None:
            pao2_alveolar = calculate_alveolar_pao2(fio2, paco2)
        if pao2_alveolar is not None and pao2_alveolar > 0:
            crop_val = crop_index(
                cdyn, mip,
                respiratory_rate, tidal_volume_ml, pao2, pao2_alveolar,
            )
            assessment.crop_value = round(crop_val, 1)
            if crop_val > 13:
                assessment.crop_interpretation = "CROP > 13: historically favorable; not sufficient for an extubation decision"
            else:
                assessment.crop_interpretation = "CROP <= 13: historical risk marker; not a standalone extubation decision"

    # SBT criteria checklist
    criteria = {}
    if adequate_oxygenation is not None:
        criteria["Adequate oxygenation (SpO2>=90% on FiO2<=0.4 or PaO2>=60)"] = adequate_oxygenation
    if hemodynamic_stability is not None:
        criteria["Hemodynamic stability (no/low-dose vasopressors)"] = hemodynamic_stability
    if no_active_infection is not None:
        criteria["No active/severe infection"] = no_active_infection
    if adequate_mental_status is not None:
        criteria["Adequate mental status (alert, follows commands)"] = adequate_mental_status
    if no_sedation is not None:
        criteria["Off or minimal sedation"] = no_sedation
    if cough_reflex_present is not None:
        criteria["Cough reflex present (able to clear secretions)"] = cough_reflex_present

    assessment.sbt_criteria = criteria
    assessment.sbt_criteria_met = sum(1 for v in criteria.values() if v)
    assessment.sbt_criteria_total = len(criteria)

    # There is no validated voting score combining RSBI, minute ventilation,
    # MIP, CROP and this partial checklist. Never infer SBT/extubation success.
    assessment.weaning_likely = None
    if not criteria:
        assessment.overall_recommendation = (
            "Bedside SBT readiness criteria were not supplied. Review the cause of "
            "respiratory failure, oxygenation, hemodynamic stability and ability "
            "to initiate breaths using a local liberation protocol."
        )
    elif not all(criteria.values()):
        assessment.overall_recommendation = (
            "At least one reported bedside consideration was not met. Review "
            "the clinical context and local SBT protocol; calculated indices "
            "must not override bedside assessment."
        )
    else:
        assessment.overall_recommendation = (
            "All supplied checklist items are marked met, but this is not a "
            "validated readiness score. A clinician must assess SBT eligibility, "
            "SBT performance and separate extubation considerations."
        )

    return assessment


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def _safe_path(path: str) -> str:
    """Validate path is safe (no directory traversal)."""
    normalized = os.path.normpath(path)
    if normalized.startswith("..") or normalized.startswith("/..") or ".." in normalized.split(os.sep):
        raise ValueError(f"Path traversal detected: {path}")
    return normalized


def process_csv(input_path: str, output_path: str) -> int:
    """Process a CSV of ventilator data and write weaning assessments.

    Expected columns: respiratory_rate, tidal_volume_ml
    Optional: mip, plateau_pressure, peak_pressure, peep, pao2, fio2, paco2,
              adequate_oxygenation, hemodynamic_stability, no_active_infection,
              adequate_mental_status, no_sedation, cough_reflex_present, patient_id
    """
    input_path = _safe_path(input_path)
    output_path = _safe_path(output_path)
    if os.path.abspath(input_path) == os.path.abspath(output_path):
        raise ValueError("Output CSV must differ from input CSV")
    results: List[Dict[str, Any]] = []
    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            def _float(k):
                v = row.get(k, "")
                return float(v) if v not in ("", None) else None
            def _bool(k):
                v = row.get(k, "")
                if v in ("", None):
                    return None
                value = v.strip().lower()
                if value in ("1", "true", "yes", "y"):
                    return True
                if value in ("0", "false", "no", "n"):
                    return False
                raise ValueError(f"Invalid boolean for {k}: {v!r}")

            a = assess_weaning(
                respiratory_rate=float(row["respiratory_rate"]),
                tidal_volume_ml=float(row["tidal_volume_ml"]),
                mip=_float("mip"),
                plateau_pressure=_float("plateau_pressure"),
                peak_pressure=_float("peak_pressure"),
                peep=_float("peep"),
                pao2=_float("pao2"),
                fio2=_float("fio2"),
                paco2=_float("paco2"),
                adequate_oxygenation=_bool("adequate_oxygenation"),
                hemodynamic_stability=_bool("hemodynamic_stability"),
                no_active_infection=_bool("no_active_infection"),
                adequate_mental_status=_bool("adequate_mental_status"),
                no_sedation=_bool("no_sedation"),
                cough_reflex_present=_bool("cough_reflex_present"),
            )
            d = {
                "patient_id": row.get("patient_id", ""),
                "rsbi": a.rsbi_value,
                "rsbi_interpretation": a.rsbi_interpretation,
                "minute_ventilation": a.minute_ventilation_value,
                "ve_interpretation": a.minute_ventilation_interpretation,
                "static_compliance": a.static_compliance_value,
                "dynamic_compliance": a.dynamic_compliance_value,
                "mip": a.mip_value,
                "mip_interpretation": a.mip_interpretation,
                "crop_index": a.crop_value,
                "crop_interpretation": a.crop_interpretation,
                "sbt_criteria_met": a.sbt_criteria_met,
                "sbt_criteria_total": a.sbt_criteria_total,
                "weaning_likely": a.weaning_likely,
                "recommendation": a.overall_recommendation,
            }
            results.append(d)

    if results:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            writer.writeheader()
            writer.writerows(results)
    return len(results)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="vent_wean_sentinel",
        description="Ventilator Weaning Readiness Calculator — RSBI, CROP, MIP, compliance, SBT criteria.",
    )
    sub = p.add_subparsers(dest="cmd")

    # Single assessment
    s = sub.add_parser("single", help="Single patient weaning assessment")
    s.add_argument("--rr", type=float, required=True, help="Respiratory rate (breaths/min)")
    s.add_argument("--vt", type=float, required=True, help="Tidal volume (mL)")
    s.add_argument("--mip", type=float, default=None, help="MIP/PImax (negative cmH2O)")
    s.add_argument("--pplat", type=float, default=None, help="Plateau pressure (cmH2O)")
    s.add_argument("--ppeak", type=float, default=None, help="Peak pressure (cmH2O)")
    s.add_argument("--peep", type=float, default=None, help="PEEP (cmH2O)")
    s.add_argument("--pao2", type=float, default=None, help="PaO2 (mmHg)")
    s.add_argument("--fio2", type=float, default=None, help="FiO2 (0.0-1.0)")
    s.add_argument("--paco2", type=float, default=None, help="PaCO2 (mmHg)")

    # RSBI only
    r = sub.add_parser("rsbi", help="Calculate RSBI only")
    r.add_argument("--rr", type=float, required=True, help="Respiratory rate")
    r.add_argument("--vt", type=float, required=True, help="Tidal volume (mL)")

    # Batch
    b = sub.add_parser("batch", help="Batch process CSV")
    b.add_argument("-i", "--input", required=True)
    b.add_argument("-o", "--output", default="results.csv")

    # Audit
    a = sub.add_parser("audit", help="Run audit verification")
    a.add_argument("--task-id", default="CLI-TEST-01", help="Task identifier for audit")

    # Chat
    c = sub.add_parser("chat", help="Supervisory chat interface")
    c.add_argument("query", nargs="+", help="Query string")

    # Verify audit
    v = sub.add_parser("verify-audit", help="Verify HMAC audit trail integrity")

    # Serve
    s = sub.add_parser("serve", help="Launch FastAPI REST server")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "single":
        a = assess_weaning(
            respiratory_rate=args.rr, tidal_volume_ml=args.vt,
            mip=args.mip, plateau_pressure=args.pplat,
            peak_pressure=args.ppeak, peep=args.peep,
            pao2=args.pao2, fio2=args.fio2, paco2=args.paco2,
        )
        out = {
            "rsbi": a.rsbi_value, "rsbi_interpretation": a.rsbi_interpretation,
            "minute_ventilation_L_min": a.minute_ventilation_value,
            "ve_interpretation": a.minute_ventilation_interpretation,
            "static_compliance": a.static_compliance_value,
            "dynamic_compliance": a.dynamic_compliance_value,
            "mip": a.mip_value, "mip_interpretation": a.mip_interpretation,
            "crop_index": a.crop_value, "crop_interpretation": a.crop_interpretation,
            "weaning_likely": a.weaning_likely,
            "recommendation": a.overall_recommendation,
        }
        print(json.dumps(out, indent=2))
        return 0

    if args.cmd == "rsbi":
        val = rsbi(args.rr, args.vt)
        print(json.dumps({"rsbi": round(val, 1), "historical_threshold": 105,
                          "below_historical_threshold": val < 105,
                          "weaning_likely": None,
                          "note": "RSBI alone cannot determine SBT or extubation readiness."}, indent=2))
        return 0

    if args.cmd == "batch":
        n = process_csv(args.input, args.output)
        print(f"Processed {n} records -> {args.output}")
        return 0

    if args.cmd == "audit":
        # Legacy demonstration command; does not perform cryptographic verification.
        out = {
            "task_id": args.task_id,
            "status": "DEMONSTRATION_ONLY",
            "message": "No audit operation was performed; use verify-audit for the in-memory HMAC chain.",
        }
        print(json.dumps(out, indent=2))
        return 0

    if args.cmd == "chat":
        # Supervisory chat interface
        query = " ".join(args.query)
        out = {
            "query": query,
            "response": "Demonstration chat only; no clinical interpretation or model inference was performed.",
        }
        print(json.dumps(out, indent=2))
        return 0

    if args.cmd == "verify-audit":
        # Verify HMAC audit trail integrity
        from agents.base import AuditLogger
        verified = AuditLogger.verify_integrity()
        trail_len = len(AuditLogger.get_trail())
        out = {
            "audit_integrity_verified": verified,
            "audit_trail_length": trail_len,
            "message": "HMAC-SHA256 audit trail integrity verified." if verified else "Audit trail integrity check FAILED.",
        }
        print(json.dumps(out, indent=2))
        return 0

    if args.cmd == "serve":
        # Launch FastAPI REST server
        try:
            import uvicorn
            from agents.api import app
            print(f"Starting VentWean Sentinel API on http://{args.host}:{args.port}")
            uvicorn.run(app, host=args.host, port=args.port)
        except ImportError:
            print("FastAPI / uvicorn not installed. Run 'pip install fastapi uvicorn'")
            return 1
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
