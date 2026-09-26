# T12/T15 negative-control fixture

A card whose outcome_verifier and adoption_verifier are the SAME script (an
unconditional "return True"). Completeness counted by file existence alone
would accept this; validate_card must reject it as vacuous instead.
