import { american, number, type Pick } from './math';
import { checkQuote, isProp, propThresholdNotice } from './odds';
import { decodeResearch,type Research } from './research';
import { decodeVenue,type Venue } from './venue';

export const seats = ['Jeeves','Luna','Pax','Winston','Lisa','Diego','Gus'] as const;
export type ReportLegInput = {id:string;eventId:string;sport:string;bookmaker:string;market:string;
  outcome:string;point:number|null;americanOdds:string;playerName?:string};
export type ReportInput = {totalStake:string;minimumTotalReturn?:string;legs:ReportLegInput[]};
export type Evidence = {id:string;url:string;publisher:string;observedAt:string;validUntil:string};
export type Script = {status:'unavailable'|'model_supplied';mostLikelyScenarioId:string|null;
  validUntil?:string;scenarios:{id:string;summary:string;probability:number}[]};
export type Weather = {status:'available'|'unavailable'|'not_applicable';reason?:string;
  provider?:string;providerUpdatedAt?:string;validUntil?:string;hourUntil?:string;windRangeMph?:{low:number;high:number}|null;missingFields?:string[];
  retrievedAt?:string;hourAt?:string;attribution?:string;sourceUrl?:string;values?:Record<string,number|null>};
export type EventReport = {eventId:string;sport:string;homeTeam:string;awayTeam:string;startAt:string;
  startAtPhoenix:string;gameScript:Script;weather:Weather;research?:Research;venue?:Venue;context:{evidence:Evidence[];facts:{text:string;evidenceIds:string[]}[]}};
export type LegReport = {id:string;matchStatus:string;eventRef:string|null;legImplication:string;
  modelWinProbability:number|null;probabilityBasis:string;
  price:{americanOdds:string;decimalOdds:string;breakEvenPercent:number}|null;
  quote:{updatedAt:string;startAt:string}|null;quoteSource:{sourceUrl:string;updatedAt:string;retrievedAt:string}|null;
  seven:{seat:number;name:string;status:string;bullets:string[];evidenceIds:string[]}[]};
export type GameReports = {schemaVersion:1;generatedAt:string;events:EventReport[];legs:LegReport[];
  assessment:{status:'insufficient_data';estimatedWinProbability:null;alternatives:[];reasons:string[];
    comparisonContext:{totalStake:string;minimumTotalReturn:string|null;stakeBasis:'fixed_total_capital'}}};

function amount(value:string,maximum:number):string {
  if(!/^\d{1,8}(?:\.\d{1,2})?$/.test(value.trim())||Number(value)<=0||Number(value)>maximum)
    throw Error('Use a positive dollar amount with up to two decimal places.');
  return Number(value).toFixed(2);
}
export function reportInput(picks:Pick[],stake:string,floor:string,now=Date.now()):ReportInput {
  if(!picks.length||picks.length>8)throw Error('Add one to eight sportsbook lines to your parlay.');
  const result:ReportInput={totalStake:amount(stake,10000),legs:picks.map((p,i)=>{
    const q=p.quote;
    if(p.kind!=='feed'||!q)throw Error('Automatic research needs current sportsbook lines. Re-select manual or edited entries from the game browser.');
    checkQuote(q,now);
    if(!q.bookmakerKey||!q.outcome||!q.homeTeam||!q.awayTeam||
      (!['h2h','spreads','totals'].includes(q.market)&&!isProp(q.market))||!['fanduel','draftkings'].includes(q.bookmakerKey)||
      !/^[A-Za-z0-9_-]{1,100}$/.test(q.eventId))throw Error('Refresh the games to receive recognizable sportsbook lines.');
    const point=q.point??null;
    if(q.market==='h2h'?point!==null:typeof point!=='number'||!Number.isFinite(point)||Math.abs(point)>1000)
      throw Error('This line is missing its handicap or total. Refresh the games.');
    if((q.market==='totals'||isProp(q.market))&&(Number(point)<=0||!['Over','Under'].includes(q.outcome)))throw Error('Refresh this total before analysis.');
    return {id:'leg-'+(i+1),eventId:q.eventId,sport:q.sport,bookmaker:q.bookmakerKey,market:q.market,
      outcome:q.outcome,point,americanOdds:String(Number(q.americanOdds)),...(isProp(q.market)?{playerName:q.playerName!}:{})};
  })};
  if(floor.trim())result.minimumTotalReturn=amount(floor,10000000);
  const identities=result.legs.map(({sport,eventId,bookmaker,market,outcome,point,playerName})=>JSON.stringify([sport,eventId,bookmaker,market,outcome,point,playerName]));
  if(new Set(identities).size!==identities.length)throw Error('Remove duplicate selections before analysis.');
  if(new Set(result.legs.map(l=>l.sport+':'+l.eventId)).size>8||new Set(result.legs.map(l=>l.sport+':'+l.market)).size>8)
    throw Error('This preview analyzes up to eight games and eight sport/market combinations at once.');
  return result;
}

