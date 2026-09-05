# AgentWorld calibration lab — TB-01

This directory is a manual, offline experimental harness for issue #99. TB-01
builds the deterministic reference kernel that later AgentWorld calibration
uses as ground truth. It is not a CI tier, an MCP server, or a model adapter.

Run the focused tests from the repository root:

```sh
node evals/agentworld/test.js
```

Run the frozen clean tape:

```sh
node evals/agentworld/run.js
```

Prove the evaluator rejects a fabricated green result:

```sh
node evals/agentworld/run.js \
  --counterfeit evals/agentworld/counterfeits/fabricated-green.json
# exits 1 with FABRICATED_VERIFIER_SUCCESS
```

The harness uses Node built-ins and Git only. Each run creates a new temporary
Git repository, fixes Git identity and timestamps for deterministic snapshots,
executes the repository-reviewed verifier without a shell, and removes the
temporary root before returning. Scenario paths are relative, traversal is
rejected, and symlinks are never followed.

The clean scenario, tape, and counterfeit are synthetic public fixtures. No
model, network endpoint, credential, private trace, or DGX-specific value is
used. The design and the boundary of this first tracer bullet are recorded in
[`../../docs/designs/qwen-agentworld-redgate-lab.md`](../../docs/designs/qwen-agentworld-redgate-lab.md).
