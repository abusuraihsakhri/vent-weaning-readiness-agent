# Vent Weaning Readiness Agent

> **Domain:** Cardiovascular Medicine & Hemodynamic Analytics
> **Reference Guidelines & Standards:** `AHA/ACC Practice Guidelines & ESC Clinical Standards`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

**Vent Weaning Readiness Agent** is an advanced analytical and computational platform implementing RSBI (<105) & Spontaneous Breathing Trial Extubation Supervisor. It provides clinical decision support for mechanical ventilation liberation through validated respiratory indices.

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Core Algorithmic & Evaluation Engines

- **`WeaningAssessment`**: Complete weaning readiness assessment result including RSBI, CROP index, MIP interpretation, compliance calculations, and SBT criteria evaluation.

---

## 📐 Mathematical Formulation & Logic

```text
- RSBI = f / VT (breaths/min/L)        — RSBI < 105: Weaning likely to succeed
- CROP Index = (Cdyn * (PImax - f/VT)) * (PaO2/PAO2) / 100  — CROP > 13: Weaning likely to succeed
- Minute Ventilation (VE) = f * VT     — Normal: 5-10 L/min
- MIP/PImax: More negative = stronger   — MIP < -20 cmH2O: Adequate strength
- Static Compliance = VT / (Pplat - PEEP)  — Normal: 60-100 mL/cmH2O
- Dynamic Compliance = VT / (Ppeak - PEEP) — Normal: 40-80 mL/cmH2O
```

---

## 💻 CLI Quickstart & Usage

### 1. Single Patient Assessment
```bash
python cli.py single --rr 18 --vt 450 --mip --mip -35 --pplat 20 --ppeak 25 --peep 5 --pao2 90 --fio2 0.3 --paco2 40
```

### 2. RSBI Only Calculation
```bash
python cli.py rsbi --rr 20 --vt 400
```

### 3. Batch CSV Processing
```bash
python cli.py batch -i data.csv -o results.csv
```

### 4. Audit Verification
```bash
python cli.py audit --task-id CASE-001
python cli.py chat "Explain weaning criteria"
python cli.py verify-audit
```

### 5. Launch REST API Server
```bash
python cli.py serve --host 0.0.0.0 --port 8000
```

### Parameter Reference
- `single`: Complete weaning assessment with all parameters
- `rsbi`: Rapid Shallow Breathing Index calculation only
- `batch`: Batch process CSV file
- `audit`: Run audit verification
- `chat`: Supervisory chat interface
- `verify-audit`: Verify HMAC audit trail integrity
- `serve`: Launch FastAPI REST server

### Input Data Schema (for batch CSV)

| Field | Description | Requirement |
|:------|:------------|:------------|
| `respiratory_rate` | Breaths per minute | Required |
| `tidal_volume_ml` | Tidal volume in mL | Required |
| `mip` | Maximum inspiratory pressure (cmH2O) | Optional |
| `plateau_pressure` | Plateau pressure (cmH2O) | Optional |
| `peak_pressure` | Peak inspiratory pressure (cmH2O) | Optional |
| `peep` | PEEP (cmH2O) | Optional |
| `pao2` | PaO2 (mmHg) | Optional |
| `fio2` | FiO2 (0.0-1.0) | Optional |
| `paco2` | PaCO2 (mmHg) | Optional |
| `patient_id` | Patient identifier | Optional |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

### Security Configuration

The `AUDIT_SECRET_KEY` environment variable is **required** (minimum 32 characters). Set it before running:

```bash
# Linux/macOS
export AUDIT_SECRET_KEY="your-strong-secret-key-here-minimum-32-chars-long"

# Windows
set AUDIT_SECRET_KEY=your-strong-secret-key-here-minimum-32-chars-long
```

Or copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
# Edit .env with your values
```

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py 1000
```

---

## 🐳 Container Deployment

```bash
docker build -t vent-weaning-readiness-agent .
docker run -p 8000:8000 --env-file .env vent-weaning-readiness-agent
```

Or using docker-compose:

```bash
cp .env.example .env
# Edit .env with your AUDIT_SECRET_KEY
docker-compose up -d
```

---

## 📁 Project Structure

```
vent-weaning-readiness-agent/
├── agents/                      # Enterprise security, PHI guard, audit trail
│   ├── base.py                  # PHIGuard, AuditTrail, AuditLogger
│   ├── models.py                # Pydantic schemas
│   ├── supervisor.py            # Multi-agent orchestrator
│   ├── workers.py               # Specialized domain workers
│   ├── api.py                   # FastAPI REST server
│   ├── llm_factory.py           # LLM client factory
│   ├── metrics.py               # Prometheus metrics
│   ├── learning.py              # Bayesian calibration engine
│   └── streamer.py              # WebSocket telemetry
├── vent_weaning_readiness_agent/  # Alternative package implementation
├── tests/                       # Pytest test suite
├── web/                         # Operations console (HTML)
├── vent_wean_sentinel.py        # Core calculations & CLI
├── cli.py                       # CLI entry point
├── simulator.py                 # High-throughput simulation
├── enrichment.py                # Enrichment feature suite
├── pyproject.toml               # Project configuration
├── Dockerfile                   # Container build
├── docker-compose.yml           # Container orchestration
└── .env.example                 # Environment template
```
