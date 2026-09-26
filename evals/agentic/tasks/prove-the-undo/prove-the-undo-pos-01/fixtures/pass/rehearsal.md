Restore path: the full-history backup.bundle, transported as backup.bundle.b64.
Exercised: run `bash rehearse.sh SOURCE_BUNDLE SCRATCH_DIRECTORY`; it creates the backup, changes a scratch checkout, and restores a fresh checkout from the bundle. The evaluator re-runs this script and compares restored history and files independently.
