# Deliverable interface

Write `dashboard.json` with a `cards` array. Each card has `id`, `owner`, and `state`, matching the supplied workstreams and workers. Preserve distinctions among pending, assigned, running, completed, verified, and blocked. No work has been executed in the starting state. A verified card additionally needs an `evidence` object naming an actual executable unittest `command`; the corresponding files must be present and its result must support verification. Do not manufacture running or verified work.
