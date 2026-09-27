"""
Unit Tests for Benchmark Suite Runner and External Baseline Comparator.
"""
import unittest
import tempfile
from pathlib import Path

from experiments.benchmark import (
    LunarRegistrationBenchmarkRunner,
    BenchmarkTestCase,
    BenchmarkDifficulty,
    ExternalReferenceRecord
)


class TestBenchmark(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.runner = LunarRegistrationBenchmarkRunner(output_dir=self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_standard_suite_definition(self):
        """Verify standard suite contains multi-scenario test cases."""
        cases = self.runner.get_standard_suite()
        self.assertGreaterEqual(len(cases), 5)
        scenarios = [c.scenario_name for c in cases]
        self.assertIn("illumination", scenarios)
        self.assertIn("rotation_translation", scenarios)
        self.assertIn("scale", scenarios)
        self.assertIn("combined", scenarios)

    def test_external_reference_baselines(self):
        """Verify external reference baselines are cleanly labeled with citations."""
        baselines = self.runner.get_external_reference_baselines()
        self.assertGreaterEqual(len(baselines), 2)
        for b in baselines:
            self.assertEqual(b.classification_tag, "EXTERNAL_REFERENCE")
            self.assertTrue(len(b.source_citation) > 0)
            self.assertGreater(b.published_rmse_px, 0.0)

    def test_run_single_benchmark_case(self):
        """Verify execution of a single benchmark test case."""
        tc = BenchmarkTestCase(
            case_id="TEST-01",
            scenario_name="rotation_translation",
            difficulty=BenchmarkDifficulty.STANDARD,
            description="Test rotation case",
            seed=42,
            image_size=256,
            target_rmse_threshold=2.0
        )
        suite_res = self.runner.run_benchmark_suite(cases=[tc], suite_name="Test Single Case Suite")
        self.assertEqual(suite_res.total_cases, 1)
        self.assertGreaterEqual(suite_res.passed_cases, 1)
        self.assertEqual(suite_res.success_rate_percentage, 100.0)
        self.assertLess(suite_res.mean_rmse_px, 2.0)


if __name__ == "__main__":
    unittest.main()
