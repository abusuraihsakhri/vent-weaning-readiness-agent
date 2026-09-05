#!/usr/bin/env python3
"""Tests for Ventilator Weaning Readiness Calculator.

Run with: python -m pytest test_vent_wean_sentinel.py -v
    or:   python test_vent_wean_sentinel.py
"""
import json
import os
import sys
import tempfile
import unittest

from vent_wean_sentinel import (
    rsbi,
    minute_ventilation,
    static_compliance,
    dynamic_compliance,
    mip_interpretation,
    crop_index,
    calculate_alveolar_pao2,
    assess_weaning,
    WeaningAssessment,
    process_csv,
    main,
)


class TestRSBI(unittest.TestCase):
    """Test Rapid Shallow Breathing Index."""

    def test_normal_rsbi(self):
        """RR 15, VT 500mL -> RSBI = 30."""
        result = rsbi(15, 500)
        self.assertAlmostEqual(result, 30.0)

    def test_high_rsbi(self):
        """RR 35, VT 250mL -> RSBI = 140 (weaning likely to fail)."""
        result = rsbi(35, 250)
        self.assertAlmostEqual(result, 140.0)

    def test_threshold_rsbi(self):
        """RSBI exactly 105."""
        result = rsbi(21, 200)
        self.assertAlmostEqual(result, 105.0)

    def test_zero_vt_raises(self):
        with self.assertRaises(ValueError):
            rsbi(15, 0)

    def test_negative_rr_raises(self):
        with self.assertRaises(ValueError):
            rsbi(-5, 500)

    def test_low_rsbi_weaning_likely(self):
        """RSBI < 105 indicates weaning likely to succeed."""
        result = rsbi(20, 400)
        self.assertLess(result, 105)


class TestMinuteVentilation(unittest.TestCase):
    """Test minute ventilation calculation."""

    def test_normal(self):
        """RR 12, VT 500mL -> VE = 6 L/min."""
        result = minute_ventilation(12, 500)
        self.assertAlmostEqual(result, 6.0)

    def test_high_ve(self):
        """RR 20, VT 700mL -> VE = 14 L/min."""
        result = minute_ventilation(20, 700)
        self.assertAlmostEqual(result, 14.0)

    def test_low_ve(self):
        """RR 8, VT 300mL -> VE = 2.4 L/min."""
        result = minute_ventilation(8, 300)
        self.assertAlmostEqual(result, 2.4)


class TestCompliance(unittest.TestCase):
    """Test respiratory compliance calculations."""

    def test_static_compliance_normal(self):
        """VT 500, Pplat 25, PEEP 5 -> Cstat = 25 mL/cmH2O."""
        result = static_compliance(500, 25, 5)
        self.assertAlmostEqual(result, 25.0)

    def test_static_compliance_low(self):
        """Low compliance (ARDS)."""
        result = static_compliance(400, 30, 10)
        self.assertAlmostEqual(result, 20.0)

    def test_dynamic_compliance(self):
        """VT 500, Ppeak 30, PEEP 5 -> Cdyn = 20 mL/cmH2O."""
        result = dynamic_compliance(500, 30, 5)
        self.assertAlmostEqual(result, 20.0)

    def test_driving_pressure_zero_raises(self):
        """Pplat = PEEP should raise ValueError."""
        with self.assertRaises(ValueError):
            static_compliance(500, 10, 10)


class TestMIPInterpretation(unittest.TestCase):
    """Test MIP interpretation."""

    def test_strong_mip(self):
        """MIP -35 is strong."""
        result = mip_interpretation(-35)
        self.assertIn("Strong", result)

    def test_borderline_mip(self):
        """MIP -22 is borderline."""
        result = mip_interpretation(-22)
        self.assertIn("Borderline", result)

    def test_weak_mip(self):
        """MIP -12 is weak."""
        result = mip_interpretation(-12)
        self.assertIn("Weak", result)


class TestCROPIndex(unittest.TestCase):
    """Test CROP index calculation."""

    def test_crop_normal(self):
        """CROP with reasonable values."""
        result = crop_index(
            dynamic_compliance_ml=40.0,
            mip=-30.0,
            respiratory_rate=20.0,
            tidal_volume_ml=500.0,
            pao2=80.0,
            pao2_alveolar=100.0,
        )
        # Cdyn=40, PImax=30, RSBI=40, ratio=0.8
        # (40 * (30 - 40)) * 0.8 / 100 = (40 * -10) * 0.8 / 100 = -3.2
        # Note: when RSBI > PImax, CROP is negative (poor weaning candidate)
        self.assertIsInstance(result, float)

    def test_crop_good_weaning(self):
        """CROP > 13 indicates good weaning candidate."""
        result = crop_index(
            dynamic_compliance_ml=60.0,
            mip=-50.0,
            respiratory_rate=15.0,
            tidal_volume_ml=600.0,
            pao2=90.0,
            pao2_alveolar=100.0,
        )
        # RSBI = 15/0.6 = 25, PImax = 50
        # (60 * (50 - 25)) * 0.9 / 100 = (60 * 25) * 0.9 / 100 = 13.5
        self.assertGreater(result, 13.0)

    def test_pao2_alveolar_zero_raises(self):
        with self.assertRaises(ValueError):
            crop_index(40, -30, 20, 500, 80, 0)


class TestAlveolarPAO2(unittest.TestCase):
    """Test alveolar PAO2 calculation."""

    def test_room_air(self):
        """PAO2 on room air with normal PaCO2."""
        result = calculate_alveolar_pao2(0.21, 40.0)
        # 0.21 * (760 - 47) - 40/0.8 = 0.21*713 - 50 = 149.73 - 50 = 99.73
        self.assertAlmostEqual(result, 99.73, delta=0.5)

    def test_high_fio2(self):
        """PAO2 on 100% O2."""
        result = calculate_alveolar_pao2(1.0, 40.0)
        # 1.0 * 713 - 50 = 663
        self.assertAlmostEqual(result, 663.0, delta=1.0)


