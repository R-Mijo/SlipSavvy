import {test} from 'node:test';
import assert from 'node:assert/strict';
import {checkQuote,quotePick,type Quote} from '../src/odds';
import {compare} from '../src/math';
import {reviewedPick} from '../src/review';
const now=Date.parse('2026-11-06T20:00:00Z');
const quote=():Quote=>({id:'a:book:h2h:Home',eventId:'a',event:'Away at Home',startAt:'2026-11-07T01:00:00Z',
  sport:'basketball_nba',market:'h2h',label:'Home',americanOdds:'-110',bookmaker:'Synthetic book',
  updatedAt:'2026-11-06T19:59:00Z',fetchedAt:'2026-11-06T20:00:00Z'});
test('Chosen feed line preserves price, event identity and freshness without inventing chance',()=>{
  const p=quotePick(quote(),now);
  assert.equal(p.kind,'feed');assert.equal(p.capturedAt,quote().fetchedAt);
  assert.match(p.event,/\(a\)/);assert.equal(p.fairPercent,'');
  assert.equal(compare([p],'10',false)[0].gross,'$19.09');
  assert.equal(compare([p],'10',false)[0].estimatedChance,null);
});
test('Stale, started, incomplete and invalid lines cannot be confirmed',()=>{
  for(const q of [{...quote(),updatedAt:'2026-11-06T18:00:00Z'},
    {...quote(),startAt:'2026-11-06T19:00:00Z'},{...quote(),bookmaker:''},
    {...quote(),americanOdds:'NaN'}])assert.throws(()=>checkQuote(q,now));
});
test('Two sportsbook quotes for the same event do not create an independent parlay',()=>{
  const a=quotePick(quote(),now),b=quotePick({...quote(),id:'other',bookmaker:'Other book'},now);
  assert.equal(compare([a,b],'10',true).length,2);
});

test('An optional user assumption is retained on a feed pick and validated',()=>{
  const p=quotePick(quote(),now,' 60 ');
  assert.equal(p.kind,'feed');assert.equal(p.fairPercent,'60');
  assert.equal(p.quote?.id,quote().id);
  assert.equal(compare([p],'10',false)[0].estimatedChance,'60.00%');
  assert.throws(()=>quotePick(quote(),now,'101'));
});

test('Provider event IDs match despite changed display names',()=>{
  const a=quotePick(quote(),now),b=quotePick({...quote(),id:'other',event:'Alternate display name'},now);
  assert.equal(compare([a,b],'10',true).length,2);
});

test('Feed/manual same-game names match with or without the provider suffix',()=>{
  const a=quotePick(quote(),now);
  for(const event of [' away  at HOME ',a.event]) {
    const b=reviewedPick({...a,event},'manual',new Date(now).toISOString());
    assert.equal(compare([a,b],'10',true).length,2,event);
  }
});

test('Distinct provider events sharing a matchup name remain distinct',()=>{
  const a=quotePick(quote(),now),b=quotePick({...quote(),id:'other',eventId:'different-game'},now);
  assert.equal(compare([a,b],'10',true).length,3);
});
