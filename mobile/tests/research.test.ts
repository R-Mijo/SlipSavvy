import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {decodeResearch} from '../src/research';
import {reportFresh,type GameReports} from '../src/reports';
const fixture=()=>JSON.parse(readFileSync(new URL('./fixtures/nfl-research-v1.json',import.meta.url),'utf8'));
const event={sport:'americanfootball_nfl',startAt:'2026-11-08T18:00:00Z'};
const names=['Synthetic Runner'];

test('Python research snapshot retains reported statuses, separate file times and unavailable confirmation',()=>{
 const r=decodeResearch(fixture(),event,names)!;
 assert.equal(r.status,'partial');assert.equal(r.mapping?.gameId,'2026_10_MIA_BUF');
 assert.equal(r.players[0].status,'roster_snapshot');
 assert.equal(r.players[0].injury.record?.gameStatus,'Questionable');
 assert.equal(r.players[0].injury.record?.recordUpdatedAt,null);
 assert.notEqual(r.sources[0].providerUpdatedAt,r.sources[0].retrievedAt);
 assert.match(r.warnings.join(' '),/not establish.*healthy/);
 assert.equal(decodeResearch(undefined,event,names),undefined);
});

test('decoder rejects changed event/player identity, inferred health and unsafe source URLs',()=>{
 for(const mutate of [
  (r:any)=>r.mapping.startAt='2026-11-08T19:00:00Z',
  (r:any)=>r.players[0].requestedName='Another Runner',
  (r:any)=>r.players[0].gsisId='00-0000002',
  (r:any)=>r.players[0].injury.status='healthy',
  (r:any)=>r.players[0].injury.record.recordUpdatedAt=r.sources[0].retrievedAt,
  (r:any)=>r.sources[0].sourceUrl='https://evil.test/private',
  (r:any)=>r.sources[0].sourceUrl+='?token=private',
  (r:any)=>r.sources[0].timeBasis='confirmed_player_status',
  (r:any)=>r.sources[0].validUntil='2027-01-01T00:00:00Z',
  (r:any)=>r.coverage.injuries='complete',
  (r:any)=>r.sources.push(r.sources[0]),
  (r:any)=>r.teamInjuries.push(r.teamInjuries[0]),
  (r:any)=>r.status='complete',
 ]){const r=fixture();mutate(r);assert.throws(()=>decodeResearch(r,event,names));}
});

test('research expiration invalidates the report even while quotes remain current',()=>{
 const research=decodeResearch(fixture(),event,names)!;
 const now=Date.parse(research.sources[0].validUntil);
 const report={generatedAt:new Date(now-1000).toISOString(),legs:[],events:[{...event,context:{evidence:[]},
  research,gameScript:{status:'unavailable'},weather:{status:'unavailable'}}]} as unknown as GameReports;
 assert.equal(reportFresh(report,now-1),true);
 assert.equal(reportFresh(report,now),false);
});
