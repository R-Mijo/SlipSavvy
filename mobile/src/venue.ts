export type Venue={status:'unavailable'|'operator_supplied';reason:string}|{status:'matched_catalog';name:string;stadiumId:string;
  roof:'outdoor'|'indoor'|'retractable';roofState:'unknown';latitude:number|null;longitude:number|null;checkedAt:string;validUntil:string;
  sources:{kind:string;url:string;publisher:string}[];scheduleSourceId:string};
function date(v:any):string{if(typeof v!=='string'||!Number.isFinite(Date.parse(v)))throw Error('Invalid venue timestamp.');return v;}
export function decodeVenue(v:any,research:any):Venue|undefined{
  if(v===undefined)return undefined;
  if(!v||typeof v!=='object')throw Error('Invalid venue.');
  if(['unavailable','operator_supplied'].includes(v.status)){
    if(typeof v.reason!=='string'||v.reason.length>100)throw Error('Invalid venue state.');
    return {status:v.status,reason:v.reason};
  }
  const mapping=research?.mapping,schedule=research?.sources?.filter((s:any)=>s.dataset==='schedule');
  if(v.status!=='matched_catalog'||v.basis!=='exact_event_schedule_and_reviewed_venue_catalog'||
    typeof v.name!=='string'||!v.name.length||v.name.length>150||typeof v.stadiumId!=='string'||!v.stadiumId.length||v.stadiumId.length>40||
    !mapping||mapping.reportedVenue?.id!==v.stadiumId||mapping.reportedVenue?.name!==v.name||schedule?.length!==1||
    schedule[0].id!==v.scheduleSourceId||!['outdoor','indoor','retractable'].includes(v.roof)||v.roofState!=='unknown')throw Error('Venue does not match event research.');
  const checked=date(v.checkedAt),until=date(v.validUntil);
  if(Date.parse(until)<=Date.parse(checked)||Date.parse(until)>Date.parse(checked)+30*86400000||
    Date.parse(until)>Date.parse(schedule[0].validUntil))throw Error('Invalid venue evidence lifetime.');
  if(v.roof==='outdoor'?typeof v.latitude!=='number'||!Number.isFinite(v.latitude)||Math.abs(v.latitude)>90||
    typeof v.longitude!=='number'||!Number.isFinite(v.longitude)||Math.abs(v.longitude)>180:v.latitude!==null||v.longitude!==null)
    throw Error('Invalid venue coordinates.');
  if(!Array.isArray(v.sources)||!v.sources.length||v.sources.length>4)throw Error('Missing venue sources.');
  const sources:{kind:string;url:string;publisher:string}[]=v.sources.map((s:any)=>{
    if(typeof s.url!=='string'||s.url.length>1000)throw Error('Invalid venue URL.');
    const u=new URL(s.url);
    if(!['roof','coordinates'].includes(s.kind)||u.protocol!=='https:'||u.username||u.password||
      [...u.searchParams.keys()].some(k=>/key|token|secret|password|authorization/i.test(k))||
      typeof s.publisher!=='string'||!s.publisher.length||s.publisher.length>100)throw Error('Invalid venue source.');
    return {kind:s.kind as string,url:s.url as string,publisher:s.publisher as string};
  });
  if(!sources.some(s=>s.kind==='roof')||v.roof==='outdoor'&&!sources.some(s=>s.kind==='coordinates'))throw Error('Incomplete venue provenance.');
  return {status:'matched_catalog',name:v.name,stadiumId:v.stadiumId,roof:v.roof,roofState:'unknown',latitude:v.latitude,longitude:v.longitude,
    checkedAt:checked,validUntil:until,sources,scheduleSourceId:v.scheduleSourceId};
}
