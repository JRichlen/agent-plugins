# Deprecated source-path adapters

The former product is retired. Only compatibility CLI adapters remain here.
Use [verification methods](../verify-before-claim/). Existing `.redgate/` records
remain readable as a legacy data format. Do not install this directory.

New calls use the same helper paths under `plugins/verify-before-claim/`.
Remove these adapters once known source-path callers migrate; retain legacy-data
reading while real records need it. Installed old copies are not changed here.
