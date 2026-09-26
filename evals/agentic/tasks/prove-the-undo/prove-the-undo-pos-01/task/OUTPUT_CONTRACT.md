# Deliverable interface

This offline task supplies the original two-commit Git history in `source-history.json`; the token is a synthetic fixture marker, never a real credential. Recreate it exactly (branch, commit messages, author/committer and dates as supplied). Prepare a full-history backup and a rewritten history with credentials.txt removed from both commits while preserving app.py and the two substantive changes. Do not perform a remote network push.

Return `backup.bundle.b64` and `rewritten.bundle.b64`: standard base64 text containing actual Git bundles of the original and sanitized main branch. This text transport preserves the real binary bundles for independent restoration. Return `rehearse.sh SOURCE_BUNDLE SCRATCH_DIRECTORY`: it must create `SCRATCH_DIRECTORY/backup.bundle`, a `changed/` checkout with a deliberate tracked app.py edit, and a `restored/` checkout restored from the backup. The original source bundle path is absolute. The harness runs the script in a fresh sandbox and independently compares commit graphs, original/changed/restored content, and rewritten history.

Write `rehearsal.md` identifying the restore path and executable rehearsal, and `outcome.md` accurately stating local preparation and that the remote force-push remains pending. A written assertion of zero differences or remote completion is insufficient.
