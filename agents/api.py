"""
FastAPI REST API Server for Vent Weaning Readiness Agent.
"""
from typing import Dict, Any, List, Optional
from dataclasses import asdict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from vent_wean_sentinel import assess_weaning
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Vent Weaning Readiness Agent API",
    description="Educational respiratory indices. Legacy generic /api/audit is a demonstration only; /api/weaning uses the respiratory calculator. Not for clinical decisions.",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


class WeaningRequest(BaseModel):
    respiratory_rate: float = Field(gt=0, allow_inf_nan=False)
    tidal_volume_ml: float = Field(gt=0, allow_inf_nan=False)
    mip: Optional[float] = Field(default=None, allow_inf_nan=False)
    plateau_pressure: Optional[float] = Field(default=None, allow_inf_nan=False)
    peak_pressure: Optional[float] = Field(default=None, allow_inf_nan=False)
    peep: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    pao2: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    fio2: Optional[float] = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    paco2: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    pao2_alveolar: Optional[float] = Field(default=None, gt=0, allow_inf_nan=False)
    adequate_oxygenation: Optional[bool] = None
    hemodynamic_stability: Optional[bool] = None
    no_active_infection: Optional[bool] = None
    adequate_mental_status: Optional[bool] = None
    no_sedation: Optional[bool] = None
    cough_reflex_present: Optional[bool] = None


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "vent-weaning-readiness-agent", "domain": "Respiratory Care", "clinical_use": False, "version": "3.1.0"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/weaning")
def api_weaning(payload: WeaningRequest):
    """Stateless educational calculations; no patient identifiers accepted."""
    try:
        return asdict(assess_weaning(**payload.model_dump(exclude_none=True)))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs():
    # Never disclose task identifiers or audit metadata through an open endpoint.
    return {"audit_trail_length": len(AuditLogger.get_trail()), "verified": AuditLogger.verify_integrity()}
