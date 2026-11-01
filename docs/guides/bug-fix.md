# Repair a gallery capture that never launched

The scheduled gallery run [41280016961](https://github.com/JRichlen/agent-plugins/actions/runs/41280016961)
evaluated its packs, then all 13 direct capture invocations failed with
`Permission denied`. No gallery output or attestation was published.

## Follow the evidence

The tracked launcher had mode `100644`; the workflow executed it directly.
The [pre-fix source](https://github.com/JRichlen/agent-plugins/blob/37fcc9d3ce27ceb9309da189382b70a6e6fd2e48/.github/workflows/refresh-examples.yml)
is pinned independently of the rebased draft branches.
Existing fixture tests used Bash, so they did not expose that launch mismatch.
The implementation agent inspected both source and the available failed-run
artifact. This is a concrete cause, not an inference that all failures are
provider failures.

The [initial workflow proposal](https://github.com/JRichlen/agent-plugins/pull/152)
sets the executable bit, invokes capture through Bash and runs a real
selection/mode/help preflight before paid reachability or evaluations. It also
keeps raw result artifacts on later failure. The existing capture tool was
extended rather than replaced.

## Check the repair without buying another run

From the repository root with Python, Git and Bash:

```sh
python3 -m unittest discover -s ci/tests -p 'test_workflows.py'
python3 evals/paid/preflight_refresh.py --selected 'scope-fence'
```

The tests exercise missing executable mode, broken help, invalid/retired names,
fresh profiles, and pairs whose question/provider/fault status does not match.
The implementation run passed nine tests. These are process/source checks, not
a new paid gallery refresh. A schedule firing successfully still needs its own
run evidence.

## Keep the boundary visible

The failed artifact contains existing results, so recovery can avoid another
model run. Recovery must retain original source identity, distinguish recovery
time from unknown original capture time, and never promise an absent signature.
Read each arm’s criterion before comparing grades: calibration can reward the
opposite behavior, so two passes are neither equal-outcome evidence nor proof
of causal improvement.

For the current procedure and failure recovery, use the
[capture runbook](../../evals/paid/README.md) and [gallery maintenance guide](../examples/README.md).
For general diagnosis steps, load [diagnosing-bugs](../../plugins/diagnosing-bugs/).
This recorded repair was not retroactively labeled a run of that skill.
