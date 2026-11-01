# Add source candidate packaging

The repository had no release workflow or release guide. The needed first slice
was narrower than automatic publishing: create an inspectable source candidate
from an exact commit, without granting a release token or executing that source.
The [baseline tree](https://github.com/JRichlen/agent-plugins/tree/37fcc9d3ce27ceb9309da189382b70a6e6fd2e48)
preserves that starting point; current implementation links below follow their
owning files rather than temporary draft commit IDs.

The implementation agent read and applied the current `codebase-design` method.
It compared repeated inline workflow logic, a large reusable workflow with mode
flags, and a shared offline contract with separate orchestration. The third
keeps file/Git packaging testable without conflating evaluation, release approval
and publication authority.

The [candidate feature proposal](https://github.com/JRichlen/agent-plugins/pull/153)
adds [`release/build_candidate.py`](../../release/build_candidate.py) and its
read-only workflow. The pure packaging boundary is Git objects in, deterministic
archive/manifest/checksums out. No model, registry or release API is involved.

## Try the committed feature

With Python and Git, from the repository root:

```sh
python3 -m unittest discover -s ci/tests -p 'test_release.py'
python3 release/build_candidate.py --revision HEAD --output /tmp/plugin-candidate-review
```

Choose an unused output directory. The initial implementation's four free tests passed; the current suite extends them with adversarial packaging controls:
real Git bytes and executable mode, repeatability despite a dirty working copy,
refusal of missing commits/overwrites/escaping links, and the workflow's
read-only/manual-staging boundary. Inspect `manifest.json` and verify
`SHA256SUMS` as shown in the [release guide](../../release/README.md).

Remove only that temporary output directory after reviewing it to undo this
exercise. It created no tag, release, plugin installation or deployment.

Packaging success is not release readiness. Version policy, the chosen channel,
exact-head checks, host support, outstanding failures and the previous qualified
revision still require review. The walkthrough demonstrates an actual bounded
feature and its tests; it is not an efficacy comparison against unaided coding.