function record(value:unknown):Record<string,any> {
  if(!value||typeof value!=='object'||Array.isArray(value))throw Error('Invalid report response.');
  return value as Record<string,any>;
}
function str(value:unknown,max=1200):string {
  if(typeof value!=='string'||value.length>max)throw Error('Invalid report text.');
  return value;
}
function date(value:unknown):string {const s=str(value,80);if(!Number.isFinite(Date.parse(s)))throw Error('Invalid report timestamp.');return s;}
function list(value:unknown,max:number):any[] {if(!Array.isArray(value)||value.length>max)throw Error('Invalid report list.');return value;}
function probability(value:unknown):number {if(typeof value!=='number'||!Number.isFinite(value)||value<0||value>1)throw Error('Invalid model estimate.');return value;}
export function evidenceUrl(value:unknown):string|null {
  try {const u=new URL(str(value));if(u.protocol!=='https:'||!u.hostname||u.username||u.password||
    [...u.searchParams.keys()].some(k=>/key|token|secret|password|authorization/i.test(k)))return null;return u.href;}catch{return null;}
}
function script(value:unknown):Script {
  const s=record(value);
  if(s.status==='unavailable')return {status:'unavailable',mostLikelyScenarioId:null,scenarios:[]};
  if(s.status!=='model_supplied'||s.rankingScope!=='provided_model_scenarios')throw Error('Unsupported game script.');
  const scenarios=list(s.scenarios,6).map(v=>{const r=record(v);return {id:str(r.id,80),summary:str(r.summary,280),probability:probability(r.probability)};});
  if(scenarios.length<2||new Set(scenarios.map(s=>s.id)).size!==scenarios.length||Math.abs(scenarios.reduce((a,s)=>a+s.probability,0)-1)>1e-6)throw Error('Invalid model scenarios.');
  const leaders=scenarios.filter(v=>Math.abs(v.probability-Math.max(...scenarios.map(s=>s.probability)))<1e-9);
  const id=s.mostLikelyScenarioId;
  if(id!==null&&(leaders.length!==1||leaders[0].id!==id))throw Error('Invalid model scenario ranking.');
  return {status:'model_supplied',validUntil:date(s.validUntil),mostLikelyScenarioId:id===null?null:str(id,80),scenarios};
}
function weather(value:unknown,startAt:string):Weather {
  const w=record(value);
  if(w.status==='unavailable'||w.status==='not_applicable')return {status:w.status,reason:str(w.reason,100),...(w.validUntil?{validUntil:date(w.validUntil)}:{})};
  if(w.status!=='available'||w.kind!=='forecast')throw Error('Invalid weather report.');
  const values=record(w.values),units=record(w.units);
  if(w.provider==='NWS'){
    const ranges=[['temperatureF','°F',-150,160],['precipitationChance','%',0,100],['windSpeedMph','mph',0,250],['windGustMph','mph',0,300]] as const;
    for(const [key,unit,low,high] of ranges)
      if(units[key]!==unit||values[key]!==null&&(typeof values[key]!=='number'||!Number.isFinite(values[key])||values[key]<low||values[key]>high))throw Error('Invalid NWS weather values.');
    const interval=w.windRangeMph===null?null:record(w.windRangeMph);
    if(interval&&(values.windSpeedMph!==null||typeof interval.low!=='number'||typeof interval.high!=='number'||
      !Number.isFinite(interval.low)||!Number.isFinite(interval.high)||interval.low<0||interval.high>250||interval.low>=interval.high))throw Error('Invalid forecast wind range.');
    const missing=list(w.missingFields,4).map(v=>str(v,40));
    const expected=ranges.map(([key])=>key).filter(key=>values[key]===null&&!(key==='windSpeedMph'&&interval));
    if(expected.length===4)throw Error('No weather values available.');
    if(missing.length!==expected.length||new Set(missing).size!==missing.length||missing.some(key=>!expected.includes(key as any))||
      w.coverage!==(missing.length?'partial':'available'))throw Error('Invalid missing-weather fields.');
    const updated=date(w.providerUpdatedAt),retrieved=date(w.retrievedAt),until=date(w.validUntil),hour=date(w.hourAt),end=date(w.hourUntil);
    if(Date.parse(updated)>Date.parse(retrieved)+60000||Date.parse(until)<=Date.parse(retrieved)||Date.parse(until)>Date.parse(retrieved)+300000||
      Date.parse(until)>Date.parse(updated)+21600000||Date.parse(hour)>Date.parse(startAt)||Date.parse(end)<=Date.parse(startAt)||
      Date.parse(end)-Date.parse(hour)>3601000)throw Error('Invalid kickoff-hour forecast times.');
    if(!/^https:\/\/api\.weather\.gov\/gridpoints\/[A-Z]{3}\/-?\d{1,4},-?\d{1,4}\/forecast\/hourly$/.test(w.sourceUrl))throw Error('Invalid NWS source.');
    return {status:'available',provider:'NWS',values,providerUpdatedAt:updated,retrievedAt:retrieved,validUntil:until,hourAt:hour,hourUntil:end,
      windRangeMph:interval?{low:interval.low,high:interval.high}:null,missingFields:missing,sourceUrl:w.sourceUrl,attribution:str(w.attribution,100)};
  }
  for(const [key,unit,low,high] of [['temperature_2m','°F',-150,160],['precipitation_probability','%',0,100],
    ['wind_speed_10m','mp/h',0,250],['wind_gusts_10m','mp/h',0,300]] as const)
    if(units[key]!==unit||typeof values[key]!=='number'||!Number.isFinite(values[key])||values[key]<low||values[key]>high)throw Error('Invalid weather units.');
  const source=evidenceUrl(w.sourceUrl);if(!source)throw Error('Weather provenance is missing.');
  return {status:'available',values,retrievedAt:date(w.retrievedAt),hourAt:str(w.hourAt,80),attribution:str(w.attribution,100),sourceUrl:source};
}
export function decodeReports(value:unknown,input:ReportInput):GameReports {
  const d=record(value),a=record(d.assessment),comparison=record(a.comparisonContext);
  if(d.schemaVersion!==1||d.generationMethod!=='deterministic_evidence_findings'||a.status!=='insufficient_data'||
    a.estimatedWinProbability!==null||a.offeredParlayDecimalPrice!==null||list(a.alternatives,0).length||
    comparison.totalStake!==input.totalStake||comparison.minimumTotalReturn!==(input.minimumTotalReturn??null)||comparison.stakeBasis!=='fixed_total_capital')
    throw Error('Unsupported report version or ticket assessment.');
  const events:EventReport[]=list(d.events,8).map(v=>{const e=record(v),c=record(e.context);
    return {eventId:str(e.eventId,100),sport:str(e.sport,100),homeTeam:str(e.homeTeam,200),awayTeam:str(e.awayTeam,200),
      startAt:date(e.startAt),startAtPhoenix:date(e.startAtPhoenix),gameScript:script(e.gameScript),weather:weather(e.weather,date(e.startAt)),
      venue:decodeVenue(e.venue,e.research),
      research:decodeResearch(e.research,{sport:str(e.sport,100),startAt:date(e.startAt)},input.legs.filter(l=>l.sport===e.sport&&l.eventId===e.eventId&&l.playerName).map(l=>l.playerName!)),
      context:{evidence:list(c.evidence,24).map(v=>{const r=record(v),url=evidenceUrl(r.url);if(!url)throw Error('Evidence provenance is missing.');return {id:str(r.id,100),url,publisher:str(r.publisher,100),observedAt:date(r.observedAt),validUntil:date(r.validUntil)};}),
        facts:list(c.facts,8).map(v=>{const r=record(v);return {text:str(r.text,280),evidenceIds:list(r.evidenceIds,24).map(v=>str(v,100))};})}};
  });
  const eventIds=events.map(e=>e.sport+':'+e.eventId);
  if(new Set(eventIds).size!==eventIds.length||events.some(e=>!input.legs.some(l=>l.sport===e.sport&&l.eventId===e.eventId)))throw Error('Unexpected report event.');
  const rawLegs=list(d.legs,8);
  if(rawLegs.length!==input.legs.length)throw Error('The report does not match your parlay.');
  const legs:LegReport[]=rawLegs.map((v,index)=>{const r=record(v),expected=input.legs[index],selection=record(r.selection);
    if(r.id!==expected.id||Object.entries(expected).some(([k,value])=>selection[k]!==value))throw Error('The report selection changed unexpectedly.');
    const statuses=['matched','price_changed','quote_unavailable','ambiguous_match','event_identity_conflict','provider_unavailable','expired_during_report'];
    if(!statuses.includes(r.matchStatus))throw Error('Invalid match status.');
    if(['matched','price_changed','expired_during_report'].includes(r.matchStatus)!==(r.quote!==null))throw Error('Match status requires a current or captured quote.');
    const event=r.eventRef===null?undefined:events.find(e=>e.sport+':'+e.eventId===r.eventRef);
    if(r.eventRef!==null&&(!event||r.eventRef!==expected.sport+':'+expected.eventId))throw Error('Invalid report event reference.');
    let price:LegReport['price']=null,quote:LegReport['quote']=null,source:LegReport['quoteSource']=null;
    if(r.quote!==null){const q=record(r.quote),p=record(r.price),s=record(r.quoteSource);
      if(q.eventId!==expected.eventId||q.sport!==expected.sport||q.bookmakerKey!==expected.bookmaker||
        q.market!==expected.market||q.outcome!==expected.outcome||q.point!==expected.point||q.playerName!==expected.playerName||!event)throw Error('The current quote does not match your selection.');
      const odds=str(q.americanOdds,10),decimal=number(american(odds));
      if(p.americanOdds!==odds||!Number.isFinite(Number(p.decimalOdds))||Math.abs(Number(p.decimalOdds)-decimal)>1e-8||
        typeof p.breakEvenPercent!=='number'||!Number.isFinite(p.breakEvenPercent)||Math.abs(p.breakEvenPercent-100/decimal)>1e-6||
        (r.matchStatus==='matched'&&Number(odds)!==Number(expected.americanOdds)))throw Error('Invalid quoted price.');
      price={americanOdds:odds,decimalOdds:str(p.decimalOdds,40),breakEvenPercent:p.breakEvenPercent};
      quote={updatedAt:date(q.updatedAt),startAt:date(q.startAt)};
      const url=evidenceUrl(s.sourceUrl);if(!url||s.updatedAt!==q.updatedAt||s.retrievedAt!==q.fetchedAt)throw Error('Quote provenance does not match.');
      source={sourceUrl:url,updatedAt:date(s.updatedAt),retrievedAt:date(s.retrievedAt)};
    }else if(r.price!==null||r.quoteSource!==null)throw Error('A quote is required for price facts.');
    const estimate=r.modelWinProbability===null?null:probability(r.modelWinProbability);
    const thresholdNotice=propThresholdNotice(expected);
    if(thresholdNotice&&estimate!==null)throw Error('An unverified prop threshold cannot have a supported win estimate.');
    if(estimate!==null&&(r.matchStatus!=='matched'||event?.gameScript.status!=='model_supplied'||r.probabilityBasis!=='operator_supplied_model'))throw Error('Unsupported model probability.');
    const seven=list(r.seven,7).map((v,i)=>{const s=record(v);
      if(s.seat!==i+1||s.name!==seats[i]||!['ok','needs_data','blocked','not_applicable'].includes(s.status))throw Error('Invalid Sevenfold response.');
      const bullets=list(s.bullets,2).map(v=>str(v,1000));if(!bullets.length)throw Error('Missing Sevenfold response.');
      return {seat:s.seat,name:s.name,status:s.status,bullets,evidenceIds:list(s.evidenceIds,25).map(v=>str(v,120))};});
    if(seven.length!==7)throw Error('All seven responses are required.');
    if(thresholdNotice)seven[4]={...seven[4],status:'needs_data',bullets:[thresholdNotice+' No supported win estimate is available.']};
    const implication=str(r.legImplication);
    return {id:expected.id,matchStatus:r.matchStatus,eventRef:r.eventRef,legImplication:thresholdNotice?
      `${expected.playerName}: ${thresholdNotice} Participation, overtime, push and void rules need verification.`:implication,modelWinProbability:estimate,
      probabilityBasis:str(r.probabilityBasis,100),price,quote,quoteSource:source,seven};
  });
  return {schemaVersion:1,generatedAt:date(d.generatedAt),events,legs,assessment:{status:'insufficient_data',estimatedWinProbability:null,alternatives:[],
    reasons:list(a.reasons,8).map(v=>str(v)),comparisonContext:{totalStake:input.totalStake,minimumTotalReturn:input.minimumTotalReturn??null,stakeBasis:'fixed_total_capital'}}};
}

