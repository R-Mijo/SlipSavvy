export type InjuryRecord={gsisId:string;team:string;playerName:string|null;position:string|null;gameStatus:string|null;
  practiceStatus:string|null;primaryInjury:string|null;practiceInjury:string|null;recordUpdatedAt:null};
export type ResearchPlayer={requestedName:string;status:'roster_snapshot'|'unmapped'|'ambiguous'|'unavailable';
  gsisId:string|null;team:string|null;rosterWeek:number|null;rosterStatus:string|null;
  injury:{status:'reported'|'not_listed'|'ambiguous'|'identity_conflict'|'coverage_unknown'|'unavailable';record:InjuryRecord|null}};
export type Research={status:'partial'|'unavailable'|'not_applicable';reason:string|null;
  mapping:{gameId:string;season:number;week:number;seasonType:'REG';homeTeamCode:string;awayTeamCode:string;startAt:string}|null;
  sources:{id:string;dataset:string;sourceUrl:string;licenseUrl:string;attribution:string;providerUpdatedAt:string;
    retrievedAt:string;metadataCheckedAt:string;validUntil:string;recordUpdatedAt:null;sha256:string;timeBasis:'file_snapshot_not_record_confirmation'}[];
  coverage:Record<'schedule'|'injuries'|'roster',string>;
  players:ResearchPlayer[];teamInjuries:InjuryRecord[];listedInjuryCount:number;injuriesTruncated:boolean;warnings:string[]};
