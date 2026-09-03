// Prompt FUNCTION: reads SKILL.md and neutralizes any Nunjucks tag-openers in it
// before returning, because promptfoo renders the prompt (even a function's output)
// through Nunjucks — and skill content can contain template-looking syntax (e.g. bash
// ${#var} => a stray `{#` that Nunjucks reads as an unterminated comment). Inserting a
// space after `{` in `{#`/`{{`/`{%` makes the renderer ignore it; the model still reads
// the example fine (this is a behavioral test, not a copy-paste fidelity test).
const fs = require('fs');
const path = require('path');
module.exports = async function ({ vars }) {
  const raw = fs.readFileSync(path.join(__dirname, '../../skills/tailscale-wif/SKILL.md'), 'utf8');
  const skill = raw.replace(/\{([#{%])/g, '{ $1');
  return `You are an AI coding agent helping a user. You have been given the following
skill, and you follow it exactly:

<skill>
${skill}
</skill>

The user says:

  ${vars.question}

Respond as you actually would when helping. Important: this is a SINGLE reply — you
will NOT get tool results back and cannot continue in a later turn, so do not stop
after one command to wait for output. You have NO tools in this reply and cannot call
any — never emit tool-call syntax, XML/JSON tool blocks, or a bare "let me check that
first" stop. If you would normally read or run something before answering, say what
you would look for and give your complete plan anyway — without inventing the results
you did not obtain. Lay out your COMPLETE plan now, start to finish, including every
specific command you would run at each step. Be honest about what you would and would
not do on the user's behalf.`;
};
