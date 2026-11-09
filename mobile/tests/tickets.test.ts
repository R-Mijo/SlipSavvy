import {test} from 'node:test';
import assert from 'node:assert/strict';
import {candidates,oddsScore,ticketPrice,selectionReason} from '../src/tickets';
import {quotePick,type Quote} from '../src/odds';
const now=Date.now();
function q(eventId:string,odds='-110',patch:Partial<Quote>={}):Quote{return {id:eventId+':'+odds,eventId,event:'Away at Home',sport:'americanfootball_nfl',market:'h2h',outcome:'Home',point:null,
  homeTeam:'Home',awayTeam:'Away',bookmaker:'FanDuel',bookmakerKey:'fanduel',label:'Home',americanOdds:odds,
  startAt:new Date(now+86400000).toISOString(),updatedAt:new Date(now).toISOString(),fetchedAt:new Date(now).toISOString(),...patch};}
test('five score bands derive only from American prices; extreme prices remain nonzero',()=>{
  assert.equal(oddsScore('+400').score,20);assert.equal(oddsScore('-400').score,80);
  assert.equal(oddsScore('+100').score,50);assert.equal(oddsScore('+900').label,'Very low');
  assert.equal(oddsScore('-900').label,'Very high');assert.ok(oddsScore('+100000').score>0);
  assert.throws(()=>oddsScore('0'));assert.throws(()=>oddsScore('NaN'));
});
test('ticket price rejects same-game, mixed books, expired prices and edited prices',()=>{
  const a=quotePick(q('a','+100'),now),b=quotePick(q('b','+100'),now);
  assert.deepEqual(ticketPrice([a,b],now),{decimal:4,score:25});
  assert.equal(ticketPrice([a,{...b,quote:{...b.quote!,eventId:'a'}}],now),null);
  assert.equal(ticketPrice([a,{...b,quote:{...b.quote!,bookmakerKey:'draftkings'}}],now),null);
  assert.equal(ticketPrice([a,b],now+901000),null);assert.equal(ticketPrice([{...a,odds:'-200'}],now),null);
});
test('bounded builder fits a target without invented odds, repeated games or mixed books',()=>{
  const pool=[q('a','+100'),q('a','+200'),q('b','+100'),q('c','+300',{bookmakerKey:'draftkings'})];
  const result=candidates(pool,'americanfootball_nfl','fanduel',2,10,40,now);
  assert.equal(result[0].returnAmount,40);assert.equal(result[0].quotes.length,2);
  for(const r of result){assert.equal(new Set(r.quotes.map(q=>q.eventId)).size,2);assert.ok(r.quotes.every(q=>pool.includes(q)&&q.bookmakerKey==='fanduel'));}
  const nearest=candidates(pool,'americanfootball_nfl','fanduel',2,10,10000,now);
  assert.equal(nearest[0].returnAmount,60);assert.equal(candidates(pool,'americanfootball_nfl','fanduel',3,10,100,now).length,0);
});
test('unknown milestones, duplicate IDs, identity conflicts and malformed report lines stay out',()=>{
  const prop=q('a','+100',{market:'player_rush_yds_alternate',playerName:'A Player',playerIdentityBasis:'provider_description',outcome:'Over',point:60});
  assert.equal(candidates([prop,q('b')],'americanfootball_nfl','fanduel',2,10,50,now).length,0);
  const valid={...prop,point:60.5};assert.equal(candidates([valid,q('b')],'americanfootball_nfl','fanduel',2,10,50,now).length,1);
  for(const pool of [[q('a'),q('a'),q('b')],[q('a'),q('a','+100',{homeTeam:'Conflicting'}),q('b')],[q('a','-110',{market:'totals',point:null}),q('b')]])
    assert.equal(candidates(pool,'americanfootball_nfl','fanduel',2,10,50,now).length,0);
  assert.throws(()=>candidates([],'americanfootball_nfl','fanduel',2,10,0,now));
});
test('main/alternate rationale compares real supplied prices with a fixed stake',()=>{
  const main=q('a','+100',{market:'player_pass_yds',playerName:'A Player',playerIdentityBasis:'provider_description',outcome:'Over',point:200.5});
  const alt={...main,id:'alt',market:'player_pass_yds_alternate',point:150.5,americanOdds:'-200',label:'Over 150.5'};
  const r={quotes:[main,q('b','+100')],decimal:4,returnAmount:40};
  assert.match(selectionReason(main,r,[main,alt],10,40),/\$30.00/);
  assert.match(selectionReason(main,r,[main],10,40),/No comparable/);
});
