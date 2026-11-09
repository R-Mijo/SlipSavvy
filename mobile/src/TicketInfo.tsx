import React from 'react';
import {Text} from 'react-native';
import {american,number,type Pick} from './math';
import {ticketPrice} from './tickets';
import {Fold,flow} from './FlowUI';
export default function TicketInfo({picks,stake,now}:{picks:Pick[];stake:string;now:number}) {
  const price=ticketPrice(picks,now),capital=Number(stake),cents=Math.round(capital*100);
  const first=picks.slice(0,Math.ceil(picks.length/2)),second=picks.slice(first.length),a=ticketPrice(first,now),b=ticketPrice(second,now);
  const half=Math.floor(cents/2)/100,rest=(cents-Math.floor(cents/2))/100;
  return <Fold title="Parlay Info" id="parlay-info">
    {price?<><Text style={flow.text}>${capital.toFixed(2)} stake · ${ (capital*price.decimal).toFixed(2)} estimated total return if every leg wins.</Text>
      <Text style={flow.note}>Return includes stake. Individual offered prices are multiplied for this estimate; sportsbook restrictions and combined pricing may differ. Pushes or voids can change settlement.</Text></>:<Text style={flow.note}>Confirm this ticket’s combined price in your sportsbook. A same-game or mixed-book payout is not calculated from its individual lines.</Text>}
    {a&&b&&price?<><Text style={flow.subtitle}>Compare two smaller tickets</Text>
      <Text style={flow.text}>Same ${capital.toFixed(2)} budget: ${half.toFixed(2)} on legs 1–{first.length}, ${rest.toFixed(2)} on legs {first.length+1}–{picks.length}.</Text>
      <Text style={flow.note}>Both win: ${(half*a.decimal+rest*b.decimal).toFixed(2)} total return. Only the first wins: ${(half*a.decimal).toFixed(2)}. Only the second wins: ${(rest*b.decimal).toFixed(2)}. Neither wins: $0.00. These are price scenarios, not predicted outcomes.</Text></>:null}
    {picks.length?<><Text style={flow.subtitle}>Individual line prices</Text>{picks.map(p=><Text key={p.id} style={flow.note}>{p.label}: {(100/number(american(p.odds))).toFixed(1)}/100 price-implied · {p.quote?.bookmaker}. Captured odds; refresh if they have changed.</Text>)}</>:null}
  </Fold>;
}
