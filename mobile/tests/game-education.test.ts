import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {gameEducation} from '../src/gameEducation';
import {quotePick} from '../src/odds';
import {decodeReports,reportInput} from '../src/reports';
test('conditional explanations preserve thresholds and never claim a forecast or availability',()=>{
 const raw=JSON.parse(readFileSync(new URL('./fixtures/player-props-v1.json',import.meta.url),'utf8'));
 const picks=raw.legs.map((l:any)=>quotePick(l.quote,Date.parse(raw.generatedAt)));
 const report=decodeReports(raw,reportInput(picks,raw.assessment.comparisonContext.totalStake,raw.assessment.comparisonContext.minimumTotalReturn??'',Date.parse(raw.generatedAt)));
 const e=gameEducation(picks[2],report.legs[2],report.events[0])!;
 assert.match(e.basis,/Not a predicted/);assert.match(e.why,/220.5/);assert.match(e.risk,/not established/);
 assert.equal(gameEducation(picks[2],{...report.legs[2],matchStatus:'price_changed'},report.events[0]),null);
 const under={...picks[2],quote:{...picks[2].quote!,outcome:'Under'}};
 assert.match(gameEducation(under,report.legs[2],report.events[0])!.script,/challenge an Under/);
});
