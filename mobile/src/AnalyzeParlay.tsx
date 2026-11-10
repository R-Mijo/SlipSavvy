import React,{useEffect,useRef,useState} from 'react';
import {Linking,Pressable,StyleSheet,Text,View} from 'react-native';
import type {Pick} from './math';
import {marketLabel} from './odds';
import NflResearch from './NflResearch';
import VenueWeather from './VenueWeather';
import {Fold} from './FlowUI';
import {gameEducation} from './gameEducation';
import {localTimestamp} from './games';
import {evidenceUrl,fetchReports,reportFresh,reportInput,type EventReport,type GameReports,type LegReport} from './reports';

const colors={bg:'#0B1016',panel:'#151E29',field:'#0E151E',border:'#344252',text:'#F1F5F9',muted:'#AFBDC9',lime:'#C9F84A',ink:'#162005',error:'#FFB4AC'};
function Action({title,onPress,id,secondary=false,disabled=false}:{title:string;onPress:()=>void;id?:string;secondary?:boolean;disabled?:boolean}) {
  return <Pressable testID={id} accessibilityRole="button" accessibilityState={{disabled}} disabled={disabled}
    onPress={onPress} style={[s.button,secondary&&s.secondary,disabled&&{opacity:.45}]}><Text style={[s.buttonText,secondary&&{color:colors.text}]}>{title}</Text></Pressable>;
}
function SourceLink({url,label}:{url:string;label:string}) {
  const [failed,setFailed]=useState(false);const safe=evidenceUrl(url);
  return safe?<><Text accessibilityRole="link" style={s.link} onPress={()=>{void Linking.openURL(safe).catch(()=>setFailed(true));}}>{label}</Text>
    {failed?<Text style={s.note}>Could not open this source.</Text>:null}</>:null;
}
const matchText:Record<string,string>={matched:'Current line matched',price_changed:'Price changed — select the current line again',
  quote_unavailable:'This exact line is unavailable — refresh the games',ambiguous_match:'This line needs clarification',
  event_identity_conflict:'Game details conflict — refresh the games',provider_unavailable:'Game data is temporarily unavailable',
  expired_during_report:'This line expired during research — refresh the games'};
