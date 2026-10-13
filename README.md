# Ventilator Weaning Indices — VentWean Sentinel

An educational adult ventilator-liberation calculator with a static browser UI, Python CLI, CSV processing and an optional FastAPI endpoint.

**Clinical limitation:** Research and teaching only. Not a validated clinical decision-support device. It cannot establish readiness for a spontaneous breathing trial (SBT), SBT success or extubation safety.

## Browser application

Open `web/index.html` locally in a modern browser. The interface calculates respiratory indices, records optional reported bedside considerations and exports values as CSV. It processes data locally without a server or Python runtime. It does not transmit, store or share form values.

The repository includes a GitHub Pages workflow to publish the `web/` directory. A live link will be added only after the deployed site has been verified.

## Calculations and evidence

- **RSBI** = respiratory rate / tidal volume in liters (breaths/min/L). The historical threshold of 105 is **not** a required SBT gatekeeper.
- **Minute ventilation** = respiratory rate × tidal volume in liters (L/min).
- **Static compliance** = tidal volume (mL) / (plateau pressure − PEEP).
- **Dynamic compliance** = tidal volume (mL) / (peak pressure − PEEP).
- **Alveolar PAO₂** = FiO₂ × (760 − 47) − PaCO₂ / 0.8 (sea-level approximation).
- **CROP** = dynamic compliance × |MIP| × (PaO₂ / PAO₂) / respiratory rate; historical threshold >13.

The 2024 AARC guideline suggests that RSBI is *not required* to screen for an SBT. Adequate oxygenation, hemodynamic stability, reversal of the underlying cause and the ability to initiate breaths are more clinically relevant screening domains. Indices alone cannot authorize extubation.

Sources: [AARC 2024 SBT guideline](https://doi.org/10.4187/respcare.11735); [Yang and Tobin 1991](https://doi.org/10.1056/NEJM199105233242101); [ATS/CHEST 2017](https://doi.org/10.1164/rccm.201610-2075ST).

## Python quick start

Python 3.9 or later:

~~~bash
python -m pip install -e '.[api,test]'
python cli.py rsbi --rr 20 --vt 400
python cli.py single --rr 18 --vt 450 --mip -35 --pplat 20 --ppeak 25 --peep 5 --pao2 90 --fio2 0.3 --paco2 40
python cli.py batch -i sample.csv -o results.csv
python cli.py serve --host 127.0.0.1 --port 8000
~~~

The installed command `vent-weaning-readiness-agent` uses this calculator. The compatibility-only `vent-weaning-readiness-legacy` command is a generic demonstration, not validated respiratory software.

The optional API exposes `POST /api/weaning` with JSON, for example `{"respiratory_rate":18,"tidal_volume_ml":450}`, as well as `GET /health`. Legacy `POST /api/audit` remains demonstration logic with arbitrary thresholds, not clinical recommendations.

The HMAC-SHA256 audit log is **in-memory only**. Audit commands require a random `AUDIT_SECRET_KEY` of 32 characters or more. The identifier-pattern guard is incomplete and is not proof of HIPAA de-identification. Do not enter real patient identifiers. Legacy `audit` and `chat` commands do not conduct clinical verification or model inference; listed LLM providers currently return a deterministic mock.

## Tests and deployment

~~~bash
python -m pip install -e '.[api,test]'
pytest -q
node --check web/calculator.js
node --check web/app.js
node --test web/test_calculator.cjs
python -m pip install build && python -m build
~~~

GitHub Actions runs Python tests on 3.10, 3.11 and 3.12 and Node-based browser calculation tests.

Optional Docker server:

~~~bash
cp .env.example .env
# Set AUDIT_SECRET_KEY to a cryptographically random value
docker compose up --build
~~~

The static application uses modern browser JavaScript rather than Pyodide; it needs no Python runtime or remote services. Browser automation is not included, so compatibility is not claimed beyond the supported web standards.

## License

MIT — see [LICENSE](LICENSE).
