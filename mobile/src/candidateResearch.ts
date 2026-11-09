import type {Candidate} from './tickets';
import {eventKey} from './tickets';
import {isProp,quotePick} from './odds';
import {fetchReports,reportFresh,reportInput,type GameReports} from './reports';

export type ReviewedCandidate=Candidate & {report?:GameReports;review:{blocked:boolean;concerns:number;gaps:number;reasons:string[]}};
/** Evidence-readiness rules, not a trained model, win forecast, or betting edge. */
export function reviewCandidate(candidate:Candidate,report?:GameReports,now=Date.now()):ReviewedCandidate {
  const reasons:string[]=[];let blocked=false,concerns=0,gaps=0;
  if(!report||!reportFresh(report,now))return {...candidate,report:undefined,review:{blocked:false,concerns:0,gaps:100,
    reasons:['Research could not be verified for this ticket. It remains a price-based candidate; retry analysis before using it.']}};
  const events=new Map(report.events.map(e=>[e.sport+':'+e.eventId,e]));
  // Only decoded reports for this exact candidate may enter this function.
  if(report.legs.length!==candidate.quotes.length)throw Error('Candidate research does not match its ticket.');
  candidate.quotes.forEach((q,i)=>{
    const leg=report.legs[i],event=events.get(eventKey(q));
    if(leg.eventRef!==eventKey(q)||leg.matchStatus!=='matched'||Number(leg.price?.americanOdds)!==Number(q.americanOdds)){
      blocked=true;reasons.push(`${q.label}: the current price or game could not be matched. Refresh this line.`);return;
    }
    const research=event?.research;
    if(q.sport==='americanfootball_nfl') {
      if(!research?.mapping){gaps++;reasons.push(`${q.event}: the exact NFL schedule and injury evidence are unavailable.`);}
      else if(research.coverage.injuries!=='file_snapshot'){gaps++;reasons.push(`${q.event}: team/week injury coverage is incomplete.`);}
      else if(research.listedInjuryCount){concerns++;reasons.push(`${q.event}: ${research.listedInjuryCount} injury records are listed. Their effect on this line has not been modeled.`);}
      if(isProp(q.market)){
        const player=research?.players.find(p=>p.requestedName===q.playerName),row=player?.injury.record;
        if(row){
          const status=(row.gameStatus??'').trim().toLowerCase();
          if(status==='out'){blocked=true;reasons.push(`${q.playerName} is listed Out in the injury snapshot. Excluded from the automatic suggestion; current participation still needs confirmation.`);}
          else if(['questionable','doubtful'].includes(status)){concerns+=status==='doubtful'?2:1;reasons.push(`${q.playerName} is listed ${row.gameStatus}. Check availability before using this prop.`);}
          else {gaps++;reasons.push(`${q.playerName}: an injury row is available, but current participation is not confirmed.`);}
        }else{gaps++;reasons.push(`${q.playerName}: player availability is unverified. Not listed does not establish health.`);}
      }
      if(event?.weather.status==='unavailable'||!event?.weather){gaps++;reasons.push(`${q.event}: applicable weather or roof evidence is unavailable.`);}
      else if(event.weather.status==='available'){
        const wind=event.weather.windRangeMph?.high??event.weather.values?.wind_speed_10m;
        if(typeof wind==='number'&&wind>=20){concerns++;reasons.push(`${q.event}: forecast wind reaches ${wind} mph. Review weather-sensitive lines; no numerical outcome adjustment is applied.`);}
      }
    }else if(!event?.context.facts.length){gaps++;reasons.push(`${q.event}: matchup research is not connected for this sport.`);}
    if(event?.context.facts.length)reasons.push(`${q.event}: ${event.context.facts.length} sourced context facts are available in Analytic Info.`);
  });
  if(!reasons.length)reasons.push('Current prices match and the available source checks returned no listed concern. Research is still incomplete, not proof of a good bet.');
  return {...candidate,report,review:{blocked,concerns,gaps,reasons:[...new Set(reasons)]}};
}
export function rankCandidates(items:ReviewedCandidate[],target:number):ReviewedCandidate[] {
  // Missing evidence is never interpreted as reassuring. Every rule is exposed in the UI.
  return items.slice().sort((a,b)=>Number(a.review.blocked)-Number(b.review.blocked)||
    a.review.gaps-b.review.gaps||a.review.concerns-b.review.concerns||
    Math.abs(a.returnAmount-target)-Math.abs(b.returnAmount-target));
}
export async function researchCandidates(items:Candidate[],stake:string,target:string,signal:AbortSignal,
  fetcher:typeof fetchReports=fetchReports):Promise<ReviewedCandidate[]> {
  const result:ReviewedCandidate[]=[];
  // Sequential: respect the report service's concurrency limit and reuse its source cache.
  for(const candidate of items.slice(0,3)){
    if(signal.aborted)throw Error('Research cancelled.');
    let report:GameReports|undefined;
    try {report=await fetcher(reportInput(candidate.quotes.map(q=>quotePick(q)),stake,target),signal);}catch{
      if(signal.aborted)throw Error('Research cancelled.');
    }
    result.push(reviewCandidate(candidate,report));
  }
  // The first report may have expired while a later request was running.
  return rankCandidates(result.map(r=>reviewCandidate(r,r.report)),Number(target));
}
