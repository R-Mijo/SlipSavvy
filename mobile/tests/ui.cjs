/* Exercise the actual exported app with a Python-generated report contract. */
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {setup,response,fixture,tick}=require('./app-helper.cjs');
async function app(){
 const data=await fixture(),quotes=data.legs.map(l=>l.quote),state={calls:[],status:200,hold:false,release:null};
 const a=await setup(async(url,options={})=>{
  if(String(url).endsWith('/api/sports'))return response({sports:[{key:'basketball_nba',title:'NBA'}]});
  if(String(url).includes('/api/odds?'))return response({quotes:quotes.filter(q=>q.market===new URL(url).searchParams.get('market'))});
  assert.match(String(url),/\/api\/game-reports$/);assert.equal(options.method,'POST');
  assert.equal(options.headers['Content-Type'],'application/json');assert.match(options.headers.Authorization,/^Bearer /);
  const input=JSON.parse(options.body);state.calls.push(input);
  const output=JSON.parse(JSON.stringify(data));output.assessment.comparisonContext={totalStake:input.totalStake,minimumTotalReturn:input.minimumTotalReturn??null,stakeBasis:'fixed_total_capital'};
  output.legs=input.legs.map(l=>{const leg=output.legs.find(r=>r.selection.eventId===l.eventId&&r.selection.market===l.market);return {...leg,id:l.id,selection:l};});
  if(state.hold)await new Promise(r=>state.release=r);
  return response(state.status===200?output:{error:'private-provider-failure'},state.status);
 });
 await a.click('tab-check');
 const addFour=async()=>{
  await a.click('sport-basketball_nba');await a.click('market-spreads');await a.click('game-game-a');await a.click('quote-'+quotes[0].id);
  await a.click('market-totals');await a.wait('quote-'+quotes[1].id);await a.click('quote-'+quotes[1].id);
  await a.click('game-game-b');await a.click('quote-'+quotes[3].id);
  await a.click('market-spreads');await a.wait('quote-'+quotes[2].id);await a.click('quote-'+quotes[2].id);
 };
 return {...a,state,addFour,quotes};
}
test('manual ticket keeps analyze below selections and collapses research without named personas',async()=>{
 const a=await app();try{
  await a.click('tab-check');await a.wait('browse-odds');
  for(const id of ['selection','event','odds','chance','add','review','confirm'])assert.equal(Boolean(a.find(id)),false,id);
  assert.equal(a.find('analyze-parlay').getAttribute('aria-disabled'),'true');
  await a.addFour();assert.match(a.find('parlay-count').textContent,/4\/8/);assert.ok(a.find('browse-odds').compareDocumentPosition(a.find('analyze-parlay'))&4);
  assert.equal(Boolean(a.find('report-options')),false);await a.click('analyze-parlay');await a.wait('game-reports');
  assert.equal(a.state.calls[0].legs.length,4);assert.equal(a.state.calls[0].minimumTotalReturn,undefined);
  assert.equal(Boolean(a.find('report-leg-0')),false);
  assert.equal(a.find('weather-info').getAttribute('aria-expanded'),'false');
  await a.click('analytic-info');
  assert.doesNotMatch(a.find('game-reports').textContent,/Sevenfold|Jeeves|Luna|Winston/);
  assert.equal(a.d.querySelectorAll('[data-testid^="report-leg-"]').length,4);
  await a.zone('Asia/Tokyo');assert.ok(Boolean(a.find('game-reports')),'zone changes presentation without invalidating research');
  await a.click('remove-3');assert.equal(Boolean(a.find('game-reports')),false);assert.match(a.find('parlay-count').textContent,/3\/8/);
  await a.click('tab-savvy');assert.ok(a.find('savvy-builder'));assert.equal(a.d.querySelectorAll('[role=tab]').length,2);
 }finally{a.close();}
});
test('access errors are safe and changing stake invalidates a report',async()=>{
 const a=await app();try{
  await a.addFour();a.state.status=401;await a.click('analyze-parlay');await a.wait('report-error');
  assert.match(a.find('report-error').textContent,/Preview access/);assert.doesNotMatch(a.d.body.textContent,/private-provider/);
  a.state.status=200;await a.click('analyze-parlay');await a.wait('game-reports');
  await a.click('stake-20');assert.equal(Boolean(a.find('game-reports')),false);
  await a.click('analyze-parlay');await a.wait('game-reports');assert.equal(a.state.calls.at(-1).totalStake,'20.00');
 }finally{a.close();}
});
test('cancelled and obsolete requests cannot resurrect reports for a changed parlay',async()=>{
 const a=await app();try{
  await a.addFour();a.state.hold=true;await a.click('analyze-parlay');await a.wait('cancel-analysis');
  await a.click('cancel-analysis');a.state.release();await tick();assert.equal(Boolean(a.find('game-reports')),false);
  await a.click('analyze-parlay');await a.wait('cancel-analysis');await a.click('remove-0');a.state.release();await tick();
  assert.equal(Boolean(a.find('game-reports')),false);assert.equal(Boolean(a.find('report-error')),false);
 }finally{a.close();}
});
