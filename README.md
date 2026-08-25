# Ventilator Weaning Readiness Calculator

Real clinical calculators for mechanical ventilation liberation assessment. Stdlib-only Python.

## Calculators

| Calculator | Formula | Threshold | Reference |
|:-----------|:--------|:----------|:----------|
| **RSBI** | f / VT (breaths/min/L) | < 105: likely to succeed | Yang & Tobin, NEJM 1991 |
| **CROP Index** | (Cdyn × (PImax - RSBI)) × (PaO2/PAO2) / 100 | > 13: likely to succeed | Yang & Tobin, 1991 |
| **Minute Ventilation** | f × VT | Normal 5-10 L/min | Standard |
| **MIP/PImax** | Max inspiratory pressure | < -20 cmH2O: adequate | Standard |
| **Static Compliance** | VT / (Pplat - PEEP) | Normal 60-100 mL/cmH2O | Standard |
| **Dynamic Compliance** | VT / (Ppeak - PEEP) | Normal 40-80 mL/cmH2O | Standard |
| **SBT Criteria** | Checklist of readiness criteria | All met: proceed | ATS/ACCP 2017 |

## Quick Start

```bash
# Full weaning assessment
python vent_wean_sentinel.py single --rr 18 --vt 450 --mip -35 --pplat 20 --ppeak 25 --peep 5 --pao2 90 --fio2 0.3 --paco2 40

# RSBI only
python vent_wean_sentinel.py rsbi --rr 20 --vt 400

# Batch CSV processing
python vent_wean_sentinel.py batch -i vent_data.csv -o results.csv
```

## Python API

```python
from vent_wean_sentinel import (
    rsbi, minute_ventilation, static_compliance, dynamic_compliance,
    crop_index, assess_weaning, mip_interpretation,
)

# RSBI
val = rsbi(respiratory_rate=20, tidal_volume_ml=400)  # 50.0

# Full assessment
result = assess_weaning(
    respiratory_rate=18, tidal_volume_ml=450, mip=-35,
    plateau_pressure=20, peak_pressure=25, peep=5,
    pao2=90, fio2=0.3, paco2=40,
)
# result.rsbi_value, result.weaning_likely, result.overall_recommendation
```

## Tests

```bash
python -m pytest test_vent_wean_sentinel.py -v
```

## License

MIT
