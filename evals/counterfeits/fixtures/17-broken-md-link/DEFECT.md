# Counterfeit: a markdown link points at a file that doesn't exist

**Gate exercised:** cheap tier section 7b — every local relative markdown
link (`[text](target)`) in every plugin `.md` file resolves to a real file.

**Defect:** a markdown-syntax link to a non-existent reference file is added
to the baseline plugin's SKILL.md. This is the exact shape of the
context-handoff regression this gate was added to catch: a reference link
with a wrong relative depth (or, here, a wrong filename) that nothing
resolves before shipping.

EXPECT_FAIL_SUBSTRING=which does not resolve to a real file
