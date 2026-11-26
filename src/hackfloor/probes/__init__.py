"""Built-in probes. Importing this package registers them."""

from hackfloor.probes import answer, completion, leak, workspace
from hackfloor.probes.base import Probe, ProbeContext, Variant, get_probes, register

BUILTIN_PROBES: list[Probe] = [
    completion.EmptyProbe(),
    completion.FormatOnlyProbe(),
    completion.DumpProbe(),
    workspace.AlwaysEqualProbe(),
    workspace.EarlyExitProbe(),
    workspace.ConftestProbe(),
    workspace.TestEditProbe(),
    workspace.RewardFileProbe(),
    workspace.SkipTestProbe(),
    workspace.LookupTableProbe(),
    completion.EchoProbe(),
    completion.JudgeInjectionProbe(),
    leak.AnswerKeyProbe(),
    leak.GitHistoryProbe(),
    answer.WrongAnswerProbe(),
]

__all__ = ["BUILTIN_PROBES", "Probe", "ProbeContext", "Variant", "get_probes", "register"]
