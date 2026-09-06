"""evals.agentic.framework — the vocabulary export surface.

Integration-owned. This package re-exports ONLY the frozen vocabulary from
``contract.py``; every other module is imported by path
(``from evals.agentic.framework import analysis``) so that any lane can run its
own tests against ``contract.py`` alone (contract §6).
"""
from .contract import *  # noqa: F401,F403  — the vocabulary in contract §2 via __all__
from .contract import __all__  # noqa: F401  — integration keeps this in sync
