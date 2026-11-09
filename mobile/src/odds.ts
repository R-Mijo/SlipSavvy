import { american, validatePick, type Pick } from './math';
export type Quote = { id:string; eventId:string; event:string; startAt:string; sport:string;
  market:string; label:string; americanOdds:string; bookmaker:string; updatedAt:string; fetchedAt:string;
  bookmakerKey?:string; homeTeam?:string; awayTeam?:string; outcome?:string; point?:number|null;
  playerName?:string; playerIdentityBasis?:string };
export const propMarkets=['player_pass_yds','player_rush_yds','player_pass_yds_alternate','player_rush_yds_alternate'] as const;
export const isProp=(market:string)=>propMarkets.some(m=>m===market);
export function marketLabel(market:string):string {
  return ({h2h:'Moneyline',spreads:'Spread',totals:'Total',player_pass_yds:'Passing yards',player_rush_yds:'Rushing yards',
    player_pass_yds_alternate:'Alternate passing yards',player_rush_yds_alternate:'Alternate rushing yards'} as Record<string,string>)[market]??market;
}
export function checkQuote(q:Quote, now=Date.now()):void {
  if(!q||!['id','eventId','event','label','americanOdds','bookmaker','updatedAt','fetchedAt','startAt','sport','market']
    .every(k=>{const value=q[k as keyof Quote];return typeof value==='string'&&value.length>0&&value.length<=600;})) throw Error('This line is incomplete. Refresh the games.');
  const age=now-Date.parse(q.updatedAt);
  american(q.americanOdds);
  if(isProp(q.market)&&(q.sport!=='americanfootball_nfl'||typeof q.playerName!=='string'||!q.playerName.trim()||
    q.playerName!==q.playerName.trim()||q.playerName.length>120||/[\x00-\x1f]/.test(q.playerName)||q.playerIdentityBasis!=='provider_description'||
    !['Over','Under'].includes(q.outcome??'')||typeof q.point!=='number'||!Number.isFinite(q.point)||q.point<=0||q.point>1000))
    throw Error('This player line is incomplete. Refresh the props.');
  if(!Number.isFinite(age)||age < -60000||age>900000||!Number.isFinite(Date.parse(q.startAt))||
    Date.parse(q.startAt)<=now||!Number.isFinite(Date.parse(q.fetchedAt))) throw Error('This line is no longer current. Refresh the games.');
}
export function quotePick(q:Quote,now=Date.now(),fairPercent=''):Pick {
  checkQuote(q,now);
  return validatePick({id:q.id,label:q.label,event:`${q.event} (${q.eventId})`,odds:q.americanOdds,fairPercent,
    source:`${q.bookmaker} via The Odds API · Updated ${q.updatedAt}`,sourceUrl:'https://the-odds-api.com/',
    capturedAt:q.fetchedAt,kind:'feed',confirmed:true,quote:q});
}
export async function oddsRequest(path:string,signal?:AbortSignal) {
  const base=process.env.EXPO_PUBLIC_ODDS_API_URL;
  if(!base||!/^https:\/\//.test(base)) throw Error('Game data is not connected yet.');
  const response=await fetch(base.replace(/\/$/,'')+path,{signal,headers:{
    Authorization:'Bearer '+(process.env.EXPO_PUBLIC_ODDS_PREVIEW_TOKEN??'')}});
  let data;try{data=await response.json();}catch{throw Error('Game data is temporarily unavailable. Try refresh.');}
  if(!response.ok)throw Error(typeof data?.error==='string'?data.error:'Game data is unavailable.');
  return data;
}
