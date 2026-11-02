"""Expose the calibration workflow's offline controls to the free CI gate."""
import importlib.util
from pathlib import Path

source = Path(__file__).resolve().parents[2] / "evals/paid/calibration/test-workflow.py"
spec = importlib.util.spec_from_file_location("calibration_workflow_controls", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
CalibrationWorkflow = module.CalibrationWorkflow
