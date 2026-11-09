import React,{useState} from 'react';
import {Image,Pressable,ScrollView,StyleSheet,Text,View} from 'react-native';
import {SafeAreaProvider,SafeAreaView} from 'react-native-safe-area-context';
import {StatusBar} from 'expo-status-bar';
import BrowseOdds from './src/BrowseOdds';
import TimeZoneChoice from './src/TimeZoneChoice';
import {deviceZone} from './src/games';
import AnalyzeParlay from './src/AnalyzeParlay';
import {quotePick,propThresholdNotice,type Quote} from './src/odds';
import {replacePick} from './src/review';
import type {Pick} from './src/math';

function Learn(){return <View style={s.stack}>
  <Text style={s.title}>Learn the odds</Text>
  <View style={s.card}><Text style={s.cardTitle}>Prices and predictions</Text><Text style={s.body}>At −110, the price needs a win rate above 52.38% to break even. That is a price threshold, not a prediction of the game.</Text>
    <Text style={s.body}>A $10 bet at +150 returns $25 if it wins, including your $10 stake.</Text></View>
  <View style={s.card}><Text style={s.cardTitle}>Each extra leg must also win</Text><Text style={s.body}>For independent 50% outcomes, one wins 50% of the time, two both win 25%, and four all win 6.25%. Six independent 60% selections all win about 4.67% of the time.</Text>
    <Text style={s.body}>Selections from the same game can be related. They need a shared game model and the sportsbook's actual combined price.</Text></View>
  <View style={s.card}><Text style={s.cardTitle}>What Sevenfold can establish</Text><Text style={s.body}>Current lines and exact price calculations can be checked. Game scripts and win estimates require supported research and model inputs. More simulations improve sampling precision, not the quality of the underlying forecast.</Text></View>
  <View style={s.card}><Text style={s.cardTitle}>Keep it affordable</Text><Text style={s.body}>Set a limit before you start. Use money you can afford to lose, take breaks and avoid chasing losses. SlipSavvy does not place bets or guarantee winnings.</Text></View>
</View>;}

export default function App(){
  const [timeZone,setTimeZone]=useState(deviceZone);
  const [tab,setTab]=useState<'build'|'learn'>('build'),[picks,setPicks]=useState<Pick[]>([]),[notice,setNotice]=useState(''),[error,setError]=useState('');
  const add=(quote:Quote)=>{try{const pick=quotePick(quote);setPicks(replacePick(picks,pick));setNotice(quote.label+' added to your parlay.');setError('');}
    catch(e){setError((e as Error).message);}};
  const count=picks.length,illustration=100*Math.pow(.5,Math.max(1,count));
  return <SafeAreaProvider><SafeAreaView style={s.safe}>
    <StatusBar style="light"/>
    <View style={s.brandRow}><Image source={require('./assets/logo-horizontal.png')} accessible accessibilityLabel="SlipSavvy" style={s.brand} resizeMode="contain"/><Text style={s.badge}>PHONE PREVIEW</Text></View>
    <ScrollView contentContainerStyle={s.content} keyboardShouldPersistTaps="handled">
      {tab==='learn'?<Learn/>:<View style={s.stack}>
        <View><Text style={s.title}>Build your parlay.</Text><Text style={s.body}>Choose your lines. See the tradeoffs.</Text></View>
        <View style={s.card} testID="parlay-tray">
          <View style={s.row}><Text style={s.cardTitle}>Your parlay</Text><Text style={s.lime} testID="parlay-count">{count}/8 legs</Text></View>
          {!count?<Text style={s.body}>Choose a sport, date and game below to add your first line.</Text>:picks.map((pick,i)=><View style={s.pick} key={pick.id} testID={'pick-'+i}>
            <View style={s.row}><Text style={[s.selection,s.flex]}>{pick.label}</Text><Text style={s.price}>{Number(pick.odds)>0?'+':''}{pick.odds}</Text></View>
            {pick.quote&&propThresholdNotice(pick.quote)?<Text style={s.body}>{propThresholdNotice(pick.quote)}</Text>:null}
            <Text style={s.note}>{pick.quote?.event??pick.event}</Text>
            <View style={s.row}><Text style={[s.note,s.flex]}>{pick.quote?.bookmaker??pick.source}</Text>
              <Pressable testID={'remove-'+i} accessibilityRole="button" accessibilityLabel={'Remove '+pick.label} style={s.remove}
                onPress={()=>{setPicks(picks.filter(p=>p.id!==pick.id));setNotice('Selection removed.');setError('');}}><Text style={s.lime}>Remove</Text></Pressable></View>
          </View>)}
          {notice?<Text accessibilityLiveRegion="polite" style={s.note}>{notice}</Text>:null}
          {error?<Text accessibilityRole="alert" testID="error" style={s.error}>{error}</Text>:null}
        </View>
        {count?<View style={s.lesson} testID="leg-lesson"><Text style={s.cardTitle}>What changes with {count===1?'another leg':count+' legs'}?</Text>
          <Text style={s.body}>Every added leg must also win. An extra leg can raise the payout while reducing the chance of the whole ticket winning.</Text>
          <Text style={s.note} testID="leg-illustration">Illustration only: at 50% each with independent outcomes, {Math.max(1,count)} {count===1?'leg wins':'legs all win'} {illustration.toFixed(2)}% of the time. This is not a forecast for your picks.</Text>
          <Text style={s.note}>Same-game relationships can change the result. Easier alternate lines and split tickets also change the price and risk.</Text>
        </View>:null}
        <TimeZoneChoice zone={timeZone} onChange={setTimeZone}/>
        <AnalyzeParlay picks={picks} timeZone={timeZone}/>
        <BrowseOdds timeZone={timeZone} onChoose={add} selectedIds={picks.map(p=>p.id)}/>
        <Text style={s.note}>Private session · Entries stay in memory and clear when the app reloads. No account, payment or bet placement. For adults of legal betting age where permitted.</Text>
      </View>}
    </ScrollView>
    <View style={s.nav}>{(['build','learn'] as const).map(t=><Pressable key={t} testID={'tab-'+(t==='build'?'check':t)} accessibilityRole="tab" accessibilityState={{selected:tab===t}}
      onPress={()=>setTab(t)} style={[s.navItem,t===tab&&{backgroundColor:'#151E29'}]}><Text style={[s.cardTitle,t===tab&&s.lime]}>{t==='build'?'Build parlay':'Learn the odds'}</Text></Pressable>)}</View>
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
