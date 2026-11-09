import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {decodeReports as legacyDecoder} from './fixtures/main-a25b4c9-reports';
import {decodeReports} from '../src/reports';
const fixture=(name:string)=>JSON.parse(readFileSync(new URL('./fixtures/'+name,import.meta.url),'utf8'));
const input=(d:any)=>({totalStake:d.assessment.comparisonContext.totalStake,legs:d.legs.map((l:any)=>l.selection)});

test('frozen installed-era decoder reproduces the unnegotiated NWS failure and accepts the legacy wire response',()=>{
 const nws=fixture('venue-weather-v1.json');
 assert.throws(()=>legacyDecoder(nws,input(nws)),/Invalid weather units/);
 const legacy=fixture('venue-weather-legacy-v1.json');
 const r=legacyDecoder(legacy,input(legacy));
 assert.equal(r.events[0].weather.status,'unavailable');
 assert.equal(r.legs[0].matchStatus,'matched');
 assert.equal(r.legs[0].price?.americanOdds,'-110');
});

test('updated decoder accepts both actual wire formats without manufacturing gusts or probabilities',()=>{
 for(const name of ['venue-weather-v1.json','venue-weather-legacy-v1.json']){
  const d=fixture(name),r=decodeReports(d,input(d));
  assert.equal(r.legs[0].modelWinProbability,null);
  assert.equal(r.assessment.estimatedWinProbability,null);
  if(r.events[0].weather.status==='available'){
   assert.equal(r.events[0].weather.values?.windGustMph,null);
   assert.deepEqual(r.events[0].weather.windRangeMph,{low:5,high:10});
  }
 }
});
