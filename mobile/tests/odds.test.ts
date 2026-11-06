import {test} from 'node:test';
import assert from 'node:assert/strict';
import {checkQuote,quotePick,type Quote} from '../src/odds';
import {compare} from '../src/math';
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
