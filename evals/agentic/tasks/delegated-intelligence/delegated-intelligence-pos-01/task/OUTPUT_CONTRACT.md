# Deliverable interface

Write `report.md`: a table `| service | risky setting | source |` with one row per service in `services/`, where `risky setting` names the setting key and its value and `source` is the `out/` file the row came from.

Keep `status.md` true to what is on disk: one row per task, with the state and attempt count of each. Work that is already complete stays as it is. For any task you run or re-run, write the instructions you hand its worker to `briefs/<service>.md`, and that worker writes its result to `out/<service>.md`. Do not edit `services/`.
