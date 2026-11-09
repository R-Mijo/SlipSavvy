import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {decodeReports,reportFresh,type ReportInput} from '../src/reports';
const fixture=()=>JSON.parse(readFileSync(new URL('./fixtures/venue-weather-v1.json',import.meta.url),'utf8'));
const input=(d:any):ReportInput=>({totalStake:'10.00',legs:d.legs.map((l:any)=>l.selection)});

test('Python venue/weather contract preserves the actual venue, NWS wind range and missing gusts',()=>{
 const d=fixture(),r=decodeReports(d,input(d)),e=r.events[0];
 assert.equal(e.venue?.status,'matched_catalog');
 assert.equal(e.weather.provider,'NWS');
 assert.deepEqual(e.weather.windRangeMph,{low:5,high:10});
 assert.equal(e.weather.values?.windGustMph,null);
 assert.equal(e.weather.values?.windSpeedMph,null);
 assert.deepEqual(e.weather.missingFields,['windGustMph']);
 assert.equal(reportFresh(r,Date.parse(d.generatedAt)),true);
 assert.equal(reportFresh(r,Date.parse(e.weather.validUntil!)),false);
 assert.equal(r.assessment.estimatedWinProbability,null);
});

test('decoder rejects changed venue identity, unverified roof state, invented weather and incorrect hour/source',()=>{
 for(const mutate of [
  (d:any)=>d.events[0].venue.stadiumId='MIN01',
  (d:any)=>d.events[0].venue.roofState='closed',
  (d:any)=>d.events[0].venue.sources=[],
  (d:any)=>d.events[0].venue.validUntil='2027-01-01T00:00:00Z',
  (d:any)=>d.events[0].weather.values.windSpeedMph=7.5,
  (d:any)=>d.events[0].weather.values.windGustMph=0,
  (d:any)=>d.events[0].weather.hourAt='2026-11-08T22:00:00Z',
  (d:any)=>d.events[0].weather.sourceUrl='https://api.weather.gov.evil.test/forecast',
  (d:any)=>d.events[0].weather.providerUpdatedAt='2026-11-09T00:00:00Z',
 ]){const d=fixture(),req=input(d);mutate(d);assert.throws(()=>decodeReports(d,req));}
});
