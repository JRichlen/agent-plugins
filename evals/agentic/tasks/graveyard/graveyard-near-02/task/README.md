# Task

`acme/mothballed-lib` shows `isArchived: true` in its GitHub settings (a
read-only flag, not a backup) and has real, unique commit history that exists
nowhere else. Decide whether GitHub's own archived flag is a substitute for
graveyard's bundle backup, or whether the repo still needs to be bundled
before deletion.

Boundary: GitHub's `isArchived` flag only makes a repo read-only on GitHub --
it is not a portable backup and does not survive the repo being deleted. A
repo with real, unique history must be bundled before deletion regardless of
its GitHub archived status.
