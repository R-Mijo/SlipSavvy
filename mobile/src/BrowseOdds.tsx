import React,{useEffect,useState} from 'react';
import {Pressable,StyleSheet,Text,View} from 'react-native';
import {checkQuote,oddsRequest,type Quote} from './odds';
export default function BrowseOdds({onChoose}:{onChoose:(q:Quote)=>void}) {
  const [sports,setSports]=useState<{key:string;title:string}[]>([]);
  const [sport,setSport]=useState('');const [market,setMarket]=useState('h2h');
  const [quotes,setQuotes]=useState<Quote[]>([]);const [event,setEvent]=useState('');
  const [loading,setLoading]=useState(false);const [error,setError]=useState('');const [refresh,setRefresh]=useState(0);
  useEffect(()=>{
    let active=true;const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),90000);
    setLoading(true);setError('');setQuotes([]);setEvent('');
    (async()=>{try{
      if(!sport){const data=await oddsRequest('/api/sports',controller.signal);
        if(!Array.isArray(data.sports))throw Error('Game data is unavailable.');
        if(active)setSports(data.sports.filter((v:any)=>typeof v.key==='string'&&typeof v.title==='string'));
      }else{const data=await oddsRequest(`/api/odds?sport=${encodeURIComponent(sport)}&market=${market}`,controller.signal);
        if(!Array.isArray(data.quotes))throw Error('Game data is unavailable.');
        const valid=data.quotes.filter((q:Quote)=>{try{checkQuote(q);return true;}catch{return false;}});
        if(active)setQuotes(valid);
      }
    }catch(e){if(active)setError(controller.signal.aborted?'Game data took too long. Try refresh.':(e as Error).message);}
    finally{clearTimeout(timer);if(active)setLoading(false);}})();
    return()=>{active=false;controller.abort();clearTimeout(timer);};
  },[sport,market,refresh]);
  const button=(label:string,fn:()=>void,id:string,selected=false)=><Pressable key={id} testID={id}
    accessibilityRole="button" accessibilityState={{selected}} onPress={fn} style={[s.button,selected&&s.selected]}>
    <Text style={s.text}>{label}</Text></Pressable>;
  const games=[...new Map(quotes.map(q=>[q.eventId,q])).values()];
  return <View style={s.panel} testID="browse-odds">
    <Text style={s.title}>Choose a sport, game and line</Text>
    <Text style={s.note}>Upcoming games · Prices can change. Confirm with your sportsbook.</Text>
    <View style={s.row}>{sports.map(v=>button(v.title,()=>setSport(v.key),'sport-'+v.key,sport===v.key))}</View>
    {sport?<View style={s.row}>{([['h2h','Moneyline'],['spreads','Spread'],['totals','Total']] as const)
      .map(([key,label])=>button(label,()=>setMarket(key),'market-'+key,market===key))}</View>:null}
    {loading?<Text style={s.note}>Loading games…</Text>:null}
    {error?<Text style={s.error} accessibilityRole="alert">{error}</Text>:null}
    {!loading&&!error&&sport&&!games.length?<Text style={s.note}>No current pregame lines are available for this selection.</Text>:null}
    {!loading&&!error&&sport?games.map(q=>button(q.event+' · '+new Date(q.startAt).toLocaleString(),()=>setEvent(q.eventId),'game-'+q.eventId,event===q.eventId)):null}
    {!loading&&event?quotes.filter(q=>q.eventId===event).map(q=><View key={q.id} style={s.quote}>
      {button(`${q.label} · ${Number(q.americanOdds)>0?'+':''}${q.americanOdds} · ${q.bookmaker}`,()=>{
        try{checkQuote(q);onChoose(q);}catch(e){setError((e as Error).message);}
      },'quote-'+q.id)}
      <Text style={s.note}>Updated {new Date(q.updatedAt).toLocaleString()} · The Odds API</Text>
    </View>):null}
    {button('Refresh games',()=>setRefresh(v=>v+1),'refresh-odds')}
    <Text style={s.note}>Refresh uses a five-minute shared cache. No win forecast is inferred from these prices.</Text>
  </View>;
}
const s=StyleSheet.create({panel:{backgroundColor:'#151E29',padding:18,borderRadius:18,gap:12},
  row:{flexDirection:'row',flexWrap:'wrap',gap:8},button:{backgroundColor:'#233141',padding:12,borderRadius:10,minHeight:44},
  selected:{borderWidth:1,borderColor:'#C9F84A'},text:{color:'#F1F5F9',fontSize:14},
  title:{color:'#F1F5F9',fontWeight:'700',fontSize:18},note:{color:'#AFBDC9',fontSize:12,lineHeight:19},
  error:{color:'#FFB4AC'},quote:{gap:5}});
