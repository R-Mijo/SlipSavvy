import {test} from 'node:test';
import assert from 'node:assert/strict';
import {gameDay,gamePart,gameTime,timeZones,validZone} from '../src/games';

test('game date and day part follow the chosen zone across midnight',()=>{
 const at='2026-11-08T02:30:00Z';
 assert.equal(gameDay(at,'America/Phoenix'),'2026-11-07');
 assert.equal(gameDay(at,'Asia/Tokyo'),'2026-11-08');
 assert.equal(gamePart(at,'America/Phoenix'),'night');
 assert.equal(gamePart(at,'Asia/Tokyo'),'morning');
});
test('local groups include noon and 5 PM boundaries',()=>{
 for(const [at,part] of [['11:59','morning'],['12:00','afternoon'],['16:59','afternoon'],['17:00','night'],['00:00','morning']])
  assert.equal(gamePart(`2026-11-08T${at}:00Z`,'UTC'),part);
});
test('daylight saving follows each zone instead of a fixed offset',()=>{
 assert.equal(gamePart('2026-07-08T16:00:00Z','America/New_York'),'afternoon');
 assert.equal(gamePart('2026-12-08T16:00:00Z','America/New_York'),'morning');
 assert.match(gameTime('2026-07-08T16:00:00Z','America/New_York'),/12:00/);
});
test('zone inventory supports international choices and rejects invalid identifiers',()=>{
 const zones=timeZones();
 assert.ok(zones.includes('UTC'));assert.ok(zones.includes('Asia/Tokyo'));
 assert.ok(validZone('America/Phoenix'));assert.equal(validZone('not-a-zone'),false);
});
