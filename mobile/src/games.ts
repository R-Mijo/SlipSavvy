import type {Quote} from './odds';
import {fallbackZones} from './timeZones';
export type DayPart='morning'|'afternoon'|'night';
export const dayParts:DayPart[]=['morning','afternoon','night'];
export function validZone(zone:string):boolean {try{new Intl.DateTimeFormat('en-US',{timeZone:zone});return Boolean(zone);}catch{return false;}}
export function deviceZone():string {try{const zone=Intl.DateTimeFormat().resolvedOptions().timeZone;return validZone(zone)?zone:'UTC';}catch{return 'UTC';}}
export function timeZones():string[] {
  const supported=(Intl as typeof Intl & {supportedValuesOf?:(key:string)=>string[]}).supportedValuesOf;
  let zones=fallbackZones;try{if(supported)zones=supported('timeZone');}catch{}
  return [...new Set(['UTC',deviceZone(),...zones.filter(validZone)])].sort();
}
export function gameDay(startAt:string,zone:string):string {
  const parts=new Intl.DateTimeFormat('en-US',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(startAt));
  const get=(type:string)=>parts.find(p=>p.type===type)!.value;
  return `${get('year')}-${get('month')}-${get('day')}`;
}
export function gamePart(startAt:string,zone:string):DayPart {
  const hour=Number(new Intl.DateTimeFormat('en-US',{timeZone:zone,hour:'numeric',hourCycle:'h23'}).format(new Date(startAt)));
  return hour<12?'morning':hour<17?'afternoon':'night';
}
export function dayLabel(day:string):string {return new Date(day+'T12:00:00Z').toLocaleDateString('en-US',{timeZone:'UTC',weekday:'short',month:'short',day:'numeric',year:'numeric'});}
export function gameTime(startAt:string,zone:string):string {return new Date(startAt).toLocaleTimeString('en-US',{timeZone:zone,hour:'numeric',minute:'2-digit',timeZoneName:'short'});}
export function localTimestamp(startAt:string,zone:string):string {return new Date(startAt).toLocaleString('en-US',{timeZone:zone,year:'numeric',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'});}
export function gameChoices(quotes:Quote[]):Quote[] {
  return [...new Map([...quotes].sort((a,b)=>Date.parse(a.startAt)-Date.parse(b.startAt)||a.event.localeCompare(b.event)).map(q=>[q.eventId,q])).values()];
}
