import React,{useState} from 'react';
import {Pressable,StyleSheet,Text,View} from 'react-native';
import type {Research} from './research';
import {localTimestamp} from './games';

const statusText:Record<string,string>={roster_snapshot:'Matched to roster snapshot',unmapped:'Player identity not matched',
  ambiguous:'Player identity is ambiguous',unavailable:'Player research unavailable'};
function injuryText(status:string):string{return ({reported:'Listed in injury snapshot',not_listed:'Not listed; health and participation are unknown',
  ambiguous:'Conflicting injury rows; status withheld',identity_conflict:'Player details conflict; injury status withheld',
  coverage_unknown:'Injury coverage for this team/week is unknown',unavailable:'Injury data unavailable'} as Record<string,string>)[status];}
export default function NflResearch({research,playerName,timeZone,SourceLink}:{research?:Research;playerName?:string;timeZone:string;
  SourceLink:React.ComponentType<{url:string;label:string}>}){
  const [open,setOpen]=useState(false);
  if(!research||research.status==='not_applicable')return null;
  const player=research.players.find(p=>p.requestedName===playerName),row=player?.injury.record;
  return <View style={s.stack} testID="nfl-research">
    <Text style={s.title}>NFL research</Text>
    <Text style={s.text}>{research.mapping?`Week ${research.mapping.week} schedule matched · file snapshots, incomplete research`:'Research unavailable for this exact game'}</Text>
    {player?<View style={s.stack} testID="player-research">
      <Text style={s.text}>{player.requestedName} · {statusText[player.status]}</Text>
      {player.rosterWeek?<Text style={s.note}>Roster week {player.rosterWeek} · source code {player.rosterStatus??'unknown'} · not confirmation that the player will play.</Text>:null}
      <Text style={s.text}>{injuryText(player.injury.status)}</Text>
      {row?<><Text style={s.note}>Reported game status: {row.gameStatus??'Not supplied'} · practice: {row.practiceStatus??'Not supplied'}</Text>
        <Text style={s.note}>Reported injury: {row.primaryInjury??row.practiceInjury??'Not supplied'}</Text></>:null}
    </View>:null}
    <Pressable testID="research-toggle" accessibilityRole="button" accessibilityState={{expanded:open}} onPress={()=>setOpen(!open)} style={s.button}>
      <Text style={s.link}>{open?'Hide research details':'Research sources & gaps'}</Text>
    </Pressable>
    {open?<View style={s.stack} testID="research-details">
      {Object.entries(research.coverage).map(([topic,status])=><Text key={topic} style={s.note}>{topic==='roster'?'Roster':topic==='injuries'?'Injuries':'Schedule'}: {{unavailable:'unavailable',not_requested:'not requested',file_snapshot:'file snapshot only',matched:'matched',missing:'source file missing',stale:'source file is stale',ambiguous:'ambiguous source',invalid:'source could not be verified',coverage_unknown:'team/week coverage unknown',identity_unmatched:'game identity not matched'}[status]}</Text>)}
      {research.warnings.map((text,i)=><Text key={i} style={s.note}>{text}</Text>)}
      {research.mapping?<Text style={s.note}>{research.listedInjuryCount} uniquely listed injury records for these teams/week{research.injuriesTruncated?' · first 32 shown':''}. This is not a complete availability check.</Text>:null}
      {research.teamInjuries.map(p=><Text key={p.team+':'+p.gsisId} style={s.note}>
        {p.team} · {p.playerName??'Unnamed player'} · reported game status {p.gameStatus??'not supplied'} · practice {p.practiceStatus??'not supplied'}
      </Text>)}
      {research.sources.map(source=><View key={source.id} style={s.stack}>
        <SourceLink url={source.sourceUrl} label={'nflverse '+source.dataset+' source'}/>
        <Text style={s.note}>File updated {localTimestamp(source.providerUpdatedAt,timeZone)} · retrieved {localTimestamp(source.retrievedAt,timeZone)}</Text>
        <Text style={s.note}>Per-player confirmation time is unavailable. {source.attribution}.</Text>
        <SourceLink url={source.licenseUrl} label="Source license"/>
      </View>)}
    </View>:null}
  </View>;
}
const s=StyleSheet.create({stack:{gap:8},title:{color:'#F1F5F9',fontSize:15,fontWeight:'700'},text:{color:'#F1F5F9',fontSize:14,lineHeight:21},
  note:{color:'#AFBDC9',fontSize:12,lineHeight:19},link:{color:'#C9F84A',fontSize:14},button:{padding:12,minHeight:44,borderWidth:1,borderColor:'#344252',borderRadius:10}});