function LegCard({leg,event,pick,index,timeZone}:{leg:LegReport;event?:EventReport;pick:Pick;index:number;timeZone:string}) {
  const [open,setOpen]=useState(index===0),[sources,setSources]=useState(false);
  const education=gameEducation(pick,leg,event);
  const script=event?.gameScript;
  const leading=script?.scenarios.find(v=>v.id===script.mostLikelyScenarioId);
  return <View style={s.card} testID={'report-leg-'+index}>
    <Pressable accessibilityRole="button" accessibilityState={{expanded:open}} testID={'report-toggle-'+index} onPress={()=>setOpen(!open)} style={s.heading}>
      <View style={s.flex}><Text style={s.eyebrow}>LEG {index+1}</Text><Text style={s.title}>{pick.label}</Text>
        <Text style={s.note}>{event?`${event.awayTeam} at ${event.homeTeam}`:pick.event}</Text></View>
      <Text style={s.link}>{open?'−':'+'}</Text>
    </Pressable>
    <Text style={s.note}>{matchText[leg.matchStatus]}</Text>
    {open?<View style={s.stack}>
      <Text style={s.note}>{pick.quote?.bookmaker} · {marketLabel(pick.quote?.market??'')}</Text>
      {event?<Text style={s.note}>{localTimestamp(event.startAt,timeZone)}</Text>:null}
      <Text style={s.text}>Current odds: {leg.price?.americanOdds??'Unavailable'}</Text>
      {leg.modelWinProbability!==null?<Text style={s.text}>Supplied model estimate: {(leg.modelWinProbability*100).toFixed(1)}%</Text>:null}
      {leg.price?<Text style={s.note}>Bookmaker break-even: {leg.price.breakEvenPercent.toFixed(2)}% · a price threshold, not a win forecast.</Text>:null}
      <Text style={s.section}>Game script & rationale</Text>
      {leading?<><Text style={s.text}>{leading.summary}</Text><Text style={s.note}>Highest-weight scenario in the supplied model. Research references and model evaluation remain the operator's responsibility.</Text></>:
        <Text style={s.note}>{script?.status==='model_supplied'?'The model has no uniquely highest-weight scenario.':'No predictive game script is available. The scenario below explains this line’s conditions.'}</Text>}
      {education?<View testID={'game-education-'+index} style={s.stack}><Text style={s.note}>{education.basis}</Text><Text style={s.section}>What could happen?</Text><Text style={s.text}>{education.script}</Text><Text style={s.section}>Why this line?</Text><Text style={s.text}>{education.why}</Text><Text style={s.section}>What could go wrong?</Text><Text style={s.note}>{education.risk}</Text></View>:null}
      <Text style={s.text}>{leg.legImplication}</Text>
      {event?.context.facts.map((f,i)=><Text key={i} style={s.note}>{f.text}</Text>)}
      <NflResearch research={event?.research} playerName={pick.quote?.playerName} timeZone={timeZone} SourceLink={SourceLink}/>
      <Action title={sources?'Hide sources':'Sources & timestamps'} secondary onPress={()=>setSources(!sources)}/>
      {sources?<View style={s.stack}>
        {leg.quoteSource?<><SourceLink url={leg.quoteSource.sourceUrl} label="Odds provider: The Odds API"/><Text style={s.note}>Updated {localTimestamp(leg.quoteSource.updatedAt,timeZone)} · retrieved {localTimestamp(leg.quoteSource.retrievedAt,timeZone)}</Text></>:null}
        {event?.context.evidence.map(e=><View key={e.id}><SourceLink url={e.url} label={e.publisher}/><Text style={s.note}>Operator-supplied reference · checked {localTimestamp(e.observedAt,timeZone)}</Text></View>)}
        {!event?.context.evidence.length?<Text style={s.note}>Additional matchup evidence has not been connected.</Text>:null}
      </View>:null}
    </View>:null}
  </View>;
}

