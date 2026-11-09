import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {checkQuote,quotePick,type Quote} from '../src/odds';
import {decodeReports,reportInput,type ReportInput} from '../src/reports';
const fixture=()=>JSON.parse(readFileSync(new URL('./fixtures/player-props-v1.json',import.meta.url),'utf8'));
const input=(d:any):ReportInput=>({totalStake:'30.00',legs:d.legs.map((l:any)=>l.selection)});

test('Python mixed-market contract preserves provider player identity through mobile selection and report decoding',()=>{
  const d=fixture(),now=Date.parse(d.generatedAt),picks=d.legs.map((l:any)=>quotePick(l.quote,now));
  const req=reportInput(picks,'30','',now);
  assert.deepEqual(req,input(d));
  const r=decodeReports(d,req);
  assert.equal(r.events.length,1);assert.equal(r.legs.length,4);
  assert.equal(r.legs[3].modelWinProbability,null);
  assert.match(r.legs[3].legImplication,/Synthetic Player A/);
  assert.match(r.legs[3].legImplication,/participation/i);
  assert.deepEqual(r.assessment.alternatives,[]);
});

test('two players with equal thresholds stay distinct; malformed prop identities cannot be selected',()=>{
  const d=fixture(),now=Date.parse(d.generatedAt),a=d.legs[2].quote as Quote;
  const b={...a,id:a.id+':other',playerName:'Synthetic Player B'};
  assert.equal(reportInput([quotePick(a,now),quotePick(b,now)],'10','',now).legs.length,2);
  for(const mutate of [
    (q:Quote)=>delete q.playerName,(q:Quote)=>q.playerName=' Ambiguous ',(q:Quote)=>q.playerName='X\nY',
    (q:Quote)=>q.playerIdentityBasis='verified_roster',(q:Quote)=>q.outcome='Yes',
    (q:Quote)=>q.point=NaN,(q:Quote)=>q.point=0,(q:Quote)=>q.sport='basketball_nba'
  ]){const q={...a};mutate(q);assert.throws(()=>checkQuote(q,now));}
});

test('decoder rejects a changed player even if every other selection and price matches',()=>{
  for(const location of ['selection','quote']){
    const d=fixture(),req=input(d);req.legs=structuredClone(req.legs);
    d.legs[2][location].playerName='Synthetic Player B';
    assert.throws(()=>decodeReports(d,req));
  }
});
