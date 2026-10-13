"""Regression tests for correct respiratory calculations and audit integrity."""
import math
import pytest

from vent_wean_sentinel import (
    assess_weaning,
    crop_index,
    process_csv,
    rsbi,
    calculate_alveolar_pao2,
)
from agents.base import AuditTrail
from agents.api import WeaningRequest, api_weaning


def test_published_crop_equation():
    # (40 mL/cmH2O * 30 cmH2O * oxygenation ratio 0.8) / 20 breaths/min
    assert crop_index(40, -30, 20, 500, 80, 100) == pytest.approx(48)


def test_crop_rejects_zero_rate():
    with pytest.raises(ValueError, match="Respiratory rate"):
        crop_index(40, -30, 0, 500, 80, 100)


def test_nonfinite_measurements_rejected():
    for invalid in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError):
            rsbi(invalid, 400)
        with pytest.raises(ValueError):
            assess_weaning(16, 400, pao2=invalid)
        with pytest.raises(ValueError):
            calculate_alveolar_pao2(0.3, invalid)


def test_assessment_does_not_claim_unvalidated_prediction():
    result = assess_weaning(
        15, 500, mip=-40, peep=5, peak_pressure=25,
        pao2=90, fio2=0.3, paco2=40,
        adequate_oxygenation=True, hemodynamic_stability=False,
    )
    assert result.weaning_likely is None
    assert "not met" in result.overall_recommendation
    assert result.crop_value == pytest.approx(
        round((500 / 20) * 40 * (90 / (0.3 * 713 - 40 / 0.8)) / 15, 1)
    )


def test_csv_must_not_overwrite_input(tmp_path):
    original = tmp_path / "input.csv"
    original.write_text("respiratory_rate,tidal_volume_ml\n15,500\n")
    with pytest.raises(ValueError, match="must differ"):
        process_csv(str(original), str(original))
    assert original.read_text().startswith("respiratory_rate")


def test_hmac_verifies_all_signed_fields_and_returns_defensive_copies():
    trail = AuditTrail(secret_key="unit-test-only-not-a-production-key-123456")
    trail.log("tester", "test", "EVALUATION", {"synthetic": True})
    assert trail.verify_integrity()
    copied = trail.get_trail()
    copied[0]["actor"] = "changed"
    assert trail.verify_integrity()
    trail.logs[0]["actor"] = "changed"
    assert not trail.verify_integrity()


def test_stateless_api_uses_respiratory_engine():
    request = WeaningRequest(respiratory_rate=20, tidal_volume_ml=500)
    result = api_weaning(request)
    assert result["rsbi_value"] == 40
    assert result["weaning_likely"] is None
