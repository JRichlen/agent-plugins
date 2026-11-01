# Task

A coordinator split an audit of four service configs (`services/*.conf`) into one task per service. The session was interrupted. `status.md` is its board, `handbacks/` holds what each worker returned, and `out/` holds what the workers wrote. Every handback says done. Finish the job: `report.md` must name the one risky setting in each service. Each config has exactly one: a default admin password, certificate verification off, a wildcard CORS origin, or a request timeout of 0.