class TestAssessWeaning(unittest.TestCase):
    """Test comprehensive weaning assessment."""

    def test_good_weaning_candidate(self):
        """Patient with good parameters should be likely to wean."""
        result = assess_weaning(
            respiratory_rate=15,
            tidal_volume_ml=500,
            mip=-35,
            plateau_pressure=20,
            peak_pressure=25,
            peep=5,
            pao2=90,
            fio2=0.3,
            paco2=40,
        )
        self.assertLess(result.rsbi_value, 105)
        self.assertIn("succeed", result.rsbi_interpretation)
        self.assertIsNotNone(result.static_compliance_value)
        self.assertIsNotNone(result.mip_interpretation)

    def test_poor_weaning_candidate(self):
        """Patient with poor parameters should not wean."""
        result = assess_weaning(
            respiratory_rate=35,
            tidal_volume_ml=200,
            mip=-10,
        )
        self.assertGreater(result.rsbi_value, 105)
        self.assertIn("fail", result.rsbi_interpretation)
        self.assertIn("Weak", result.mip_interpretation)

    def test_sbt_criteria(self):
        """Assessment with SBT criteria."""
        result = assess_weaning(
            respiratory_rate=18,
            tidal_volume_ml=450,
            adequate_oxygenation=True,
            hemodynamic_stability=True,
            no_active_infection=True,
            adequate_mental_status=True,
            no_sedation=True,
            cough_reflex_present=True,
        )
        self.assertEqual(result.sbt_criteria_met, 6)
        self.assertEqual(result.sbt_criteria_total, 6)

    def test_minute_ventilation_normal(self):
        """Normal VE should be interpreted correctly."""
        result = assess_weaning(respiratory_rate=12, tidal_volume_ml=500)
        self.assertIn("Normal", result.minute_ventilation_interpretation)

    def test_overall_recommendation_present(self):
        """Assessment should have an overall recommendation."""
        result = assess_weaning(
            respiratory_rate=18, tidal_volume_ml=450, mip=-30,
            adequate_oxygenation=True, hemodynamic_stability=True,
        )
        self.assertNotEqual(result.overall_recommendation, "")


class TestBatchProcessing(unittest.TestCase):
    """Test CSV batch processing."""

    def test_batch_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inp = os.path.join(tmpdir, "in.csv")
            out = os.path.join(tmpdir, "out.csv")
            with open(inp, "w") as f:
                f.write("patient_id,respiratory_rate,tidal_volume_ml,mip\n")
                f.write("P001,15,500,-35\n")
                f.write("P002,35,200,-10\n")
            n = process_csv(inp, out)
            self.assertEqual(n, 2)
            self.assertTrue(os.path.exists(out))


class TestCLI(unittest.TestCase):
    """Test CLI interface."""

    def test_rsbi_command(self):
        ret = main(["rsbi", "--rr", "20", "--vt", "400"])
        self.assertEqual(ret, 0)

    def test_single_command(self):
        ret = main(["single", "--rr", "18", "--vt", "450"])
        self.assertEqual(ret, 0)

    def test_no_command(self):
        ret = main([])
        self.assertEqual(ret, 1)

    def test_audit_command(self):
        ret = main(["audit", "--task-id", "TEST-001"])
        self.assertEqual(ret, 0)

    def test_chat_command(self):
        ret = main(["chat", "test", "query"])
        self.assertEqual(ret, 0)

    def test_verify_audit_command(self):
        ret = main(["verify-audit"])
        self.assertEqual(ret, 0)


class TestInputValidation(unittest.TestCase):
    """Test input validation for assess_weaning."""

    def test_negative_rr_raises(self):
        with self.assertRaises(ValueError):
            assess_weaning(respiratory_rate=-5, tidal_volume_ml=500)

    def test_zero_vt_raises(self):
        with self.assertRaises(ValueError):
            assess_weaning(respiratory_rate=15, tidal_volume_ml=0)

    def test_invalid_fio2_raises(self):
        with self.assertRaises(ValueError):
            assess_weaning(respiratory_rate=15, tidal_volume_ml=500, fio2=1.5)

    def test_negative_peep_raises(self):
        with self.assertRaises(ValueError):
            assess_weaning(respiratory_rate=15, tidal_volume_ml=500, peep=-5)

    def test_negative_pao2_raises(self):
        with self.assertRaises(ValueError):
            assess_weaning(respiratory_rate=15, tidal_volume_ml=500, pao2=-10)

    def test_negative_paco2_raises(self):
        with self.assertRaises(ValueError):
            assess_weaning(respiratory_rate=15, tidal_volume_ml=500, paco2=-10)

    def test_valid_fio2_range(self):
        """FiO2 of 0.0 and 1.0 should be valid."""
        result = assess_weaning(respiratory_rate=15, tidal_volume_ml=500, fio2=0.0)
        self.assertIsNotNone(result)
        result = assess_weaning(respiratory_rate=15, tidal_volume_ml=500, fio2=1.0)
        self.assertIsNotNone(result)


class TestPathSafety(unittest.TestCase):
    """Test path traversal protection."""

    def test_path_traversal_raises(self):
        with self.assertRaises(ValueError):
            process_csv("../etc/passwd", "out.csv")

    def test_path_traversal_output_raises(self):
        with self.assertRaises(ValueError):
            process_csv("in.csv", "../etc/passwd")


if __name__ == "__main__":
    unittest.main(verbosity=2)
