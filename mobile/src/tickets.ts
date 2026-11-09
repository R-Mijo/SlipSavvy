import {american,number,type Pick} from './math';
import {checkQuote,propThresholdNotice,quotePick,type Quote} from './odds';
import {reportInput} from './reports';

export const levels = [
  {label:'Very low',color:'#B83A48'}, {label:'Low',color:'#E77743'},
  {label:'Moderate',color:'#E9BD45'}, {label:'High',color:'#8CCC55'},
  {label:'Very high',color:'#40DE86'},
];
export function oddsScore(odds:string) {
  const score=100/number(american(odds));
  return {score,...levels[Math.min(4,Math.floor(score/20))]};
}
export const eventKey=(q:Quote)=>q.sport+':'+q.eventId;
export function ticketPrice(picks:Pick[],now=Date.now()):{decimal:number;score:number}|null {
  if(!picks.length)return null;
  const events=new Set<string>(),books=new Set<string>();let price=1;
  try {for(const pick of picks){
    const q=pick.quote;if(!q||pick.kind!=='feed'||Number(pick.odds)!==Number(q.americanOdds))return null;
    checkQuote(q,now);
    if(!['fanduel','draftkings'].includes(q.bookmakerKey??'')||events.has(eventKey(q)))return null;
    events.add(eventKey(q));books.add(q.bookmakerKey!);price*=number(american(q.americanOdds));
  }}catch{return null;}
  return books.size===1?{decimal:price,score:100/price}:null;
}
export type Candidate={quotes:Quote[];decimal:number;returnAmount:number};
/** Bounded price search, deliberately not a forecasting or AI ranking model. */
export function candidates(pool:Quote[],sport:string,book:string,legs:number,stake:number,target:number,now=Date.now()):Candidate[] {
  if(!Number.isInteger(legs)||legs<2||legs>4||![5,10,20].includes(stake)||!Number.isFinite(target)||target<=stake||target>100000)
    throw Error('Choose 2–4 legs and a total return above your stake, up to $100,000.');
  const groups=new Map<string,Quote[]>(),ids=new Map<string,number>();
  pool.forEach(q=>ids.set(q.id,(ids.get(q.id)??0)+1));
  for(const q of pool){try{
    checkQuote(q,now);
    reportInput([quotePick(q,now)],'10','',now);
    if(q.sport!==sport||q.bookmakerKey!==book||ids.get(q.id)!==1||propThresholdNotice(q)||
      !q.homeTeam||!q.awayTeam||!q.outcome||!['h2h','spreads','totals','player_pass_yds','player_rush_yds','player_pass_yds_alternate','player_rush_yds_alternate'].includes(q.market))continue;
    const key=eventKey(q),group=groups.get(key)??[];group.push(q);groups.set(key,group);
  }catch{/* Ignore unusable offers, never repair their identity or price. */}}
  // Conflicting event identities are not safe to combine or use for research.
  const events=[...groups.values()].filter(g=>g.every(q=>q.startAt===g[0].startAt&&q.homeTeam===g[0].homeTeam&&q.awayTeam===g[0].awayTeam))
    .sort((a,b)=>Date.parse(a[0].startAt)-Date.parse(b[0].startAt)||a[0].eventId.localeCompare(b[0].eventId)).slice(0,24);
  let states:{quotes:Quote[];decimal:number}[]=[{quotes:[],decimal:1}];
  const rank=(x:{quotes:Quote[];decimal:number})=>Math.abs(Math.log(x.decimal)-Math.log(target/stake)*x.quotes.length/legs);
  for(const group of events){
    const offers=group.sort((a,b)=>a.id.localeCompare(b.id)).slice(0,64),next=[...states];
    for(const state of states)if(state.quotes.length<legs)for(const q of offers){
      // The report endpoint accepts four distinct sport/market lookups.
      if(new Set([...state.quotes,q].map(v=>v.sport+':'+v.market)).size>4)continue;
      next.push({quotes:[...state.quotes,q],decimal:state.decimal*number(american(q.americanOdds))});
    }
    // Keep separate beams per length so short tickets cannot crowd out complete ones.
    states=Array.from({length:legs+1},(_,n)=>next.filter(s=>s.quotes.length===n).sort((a,b)=>rank(a)-rank(b)).slice(0,128)).flat();
  }
  return states.filter(s=>s.quotes.length===legs).sort((a,b)=>Math.abs(a.decimal*stake-target)-Math.abs(b.decimal*stake-target))
    .slice(0,3).map(s=>({...s,returnAmount:s.decimal*stake}));
}

export function selectionReason(q:Quote,ticket:Candidate,pool:Quote[],stake:number,target:number):string {
  const category=(m:string)=>m.replace(/_alternate$/,'');
  const alternate=pool.find(v=>{try{checkQuote(v);reportInput([quotePick(v)],'10','');return v.id!==q.id&&v.bookmakerKey===q.bookmakerKey&&eventKey(v)===eventKey(q)&&
    v.homeTeam===q.homeTeam&&v.awayTeam===q.awayTeam&&v.startAt===q.startAt&&
    v.playerName===q.playerName&&v.outcome===q.outcome&&category(v.market)===category(q.market)&&
    v.market!==q.market&&!propThresholdNotice(v);}catch{return false;}});
  const kind=q.market.endsWith('_alternate')?'Alternate line':'Main line';
  if(!alternate)return `${kind} selected for the ticket’s return target. No comparable main/alternate price was available in the checked offers; a matchup advantage has not been established.`;
  const otherReturn=ticket.returnAmount/number(american(q.americanOdds))*number(american(alternate.americanOdds));
  return `${kind}: estimated ticket return $${ticket.returnAmount.toFixed(2)} on $${stake}. Replacing it with ${alternate.label} at ${alternate.americanOdds} gives $${otherReturn.toFixed(2)}, against your $${target} target. This explains the price tradeoff, not which outcome will win.`;
}
