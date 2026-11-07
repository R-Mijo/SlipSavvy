const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const {setup,response,shifted}=require('./app-helper.cjs');

test('mobile weather displays ranged winds and missing gusts with actual venue sources, then unknown roof state',async()=>{
 const raw=JSON.parse(await fs.readFile(path.join(__dirname,'fixtures/venue-weather-v1.json'),'utf8'));
 const report=shifted(raw,Date.now()-Date.parse(raw.generatedAt));
 let current=report;
 const a=await setup(async(url,options)=>{
  const u=new URL(url);
  if(u.pathname==='/api/sports')return response({sports:[{key:'americanfootball_nfl',title:'NFL'}]});
  if(u.pathname==='/api/game-reports')return response(current);
  return response({quotes:[report.legs[0].quote]});
 });
 try{
  await a.wait('browse-odds');await a.click('sport-americanfootball_nfl');await a.click('game-synthetic-weather');
  await a.click('quote-'+report.legs[0].quote.id);await a.click('analyze-parlay');await a.wait('game-reports');
  assert.match(a.find('venue-weather').textContent,/Lumen Field/);
  assert.match(a.find('venue-weather').textContent,/5–10 mph/);
  assert.match(a.find('venue-weather').textContent,/gusts: Unavailable/);
  assert.match(a.find('venue-weather').textContent,/Forecast updated.*retrieved/);
  await a.click('venue-sources-toggle');
  assert.match(a.find('venue-weather').textContent,/Washington State Public Stadium Authority/);
  current=structuredClone(report);const e=current.events[0];
  e.venue.name='Lucas Oil Stadium';e.venue.stadiumId='IND00';e.venue.roof='retractable';e.venue.latitude=null;e.venue.longitude=null;
  e.research.mapping.reportedVenue={id:'IND00',name:'Lucas Oil Stadium'};
  e.weather={status:'unavailable',reason:'roof_state_unknown'};
  await a.click('analyze-parlay');await a.wait('venue-weather');
  assert.match(a.find('venue-weather').textContent,/roof state is unverified/);
  assert.doesNotMatch(a.find('venue-weather').textContent,/outdoor weather is not applied/);
 }finally{a.close();}
});
