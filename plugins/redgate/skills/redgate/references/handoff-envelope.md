# The handoff envelope

Pointers only; no transcripts. A child re-reads what the environment already
holds — the parent ships references, not content.

## DOWN (parent → child)

| Field | Content |
|---|---|
| `notes` | free text, **first** — reasoning fields precede verdict fields |
| `criteria` | the numbered criteria, **verbatim** |
| `criteria_path` + `sha` | where they live and their pinned hash |
| `check_cmd` | the one criterion this child owns |
| `context[]` | ≤5 `path:line` or URL pointers |
| `boundary` | one line: where this child's work stops |
| `lease[]` | file globs this child may write |
| `budget` | `{tool_calls, attempts, tokens, depth_remaining}` |

## UP (child → parent)

| Field | Content |
|---|---|
| `notes` | free text, **first**, ≤80 words |
| `status` | the child's own verdict |
| `results[]` | `{id, PASS\|FAIL\|UNVERIFIABLE, evidence_ref}` |
| `artifacts[]` | paths, never contents |
| `unmet[]` | criterion ids still red |
| `blocked` | ≤2 lines |

## The rules that matter

- **The 300-token cap applies to `notes`/`results`/`blocked` only.** Criteria
  text is **excluded from the cap** and never counted against it. Capping it
  forces paraphrase, and paraphrase of criteria is goal drift wearing a
  compression argument.
- **Criteria travel verbatim, once, at the tail** of the child prompt,
  alongside `criteria_path` + `sha`. A child with filesystem access re-reads
  the file; duplicating at head *and* tail is redundant once the path travels.
- **Reasoning before verdicts.** Constrained decoding degrades reasoning when
  the verdict is emitted first.
- **Evidence travels as `out_ref` paths**, never as pasted command output.
  Long output blows the envelope and buries the signal.
- `machine-voice` compresses `notes`. It never touches criteria.
