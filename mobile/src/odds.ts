import { american, validatePick, type Pick } from './math';
export type Quote = { id:string; eventId:string; event:string; startAt:string; sport:string;
  market:string; label:string; americanOdds:string; bookmaker:string; updatedAt:string; fetchedAt:string };
export function checkQuote(q:Quote, now=Date.now()):void {
  if(!q||!['id','eventId','event','label','americanOdds','bookmaker','updatedAt','fetchedAt','startAt','sport','market']
    .every(k=>typeof q[k as keyof Quote]==='string'&&q[k as keyof Quote].length>0&&q[k as keyof Quote].length<=600)) throw Error('This line is incomplete. Refresh the games.');
  const age=now-Date.parse(q.updatedAt);
  american(q.americanOdds);
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
  const data=await response.json();
  if(!response.ok)throw Error(typeof data.error==='string'?data.error:'Game data is unavailable.');
  return data;
}
