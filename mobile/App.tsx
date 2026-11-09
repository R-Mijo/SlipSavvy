import React,{useEffect,useState} from 'react';
import {Image,Pressable,ScrollView,StyleSheet,Text,View} from 'react-native';
import {SafeAreaProvider,SafeAreaView} from 'react-native-safe-area-context';
import {StatusBar} from 'expo-status-bar';
import BrowseOdds from './src/BrowseOdds';
import TimeZoneChoice from './src/TimeZoneChoice';
import {deviceZone} from './src/games';
import AnalyzeParlay from './src/AnalyzeParlay';
import SportPicker from './src/SportPicker';
import SavvyBuilder from './src/SavvyBuilder';
import TicketInfo from './src/TicketInfo';
import {Fold,Meter,flow} from './src/FlowUI';
import {quotePick,propThresholdNotice,type Quote} from './src/odds';
import {replacePick} from './src/review';
import type {Pick} from './src/math';
import type {GameReports} from './src/reports';

export default function App(){
  const [timeZone,setTimeZone]=useState(deviceZone),[sport,setSport]=useState('');
  const [tab,setTab]=useState<'savvy'|'check'>('savvy'),[picks,setPicks]=useState<Pick[]>([]);
  const [notice,setNotice]=useState(''),[error,setError]=useState(''),[stake,setStake]=useState('10'),[target,setTarget]=useState('100'),[autoRun,setAutoRun]=useState(0);
  const [prepared,setPrepared]=useState<{key:string;data:GameReports}|undefined>(undefined);
  const [now,setNow]=useState(Date.now());
  useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()),15000);return()=>clearInterval(timer);},[]);
  const add=(quote:Quote)=>{try{const pick=quotePick(quote);setPicks(replacePick(picks,pick));setNotice(quote.label+' added.');setError('');}
    catch(e){setError((e as Error).message);}};
  const generated=(next:Pick[],report?:GameReports)=>{setPrepared(report?{key:JSON.stringify([next,stake,target]),data:report}:undefined);setPicks(next);setNotice('Suggested ticket ready. Review the available research below.');setError('');setAutoRun(n=>n+1);};
  return <SafeAreaProvider><SafeAreaView style={s.safe}>
    <StatusBar style="light"/>
    <View style={s.brandRow}><Image source={require('./assets/logo-horizontal.png')} accessible accessibilityLabel="SlipSavvy" style={s.brand} resizeMode="contain"/><Text style={s.badge}>RESEARCH PREVIEW</Text></View>
    <ScrollView contentContainerStyle={s.content} keyboardShouldPersistTaps="handled">
      <View style={s.stack}>
        <SportPicker sport={sport} onChange={setSport}/>
        <View style={s.nav}>{(['savvy','check'] as const).map(t=><Pressable key={t} testID={'tab-'+t} accessibilityRole="tab" accessibilityState={{selected:tab===t}}
          onPress={()=>setTab(t)} style={[s.navItem,t===tab&&{backgroundColor:'#151E29',borderColor:'#C9F84A',borderWidth:1}]}><Text style={[s.cardTitle,t===tab&&s.lime]}>{t==='savvy'?'Savvy Parlay Builder':'My Picks & Research'}</Text></Pressable>)}</View>
        {tab==='savvy'?<SavvyBuilder sport={sport} stake={stake} target={target} onStake={setStake} onTarget={setTarget} onChoose={generated}/>:<>
          <Text style={flow.title}>Choose your lines.</Text><Text style={s.body}>Mix team lines and player props. We’ll research your ticket.</Text>
          <TimeZoneChoice zone={timeZone} onChange={setTimeZone}/>
          <BrowseOdds sport={sport} timeZone={timeZone} onChoose={add} selectedIds={picks.map(p=>p.id)}/>
        </>}
        <View style={s.card} testID="parlay-tray">
          <View style={s.row}><Text style={s.cardTitle}>Your parlay</Text><Text style={s.lime} testID="parlay-count">{picks.length}/8 legs</Text></View>
          {!picks.length?<Text style={s.body}>Your selections will appear here.</Text>:picks.map((pick,i)=><View style={s.pick} key={pick.id} testID={'pick-'+i}>
            <View style={s.row}><Text style={[s.selection,s.flex]}>{pick.label}</Text><Text style={s.price}>{Number(pick.odds)>0?'+':''}{pick.odds}</Text></View>
            {pick.quote&&propThresholdNotice(pick.quote)?<Text style={s.body}>{propThresholdNotice(pick.quote)}</Text>:null}
            <Text style={s.note}>{pick.quote?.event??pick.event}</Text>
            <View style={s.row}><Text style={[s.note,s.flex]}>{pick.quote?.bookmaker??pick.source}</Text>
              <Pressable testID={'remove-'+i} accessibilityRole="button" accessibilityLabel={'Remove '+pick.label} style={s.remove}
                onPress={()=>{setPicks(picks.filter(p=>p.id!==pick.id));setNotice('Selection removed.');setError('');}}><Text style={s.lime}>Remove</Text></Pressable></View>
          </View>)}
          {notice?<Text accessibilityLiveRegion="polite" style={s.note}>{notice}</Text>:null}
          {error?<Text accessibilityRole="alert" testID="error" style={s.error}>{error}</Text>:null}
          {tab==='check'?<View style={flow.wrap}>{['5','10','20'].map(v=><Pressable key={v} testID={'stake-'+v} accessibilityRole="button" accessibilityLabel={'Stake $'+v} accessibilityState={{selected:stake===v}} onPress={()=>setStake(v)} style={[flow.chip,stake===v&&flow.selected]}><Text style={flow.text}>${v}</Text></Pressable>)}</View>:null}
          <Meter picks={picks} now={now}/>
        </View>
        <TicketInfo picks={picks} stake={stake} now={now}/>
        <AnalyzeParlay picks={picks} timeZone={timeZone} stake={stake} floor={tab==='savvy'?target:''} autoRun={autoRun} prepared={prepared}/>
        <Text style={s.note}>Research, not a guarantee. Confirm lines and rules in your sportsbook. Private session · selections clear on reload. No bet placement. For adults of legal betting age where permitted.</Text>
        <Fold title="Offers & Sponsors" id="sponsor-info"><Text style={s.body}>No sponsor offers are running. Future sponsored offers will be clearly labeled and kept separate from ticket selection and research.</Text></Fold>
      </View>
    </ScrollView>
  </SafeAreaView></SafeAreaProvider>;
}
const s=StyleSheet.create({safe:{flex:1,backgroundColor:'#0B1016'},flex:{flex:1},stack:{gap:18},
  brandRow:{paddingHorizontal:20,paddingVertical:14,flexDirection:'row',alignItems:'center',justifyContent:'space-between',gap:10,borderBottomWidth:1,borderColor:'#344252'},
  brand:{width:180,height:36,flexShrink:1},badge:{color:'#C9F84A',fontSize:10,fontWeight:'700',letterSpacing:1},
  content:{padding:20,paddingBottom:36,width:'100%',maxWidth:720,alignSelf:'center'},
  title:{color:'#F1F5F9',fontSize:30,fontWeight:'800',lineHeight:36},cardTitle:{color:'#F1F5F9',fontSize:17,fontWeight:'700',lineHeight:24},
  body:{color:'#AFBDC9',fontSize:15,lineHeight:23},note:{color:'#AFBDC9',fontSize:12,lineHeight:19},lime:{color:'#C9F84A',fontSize:14},
  card:{backgroundColor:'#151E29',borderWidth:1,borderColor:'#344252',borderRadius:18,padding:18,gap:12},
  lesson:{borderLeftWidth:3,borderColor:'#C9F84A',paddingLeft:14,gap:8},row:{flexDirection:'row',alignItems:'center',justifyContent:'space-between',gap:10},
  pick:{borderTopWidth:1,borderColor:'#344252',paddingTop:12,gap:6},selection:{color:'#F1F5F9',fontSize:16,fontWeight:'600',lineHeight:23},price:{color:'#C9F84A',fontSize:18,fontWeight:'700'},
  remove:{minHeight:44,justifyContent:'center',paddingHorizontal:6},error:{color:'#FFB4AC',fontSize:14,lineHeight:21},
  nav:{flexDirection:'row',borderTopWidth:1,borderColor:'#344252',padding:10,gap:8},navItem:{flex:1,minHeight:48,justifyContent:'center',alignItems:'center',borderRadius:10,padding:8}});