export default function AnalyzeParlay({picks,timeZone,stake,floor,autoRun=0,prepared}:{picks:Pick[];timeZone:string;stake:string;floor:string;autoRun?:number;prepared?:{key:string;data:GameReports}}) {
  const [report,setReport]=useState<{key:string;data:GameReports}|null>(null),[pending,setPending]=useState<string|null>(null);
  const [error,setError]=useState(''),[now,setNow]=useState(Date.now());
  const controller=useRef<AbortController|null>(null),sequence=useRef(0);
  const timerRef=useRef<ReturnType<typeof setTimeout>|undefined>(undefined);
  const key=JSON.stringify([picks,stake,floor]),currentKey=useRef(key);currentKey.current=key;
  useEffect(()=>{sequence.current++;controller.current?.abort();if(timerRef.current)clearTimeout(timerRef.current);setPending(null);setError('');setReport(null);
    return()=>{sequence.current++;controller.current?.abort();if(timerRef.current)clearTimeout(timerRef.current);};},[key]);
  useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()),15000);return()=>clearInterval(timer);},[]);
  const analyze=async()=>{
    const id=++sequence.current;controller.current?.abort();
    const requestController=new AbortController();controller.current=requestController;
    let timer:ReturnType<typeof setTimeout>|undefined;
    try {
      const input=reportInput(picks,stake,floor);
      setError('');setReport(null);setPending(key);
      timer=setTimeout(()=>requestController.abort(),90000);
      timerRef.current=timer;
      const data=await fetchReports(input,requestController.signal);
      if(id===sequence.current&&currentKey.current===key){setNow(Date.now());setReport({key,data});}
    }catch(e){if(id===sequence.current&&currentKey.current===key)setError(requestController.signal.aborted?'Analysis took too long. Try again.':(e as Error).message);}
    finally{if(timer)clearTimeout(timer);if(id===sequence.current)setPending(null);}
  };
  useEffect(()=>{if(autoRun>0){if(prepared?.key===key&&reportFresh(prepared.data)){setNow(Date.now());setReport(prepared);}else void analyze();}},[autoRun]);
  const cancel=()=>{sequence.current++;controller.current?.abort();if(timerRef.current)clearTimeout(timerRef.current);setPending(null);setError('');};
  const active=report?.key===key?report.data:null,loading=pending===key;
  const fresh=active?reportFresh(active,now):false;
  return <View style={s.stack}>
    <View style={s.card}>
      <Text style={s.title}>Analyze your parlay</Text>
      <Text style={s.note}>Preview: up to 8 lines across 8 games and 8 sport/market combinations.</Text>
      <Action title={loading?'Analyzing…':'Analyze my parlay'} id="analyze-parlay" disabled={!picks.length||loading} onPress={()=>{void analyze();}}/>
      {loading?<><Text role="status" accessibilityLiveRegion="polite" style={s.note}>Checking your lines and gathering the available evidence…</Text><Action title="Cancel analysis" id="cancel-analysis" secondary onPress={cancel}/></>:null}
      {error?<Text accessibilityRole="alert" testID="report-error" style={s.error}>{error}</Text>:null}
    </View>
    {active&&!fresh?<Text accessibilityRole="alert" testID="report-expired" style={s.error}>This report needs a refresh. Analyze again with current pregame lines.</Text>:null}
    {active&&fresh?<View style={s.stack} testID="game-reports">
      <View style={s.card}><Text accessibilityRole="header" style={s.title}>{active.legs.length}-leg parlay review</Text>
        <Text style={s.text}>{active.legs.every(l=>l.matchStatus==='matched')?'Your selected prices still match. Check the research below before taking this ticket to your sportsbook.':'Some lines changed or could not be verified. Refresh those selections before using this ticket.'}</Text>
        <Text style={s.note}>The meter uses odds. Research adds context; it does not turn that score into a forecast.</Text>
      </View>
      <Fold title="Weather Info" id="weather-info">{active.events.map(event=><View key={event.sport+event.eventId} style={s.stack}><Text style={s.title}>{event.awayTeam} at {event.homeTeam}</Text><VenueWeather event={event} timeZone={timeZone} SourceLink={SourceLink}/></View>)}{!active.events.length?<Text style={s.note}>No matched games have weather evidence yet.</Text>:null}</Fold>
      <Fold title="Analytic Info" id="analytic-info">{active.legs.map((leg,i)=><LegCard key={leg.id+active.generatedAt} leg={leg} timeZone={timeZone} index={i} pick={picks[i]} event={active.events.find(e=>e.sport+':'+e.eventId===leg.eventRef)}/>)}</Fold>
    </View>:null}
  </View>;
}
const s=StyleSheet.create({flex:{flex:1},stack:{gap:14},card:{backgroundColor:colors.panel,borderWidth:1,borderColor:colors.border,borderRadius:18,padding:18,gap:12},
  heading:{flexDirection:'row',alignItems:'center',gap:12,minHeight:44},row:{flexDirection:'row',flexWrap:'wrap',gap:8},
  title:{color:colors.text,fontSize:17,fontWeight:'700',lineHeight:24},text:{color:colors.text,fontSize:14,lineHeight:21},note:{color:colors.muted,fontSize:12,lineHeight:19},
  eyebrow:{color:colors.lime,fontSize:11,fontWeight:'700'},section:{color:colors.text,fontSize:15,fontWeight:'700'},link:{color:colors.lime,fontSize:14,lineHeight:24,paddingVertical:8},
  button:{backgroundColor:colors.lime,borderRadius:10,padding:14,minHeight:48,justifyContent:'center'},buttonText:{color:colors.ink,fontSize:14,fontWeight:'700',textAlign:'center'},
  secondary:{backgroundColor:colors.field,borderWidth:1,borderColor:colors.border},chip:{borderWidth:1,borderColor:colors.border,borderRadius:10,padding:12,minHeight:44},selected:{borderColor:colors.lime},
  input:{backgroundColor:colors.field,borderColor:colors.border,borderWidth:1,borderRadius:10,color:colors.text,padding:12,minHeight:48,fontSize:16},
  finding:{borderTopWidth:1,borderColor:colors.border,paddingTop:10,gap:4},error:{color:colors.error,fontSize:14,lineHeight:21}});
