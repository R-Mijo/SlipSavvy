import type {Pick} from './math';
import type {EventReport,LegReport} from './reports';
import {isProp,propThresholdNotice} from './odds';

/** Conditional education from exact selected lines, not a generated forecast. */
export function gameEducation(pick:Pick,leg:LegReport,event?:EventReport):{basis:string;script:string;why:string;risk:string}|null {
  const q=pick.quote;
  if(!q||q.sport!=='americanfootball_nfl'||!event||leg.matchStatus!=='matched')return null;
  const point=q.point,over=q.outcome==='Over';
  let script='',why='',risk='';
  if(q.market==='spreads'&&typeof point==='number'){
    script=point<0?`One possible path is ${q.outcome} building and maintaining a lead. A closer game is a competing scenario.`:
      `One possible path is ${q.outcome} keeping the game close, even without winning outright.`;
    why=point<0?`This ${point} spread requires more than a straight-up win; the winning margin must exceed ${Math.abs(point)} points.`:
      `The +${point} spread adds a cushion. A loss by less than ${point} points can still cover.`;
    if(point===0)why='A zero-point spread needs your team to win; a tied result may push under the sportsbook rules.';
    risk='Late scoring can change a spread result after the winner looks settled. Game flow and play calling have not been forecast.';
  }else if(q.market==='totals'&&typeof point==='number'){
    script=over?'A possible Over scenario has sustained drives and enough scoring from the two teams.':'A possible Under scenario has fewer scoring opportunities or drives ending without points.';
    why=`The combined score must finish ${over?'above':'below'} ${point}. A winning team alone does not decide this selection.`;
    risk='Turnovers, short fields and overtime can change the total. Pace and recent efficiency are not connected yet.';
  }else if(isProp(q.market)&&typeof point==='number'){
    const passing=q.market.includes('pass'),stat=passing?'passing':'rushing';
    script=passing?'A trailing or close-game scenario can create passing opportunities, but attempts and efficiency still matter.':
      'A lead-protection scenario can create rushing opportunities, but the selected player must receive that workload.';
    if(!over)script+=' More opportunities would challenge an Under; reduced workload or efficiency would support its direction.';
    why=`${q.playerName} needs ${stat} yards ${over?'above':'below'} ${point} for this ${q.outcome} selection, subject to the book’s grading rules. The scenario is an explanation of opportunity, not a prediction of workload.`;
    risk='Recent usage, snap share and current participation are not established. Check the injury evidence; a roster entry does not confirm playing time.';
    const notice=propThresholdNotice(q);if(notice){why=notice;risk+=' The exact threshold outcome is unverified.';}
  }else if(q.market==='h2h'){
    script=`One scenario is ${q.outcome} winning outright; the opposing win scenario remains possible.`;
    why='Moneyline concerns the winner rather than the winning margin. The offered price does not explain why that team will win.';
    risk='Current matchup strength, usage and a calibrated game forecast are not connected.';
  }else return null;
  if(typeof point==='number'&&Number.isInteger(point)&&!propThresholdNotice(q))risk+=' An exact tie with the line may push; verify the sportsbook rules.';
  return {basis:'Conditional scenario based on your selected line. Not a predicted game script or AI forecast.',script,why,risk};
}
