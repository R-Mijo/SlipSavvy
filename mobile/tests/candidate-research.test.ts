import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {decodeReports,reportInput} from '../src/reports';
import {quotePick} from '../src/odds';
import {decodeResearch} from '../src/research';
import {reviewCandidate,rankCandidates,researchCandidates} from '../src/candidateResearch';
import type {Candidate} from '../src/tickets';
function setup(){
 const raw=JSON.parse(readFileSync(new URL('./fixtures/player-props-v1.json',import.meta.url),'utf8'));
 const now=Date.parse(raw.generatedAt),quotes=[raw.legs[2].quote];
 raw.legs=[raw.legs[2]];raw.legs[0].id='leg-1';raw.legs[0].selection.id='leg-1';
 const input=reportInput(quotes.map(q=>quotePick(q,now)),'10','',now);
 raw.assessment.comparisonContext={totalStake:'10.00',minimumTotalReturn:null,stakeBasis:'fixed_total_capital'};
 const report=decodeReports(raw,input);
 const source=JSON.parse(readFileSync(new URL('./fixtures/nfl-research-v1.json',import.meta.url),'utf8'));
 const research=decodeResearch(source,{sport:'americanfootball_nfl',startAt:source.mapping.startAt},['Synthetic Runner'])!;
 research.players[0].requestedName=quotes[0].playerName;
 research.mapping!.startAt=report.events[0].startAt;
 research.sources.forEach(s=>s.validUntil=new Date(now+600000).toISOString());
 report.events[0].research=research;
 report.events[0].weather={status:'not_applicable'};
 return {now,report,candidate:{quotes,decimal:2,returnAmount:20} as Candidate};
}
test('research distinguishes listed Out, Questionable, missing data and no listed injury',()=>{
 const {now,report,candidate}=setup();
 const reviewed=reviewCandidate(candidate,report,now);
 assert.equal(reviewed.review.blocked,false);assert.match(reviewed.review.reasons.join(' '),/Questionable/);
 const player=report.events[0].research!.players[0];player.injury.record!.gameStatus='Out';
 assert.equal(reviewCandidate(candidate,report,now).review.blocked,true);
 player.injury={status:'not_listed',record:null};
 const unknown=reviewCandidate(candidate,report,now);
 assert.match(unknown.review.reasons.join(' '),/does not establish health/);assert.ok(unknown.review.gaps>0);
 const unavailable=reviewCandidate(candidate,undefined,now);
 assert.equal(rankCandidates([unavailable,reviewed],20)[0],reviewed,'missing research cannot outrank known concerns by being silent');
});
test('changed prices are excluded and expired reports cannot retain a verified recommendation',()=>{
 const {now,report,candidate}=setup();report.legs[0].matchStatus='price_changed';
 assert.equal(reviewCandidate(candidate,report,now).review.blocked,true);
 const reviewed=reviewCandidate(candidate,report,now);
 const expired=reviewCandidate(reviewed,report,now+901000);
 assert.equal(expired.report,undefined);assert.equal(expired.review.gaps,100);
});
test('weather and context create traceable findings without modifying price-derived odds',()=>{
 const {now,report,candidate}=setup();
 report.events[0].weather={status:'available',retrievedAt:new Date(now).toISOString(),windRangeMph:{low:15,high:25}};
 report.events[0].context.facts=[{text:'Synthetic sourced context',evidenceIds:[]}];
 const reviewed=reviewCandidate(candidate,report,now);
 assert.match(reviewed.review.reasons.join(' '),/25 mph/);assert.match(reviewed.review.reasons.join(' '),/sourced context/);
 assert.equal(reviewed.decimal,candidate.decimal);assert.equal(reviewed.returnAmount,candidate.returnAmount);
});
test('review ordering uses gaps then listed concerns then target fit; no predictive probability is invented',()=>{
 const {now,report,candidate}=setup(),a=reviewCandidate(candidate,report,now),b=structuredClone(a);
 b.returnAmount=99;b.review.gaps=3;
 assert.equal(rankCandidates([b,a],100)[0],a);
 b.review.gaps=a.review.gaps;b.review.concerns=a.review.concerns+1;
 assert.equal(rankCandidates([b,a],100)[0],a);
 b.review.concerns=a.review.concerns;assert.equal(rankCandidates([a,b],100)[0],b);
});
test('research orchestration is bounded, tolerates unavailable evidence and honors cancellation',async()=>{
 const {candidate}=setup(),fresh=structuredClone(candidate);
 fresh.quotes.forEach(q=>{q.updatedAt=q.fetchedAt=new Date().toISOString();q.startAt=new Date(Date.now()+86400000).toISOString();});
 let calls=0;const c=new AbortController();
 const result=await researchCandidates([fresh,fresh,fresh,fresh],'10','100',c.signal,async()=>{calls++;throw Error('Unavailable');});
 assert.equal(calls,3);assert.ok(result.every(r=>r.review.gaps===100&&!r.report));
 c.abort();await assert.rejects(()=>researchCandidates([fresh],'10','100',c.signal,async()=>{throw Error('Should not fetch');}),/cancelled/);
});
