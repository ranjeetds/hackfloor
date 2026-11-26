"""hackfloor: adversarial probes for RL environment graders and agent benchmarks.

hackfloor runs policies that do not solve the task (empty answers, format-only output,
forged equality objects, test tampering, pytest hooks, early exits, reward-file writes)
through an environment's real grader and compares each against a matched control. A probe
that scores above its control is a finding; every finding can be replayed.
"""

from hackfloor.core import Attempt, Capability, TaskRef, Workspace
from hackfloor.probes.base import Probe, Variant, get_probes, register
from hackfloor.scan import ScanResult, scan

__version__ = "0.1.0.dev0"

__all__ = [
    "Attempt",
    "Capability",
    "Probe",
    "ScanResult",
    "TaskRef",
    "Variant",
    "Workspace",
    "__version__",
    "get_probes",
    "register",
    "scan",
]
