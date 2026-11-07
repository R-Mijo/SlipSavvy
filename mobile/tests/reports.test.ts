import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {decodeReports,reportInput,reportFresh,evidenceUrl,seats,type ReportInput} from '../src/reports';
import {quotePick} from '../src/odds';
const fixture=()=>JSON.parse(readFileSync(new URL('./fixtures/game-reports-v1.json',import.meta.url),'utf8'));
const input=(d:any):ReportInput=>({totalStake:'10.00',minimumTotalReturn:'90.00',legs:d.legs.map((l:any)=>l.selection)});

test('real Python contract gives four leg reports with shared research and all seven checks',()=>{
 const d=fixture(),r=decodeReports(d,input(d));
 assert.equal(r.legs.length,4);assert.equal(r.events.length,2);
 assert.equal(r.legs[0].eventRef,r.legs[1].eventRef);
 assert.deepEqual(r.legs[0].seven.map(s=>s.name),[...seats]);
 assert.equal(r.legs[0].modelWinProbability,null);
 assert.equal(r.assessment.estimatedWinProbability,null);
 assert.equal(reportFresh(r,Date.parse(d.generatedAt)),true);
 assert.equal(reportFresh(r,Date.parse(d.generatedAt)+901000),false);
});
test('request uses exact provider identifiers and structured outcomes, never labels',()=>{
 const d=fixture(),now=Date.parse(d.generatedAt);
 const picks=d.legs.map((l:any)=>quotePick(l.quote,now));
 const req=reportInput(picks,'10','90',now);
 assert.deepEqual(req,input(d));
 picks[0].label='A label that must not be parsed';
 assert.deepEqual(reportInput(picks,'10','90',now),req);
 assert.throws(()=>reportInput([...picks,picks[0]],'10','',now),/duplicate/);
 assert.throws(()=>reportInput(picks,'10','',now+901000),/current/);
 delete picks[0].quote;
 assert.throws(()=>reportInput(picks,'10','',now),/research needs/);
});
test('decoder rejects changed identities, missing council members, fabricated whole-ticket forecasts and broken prices',()=>{
 for(const mutate of [
  (d:any)=>d.legs[0].selection.point=-7.5,
  (d:any)=>d.legs[0].seven.pop(),
  (d:any)=>d.legs[0].seven[6].name='External Gus',
  (d:any)=>d.legs[0].price.breakEvenPercent=Number.NaN,
  (d:any)=>d.legs[0].modelWinProbability=.9,
  (d:any)=>d.assessment.estimatedWinProbability=.2,
  (d:any)=>d.legs[0].quoteSource.sourceUrl='https://example.test/?apiKey=private',
 ]){const d=fixture(),req=input(fixture());mutate(d);assert.throws(()=>decodeReports(d,req));}
});
test('report expires when evidence or game start expires, and unsafe links stay closed',()=>{
 const d=fixture(),r=decodeReports(d,input(d)),now=Date.parse(d.generatedAt);
 r.events[0].context.evidence.push({id:'e',url:'https://example.test',publisher:'Synthetic',observedAt:d.generatedAt,validUntil:new Date(now-1).toISOString()});
 assert.equal(reportFresh(r,now),false);
 const fresh=decodeReports(d,input(d));fresh.events[0].startAt=new Date(now).toISOString();
 assert.equal(reportFresh(fresh,now),false);
 for(const url of ['http://example.test','javascript:alert(1)','https://user:password@example.test','https://example.test?token=secret'])assert.equal(evidenceUrl(url),null);
 assert.equal(evidenceUrl('https://the-odds-api.com/'),'https://the-odds-api.com/');
});
