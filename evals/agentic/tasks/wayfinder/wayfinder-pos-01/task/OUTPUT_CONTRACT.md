# Deliverable interface

Write `tickets.json` as an array with one ticket for each work item in `migration.json`. Each ticket has your chosen unique `id` (letters, digits, hyphens or underscores), the input item `work` key, a nonempty `type`, its supplied `status`, and `depends_on` as an array of your ticket IDs. Preserve the supplied work and dependencies. Write the current frontier to `frontier.md`, mentioning only the IDs that are open with all dependencies complete. IDs are your choice; no work is complete at the start.
