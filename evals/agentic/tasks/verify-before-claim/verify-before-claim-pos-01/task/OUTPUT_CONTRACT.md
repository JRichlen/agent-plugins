# Deliverable interface

Use the supplied `module.py` and `module_test.py`. Write `claim.md` identifying the actual command, test count, result, and narrowly supported claim. The verifier independently executes the tests and module behavior; a completion marker alone is insufficient.

The supplied test target is immutable: `module_test.py` and `inputs/module_test.py` name the same provided tests. Do not replace either copy or submit a substitute runner. In the computation tool, the original tests are read-only at `/inputs/module_test.py` (also `/inputs/inputs/module_test.py`). Copy `module.py` into `/work`, then run `PYTHONPATH=/work python3 -m unittest discover -s /inputs -p module_test.py` and record its actual result. Return `claim.md` and any necessary `module.py` edits; do not return modified tests. The grader independently executes the original supplied test target against the resulting module.
