import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {propThresholdNotice} from '../src/odds';
import {decodeReports} from '../src/reports';
const fixture=()=>JSON.parse(readFileSync(new URL('./fixtures/player-settlement-v1.json',import.meta.url),'utf8'));

test('integer alternates remain uncertain regardless of metadata or a claimed opposite price',()=>{
 for(const market of ['player_pass_yds_alternate','player_rush_yds_alternate']){
  assert.match(propThresholdNotice({market,point:100,outcome:'Over'})!,/At exactly 100 yards/);
  assert.equal(propThresholdNotice({market,point:99.5,outcome:'Over'}),null);
 }
 assert.equal(propThresholdNotice({market:'player_rush_yds',point:100,outcome:'Over'}),null);
 assert.match(propThresholdNotice({market:'player_rush_yds',point:100.25,outcome:'Over'})!,/unsupported/);
});

test('actual Python report and legacy report text cannot imply a verified integer boundary',()=>{
 const d=fixture(),input={totalStake:'10.00',legs:d.legs.map((l:any)=>l.selection)};
 for(const legacy of [false,true]){
  if(legacy){delete d.legs[0].quote.settlement;d.legs[0].legImplication='Requires over 60 yards; exactly 60 pushes.';d.legs[0].seven[4].bullets=[d.legs[0].legImplication];}
  const r=decodeReports(d,input);
  assert.match(r.legs[0].legImplication,/At exactly 60 yards/);
  assert.match(r.legs[0].seven[4].bullets[0],/unverified/);
  assert.doesNotMatch(r.legs[0].seven[4].bullets[0],/exactly 60 pushes/);
  assert.equal(r.legs[0].modelWinProbability,null);
 }
 d.legs[0].modelWinProbability=.8;
 assert.throws(()=>decodeReports(d,input),/unverified prop threshold/);
});
