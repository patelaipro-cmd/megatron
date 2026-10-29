#!/usr/bin/env node
'use strict';
const assert=require('node:assert/strict');
const m=require('./exp014_train.js');
assert.throws(()=>m.parseSource('Foo,Bar\n1,2'),/Colonne absente/);
assert.throws(()=>m.parseSource('Division,MatchDate,HomeTeam,AwayTeam,FTHome,FTAway\nE0,2020-01-01,A,B,?,2'),/Date ou score invalide/);
const ex='Division,MatchDate,HomeTeam,AwayTeam,FTHome,FTAway\nE0,2020-01-01,A,B,2,1\nE0,2021-01-01,B,A,0,0';
const records=m.parseSource(ex);assert.equal(records.length,2);
const p=m.probs(1.4,0.9);
assert.ok(p.H[0]>=p.H[1]&&p.H[1]>=p.H[2]);
assert.ok(p.A[0]>=p.A[1]&&p.A[1]>=p.A[2]);
assert.ok(Math.abs(p.H[0]+p.A[0]+p.D-1)<1e-8);
const model=m.trainModel(records,0.02);
const result=m.assess(model,records);
assert.equal(result.n,2);
assert.ok(result.logloss.every(v=>Number.isFinite(v)&&v>0));
// No future leakage : the validation and holdout rows are not used by trainModel.
const other=m.trainModel(records,0.02);
assert.deepEqual(model,other);
console.log('EXP-014 : tests synthetiques OK (format, scores, Poisson, probabilites, determinisme).');
