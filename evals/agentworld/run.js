#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const kernel = require('./kernel.js');

const HERE = __dirname;
const defaults = {
  scenario: path.join(HERE, 'scenarios/mcp-git/tb01-clean.json'),
  tape: path.join(HERE, 'tapes/mcp-git/tb01-clean.json'),
};

function parseArgs(argv) {
  const options = { ...defaults, counterfeit: null };
  for (let index = 0; index < argv.length; index++) {
    const arg = argv[index];
    if (arg === '--scenario' || arg === '--tape' || arg === '--counterfeit') {
      if (!argv[index + 1]) throw new Error(`${arg} requires a path`);
      options[arg.slice(2)] = path.resolve(argv[++index]);
    } else {
      throw new Error(`unknown argument: ${arg}`);
    }
  }
  return options;
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function main() {
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
    const scenario = readJson(options.scenario);
    const result = options.counterfeit
      ? kernel.evaluateCounterfeit(scenario, readJson(options.counterfeit))
      : kernel.runScenario(scenario, readJson(options.tape));
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
    process.exit((result.pass || (result.evaluation && result.evaluation.pass)) ? 0 : 1);
  } catch (error) {
    process.stderr.write(`agentworld-run: ${error.message}\n`);
    process.exit(2);
  }
}

main();