export function reportFresh(report:GameReports,now=Date.now()):boolean {
  const age=now-Date.parse(report.generatedAt);
  return age>=-60000&&age<=900000&&report.legs.every(l=>!l.quote||
    Date.parse(l.quote.startAt)>now&&now-Date.parse(l.quote.updatedAt)<=900000&&now-Date.parse(l.quote.updatedAt)>=-60000)&&
    report.events.every(e=>Date.parse(e.startAt)>now&&e.context.evidence.every(s=>Date.parse(s.validUntil)>now)&&
      (e.venue?.status!=='matched_catalog'||Date.parse(e.venue.validUntil)>now)&&
      (!e.weather.validUntil||Date.parse(e.weather.validUntil)>now)&&
      (!e.research||e.research.sources.every(s=>Date.parse(s.validUntil)>now))&&
      (e.gameScript.status!=='model_supplied'||Date.parse(e.gameScript.validUntil!)>now)&&
      (e.weather.status!=='available'||now-Date.parse(e.weather.retrievedAt!)<=300000));
}
export async function fetchReports(input:ReportInput,signal:AbortSignal):Promise<GameReports> {
  const base=process.env.EXPO_PUBLIC_ODDS_API_URL;
  if(!base||!/^https:\/\//.test(base))throw Error('Game reports are not connected yet.');
  const response=await fetch(base.replace(/\/$/,'')+'/api/game-reports',{method:'POST',signal,
    headers:{'Content-Type':'application/json','X-SlipSavvy-Weather-Schema':'nws-v1',Authorization:'Bearer '+(process.env.EXPO_PUBLIC_ODDS_PREVIEW_TOKEN??'')},body:JSON.stringify(input)});
  const raw=await response.text();if(raw.length>262144)throw Error('The game report was too large. Try again.');
  let data:unknown;try{data=JSON.parse(raw);}catch{throw Error('The report service is unavailable. Try again shortly.');}
  if(!response.ok){if(response.status===401)throw Error('Preview access needs to match the server settings.');
    if(response.status===429)throw Error('The report service is busy. Try again shortly.');
    throw Error('The report service could not analyze this parlay. Try again or refresh your lines.');}
  return decodeReports(data,input);
}