function record(v:any):Record<string,any>{if(!v||typeof v!=='object'||Array.isArray(v))throw Error('Invalid NFL research.');return v;}
function str(v:any,max=280):string{if(typeof v!=='string'||!v.length||v.length>max)throw Error('Invalid NFL research text.');return v;}
function optional(v:any):string|null{return v===null?null:str(v,120);}
function date(v:any):string{const d=str(v,80);if(!Number.isFinite(Date.parse(d)))throw Error('Invalid research timestamp.');return d;}
function list(v:any,max:number):any[]{if(!Array.isArray(v)||v.length>max)throw Error('Invalid research list.');return v;}
function int(v:any,low:number,high:number):number{if(!Number.isInteger(v)||v<low||v>high)throw Error('Invalid research number.');return v;}
function gsis(v:any):string{const s=str(v,20);if(!/^00-\d{7}$/.test(s))throw Error('Invalid roster identity.');return s;}
function team(v:any):string{const s=str(v,3);if(!/^[A-Z]{2,3}$/.test(s))throw Error('Invalid research team.');return s;}
function injury(value:any):InjuryRecord{
  const r=record(value);if(r.recordUpdatedAt!==null)throw Error('Unsupported injury confirmation time.');
  return {gsisId:gsis(r.gsisId),team:team(r.team),playerName:optional(r.playerName),position:optional(r.position),
    gameStatus:optional(r.gameStatus),practiceStatus:optional(r.practiceStatus),primaryInjury:optional(r.primaryInjury),
    practiceInjury:optional(r.practiceInjury),recordUpdatedAt:null};
}
export function decodeResearch(value:any,event:{sport:string;startAt:string},names:string[]):Research|undefined{
  if(value===undefined)return undefined; // Older backend responses remain supported.
  const r=record(value);
  if(!['partial','unavailable','not_applicable'].includes(r.status))throw Error('Unsupported research state.');
  const c=record(r.coverage),coverage={} as Research['coverage'];
  for(const name of ['schedule','injuries','roster'] as const){
    if(!['unavailable','not_requested','file_snapshot','matched','missing','stale','ambiguous','invalid','coverage_unknown','identity_unmatched'].includes(c[name]))throw Error('Invalid research coverage.');
    coverage[name]=c[name];
  }
  const mapping=r.mapping===null?null:(()=>{const m=record(r.mapping);
    const season=int(m.season,2020,2100),week=int(m.week,1,18),home=team(m.homeTeamCode),away=team(m.awayTeamCode);
    if(m.status!=='matched'||m.seasonType!=='REG'||event.sport!=='americanfootball_nfl'||home===away||
      Date.parse(date(m.startAt))!==Date.parse(event.startAt)||m.gameId!==`${season}_${String(week).padStart(2,'0')}_${away}_${home}`)
      throw Error('Research does not match the game.');
    return {gameId:m.gameId,season,week,seasonType:'REG' as const,homeTeamCode:home,awayTeamCode:away,startAt:m.startAt};
  })();
  const sources=list(r.sources,3).map(v=>{const s=record(v),dataset=str(s.dataset,20);
    const files:Record<string,string>={schedule:'schedules/games.csv',roster:`rosters/roster_${mapping?.season}.csv`,injuries:`injuries/injuries_${mapping?.season}.csv`};
    if(!mapping||!(dataset in files)||s.sourceUrl!==`https://github.com/nflverse/nflverse-data/releases/download/${files[dataset]}`||
      s.licenseUrl!=='https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md'||s.recordUpdatedAt!==null||
      s.timeBasis!=='file_snapshot_not_record_confirmation'||typeof s.sha256!=='string'||!(/^[0-9a-f]{64}$/).test(s.sha256))throw Error('Unsupported research source.');
    const updated=Date.parse(date(s.providerUpdatedAt)),retrieved=Date.parse(date(s.retrievedAt)),checked=Date.parse(date(s.metadataCheckedAt)),until=Date.parse(date(s.validUntil));
    if(updated>retrieved+60000||updated>checked+60000||until<=checked||until>checked+900000)throw Error('Inconsistent research times.');
    return {id:str(s.id,100),dataset,sourceUrl:s.sourceUrl as string,licenseUrl:s.licenseUrl as string,
      attribution:str(s.attribution),providerUpdatedAt:date(s.providerUpdatedAt),retrievedAt:date(s.retrievedAt),
      metadataCheckedAt:date(s.metadataCheckedAt),validUntil:date(s.validUntil),recordUpdatedAt:null,sha256:s.sha256 as string,
      timeBasis:'file_snapshot_not_record_confirmation' as const};
  });
  if(new Set(sources.map(s=>s.dataset)).size!==sources.length||new Set(sources.map(s=>s.id)).size!==sources.length)
    throw Error('Ambiguous research sources.');
  const datasets=new Set(sources.map(s=>s.dataset));
  if((datasets.has('injuries')!==['file_snapshot','coverage_unknown'].includes(coverage.injuries))||
    (datasets.has('roster')!==(coverage.roster==='file_snapshot'))||mapping&&coverage.schedule!=='matched')throw Error('Inconsistent source coverage.');
  const players:ResearchPlayer[]=list(r.players,8).map(v=>{const p=record(v),i=record(p.injury);
    if(!names.includes(p.requestedName)||!['roster_snapshot','unmapped','ambiguous','unavailable'].includes(p.status)||
      !['reported','not_listed','ambiguous','identity_conflict','coverage_unknown','unavailable'].includes(i.status))throw Error('Unexpected research player.');
    const mapped=p.status==='roster_snapshot',id=p.gsisId===null?null:gsis(p.gsisId),club=p.team===null?null:team(p.team);
    const week=p.rosterWeek===null?null:int(p.rosterWeek,1,18);
    if(mapped?(!mapping||!datasets.has('roster')||!id||!club||!week||week>mapping.week||![mapping.homeTeamCode,mapping.awayTeamCode].includes(club)):
      (id!==null||club!==null||week!==null||p.rosterStatus!==null||i.status!=='unavailable'))throw Error('Unsupported player mapping.');
    const row=i.record===null?null:injury(i.record);
    if((i.status==='reported')!==(row!==null)||(i.status!=='unavailable'&&!datasets.has('injuries'))||
      row&&(row.gsisId!==id||row.team!==club||row.playerName!==p.requestedName))throw Error('Injury identity conflict.');
    return {requestedName:str(p.requestedName,120),status:p.status,gsisId:id,team:club,rosterWeek:week,
      rosterStatus:optional(p.rosterStatus),injury:{status:i.status,record:row}};
  });
  if(new Set(players.map(p=>p.requestedName)).size!==players.length)throw Error('Ambiguous player mapping.');
  const injuries=list(r.teamInjuries,32).map(injury),count=int(r.listedInjuryCount,0,20000);
  if(new Set(injuries.map(i=>i.team+':'+i.gsisId)).size!==injuries.length)throw Error('Ambiguous injury records.');
  if(typeof r.injuriesTruncated!=='boolean'||r.injuriesTruncated!==(count>32)||injuries.length!==Math.min(count,32)||
    injuries.some(i=>!mapping||!datasets.has('injuries')||![mapping.homeTeamCode,mapping.awayTeamCode].includes(i.team)))
    throw Error('Invalid injury coverage.');
  if(r.status==='partial'?(!mapping||!datasets.has('schedule')):(mapping!==null||sources.length||players.length||injuries.length))
    throw Error('Inconsistent research coverage.');
  return {status:r.status,reason:r.reason===null?null:str(r.reason,100),mapping,sources,coverage,players,teamInjuries:injuries,
    listedInjuryCount:count,injuriesTruncated:r.injuriesTruncated,warnings:list(r.warnings,8).map(v=>str(v))};
}
