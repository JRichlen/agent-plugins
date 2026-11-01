// Exercise patched Git dependencies without loading Promptfoo or calling models.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const cp = require('node:child_process');
const modules = path.resolve(process.argv[2]);
const {simpleGit} = require(path.join(modules, 'simple-git'));
const {vulnerabilityCheck} = require(path.join(modules, '@simple-git/argv-parser'));
const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'tool-git-smoke-'));
const env = {PATH:process.env.PATH, HOME:directory, GIT_CONFIG_NOSYSTEM:'1',
  GIT_CONFIG_GLOBAL:process.platform === 'win32' ? 'NUL' : '/dev/null'};
for (const name of ['SystemRoot','COMSPEC','PATHEXT','TEMP','TMP']) {
  if (process.env[name]) env[name] = process.env[name];
}
(async () => {
  try {
    const run = (...args) => cp.execFileSync('git', ['-c','commit.gpgsign=false','-C',directory,...args], {env,stdio:'pipe'});
    run('init','-q');
    fs.writeFileSync(path.join(directory,'fixture.txt'),'fixture\n');
    run('add','.');
    run('-c','user.name=Tool smoke','-c','user.email=fixture@example.invalid','commit','-qm','fixture');
    const libraryEnv = {...env};
    delete libraryEnv.GIT_CONFIG_GLOBAL;
    delete libraryEnv.GIT_CONFIG_NOSYSTEM;
    const git = simpleGit({baseDir:directory}).env(libraryEnv);
    assert.match(await git.revparse(['HEAD']), /^[0-9a-f]{40}\s*$/);
    assert.equal((await git.status()).isClean(), true);
    assert.equal((await git.log()).total, 1);
    assert.equal((await git.getConfig('core.repositoryformatversion')).value, '0');
    assert(vulnerabilityCheck(['status'], {VISUAL:'/nonexistent-ci-editor'}).some(v => v.category === 'allowUnsafeEditor'));
    const unsafe = simpleGit({baseDir:directory,config:['trailer.audit.cmd=/nonexistent-ci-helper']}).env(libraryEnv);
    await assert.rejects(unsafe.raw(['interpret-trailers','--trailer','audit:fixture']), error => error.plugin === 'unsafe' && /allowUnsafeCommandBinaries/.test(error.message));
    console.log('Patched Git API + VISUAL/trailer rejection: PASS (no model calls)');
  } finally {
    assert(directory.startsWith(path.join(os.tmpdir(),'tool-git-smoke-')));
    fs.rmSync(directory,{recursive:true,force:true});
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
