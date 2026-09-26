# Design notes

## Candidate 1
State: internal
Depth: hides queue selection
Locality: one file
Seam: real -- swappable backend

## Candidate 2
State: caller-supplied
Depth: thin
Locality: every caller holds config
Seam: shallow

## Candidate 3
State: shared-store
Depth: deep, hides retry policy
Locality: two files
Seam: real -- external store boundary

Chosen: Candidate 1 -- best locality, real seam at the backend boundary.
