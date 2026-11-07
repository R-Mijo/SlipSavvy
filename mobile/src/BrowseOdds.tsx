import React,{useEffect,useState} from 'react';
import {Pressable,ScrollView,StyleSheet,Text,View} from 'react-native';
import {checkQuote,oddsRequest,type Quote} from './odds';
import {dayLabel,dayParts,gameChoices,gameDay,gamePart,gameTime,localTimestamp,type DayPart} from './games';

export default function BrowseOdds({onChoose,selectedIds=[],timeZone}:{onChoose:(q:Quote)=>void;selectedIds?:string[];timeZone:string}) {
  const [sports,setSports]=useState<{key:string;title:string}[]>([]),[sport,setSport]=useState(''),[market,setMarket]=useState('h2h');
  const [quotes,setQuotes]=useState<Quote[]>([]),[event,setEvent]=useState(''),[date,setDate]=useState(''),[part,setPart]=useState<DayPart|''>(''),[page,setPage]=useState(0);
  const [loading,setLoading]=useState(false),[error,setError]=useState(''),[refresh,setRefresh]=useState(0);
  useEffect(()=>{
    let active=true;const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),90000);
    setLoading(true);setError('');setQuotes([]);
    (async()=>{try{
      if(!sport){const data=await oddsRequest('/api/sports',controller.signal);
        if(!Array.isArray(data.sports))throw Error('Game data is unavailable.');
        if(active)setSports(data.sports.filter((v:any)=>v&&typeof v.key==='string'&&typeof v.title==='string'));
      }else{const data=await oddsRequest(`/api/odds?sport=${encodeURIComponent(sport)}&market=${market}`,controller.signal);
        if(!Array.isArray(data.quotes))throw Error('Game data is unavailable.');
        const valid=data.quotes.filter((q:Quote)=>{try{checkQuote(q);return true;}catch{return false;}});
        if(active){setQuotes(valid);setEvent(current=>valid.some((q:Quote)=>q.eventId===current)?current:'');}
      }
    }catch(e){if(active)setError(controller.signal.aborted?'Game data took too long. Try refresh.':(e as Error).message);}
    finally{clearTimeout(timer);if(active)setLoading(false);}})();
    return()=>{active=false;controller.abort();clearTimeout(timer);};
  },[sport,market,refresh]);
  useEffect(()=>{setDate('');setPart('');setPage(0);setEvent('');},[timeZone]);
  const button=(label:string,fn:()=>void,id:string,selected=false,disabled=false)=><Pressable key={id} testID={id}
    accessibilityRole="button" accessibilityState={{selected,disabled}} disabled={disabled} onPress={fn} style={[s.button,selected&&s.selected,disabled&&{opacity:.4}]}>
    <Text style={s.text}>{label}</Text></Pressable>;
  const games=gameChoices(quotes),dates=[...new Set(games.map(q=>gameDay(q.startAt,timeZone)))].sort();
  const chosenDate=dates.includes(date)?date:dates[0];
  const dated=games.filter(q=>gameDay(q.startAt,timeZone)===chosenDate);
  const chosenPart=part&&dated.some(q=>gamePart(q.startAt,timeZone)===part)?part:dated.length?gamePart(dated[0].startAt,timeZone):'';
  const filtered=dated.filter(q=>gamePart(q.startAt,timeZone)===chosenPart),pages=Math.max(1,Math.ceil(filtered.length/8));
  const currentPage=Math.min(page,pages-1),visible=filtered.slice(currentPage*8,currentPage*8+8),selected=visible.find(q=>q.eventId===event);
  return <View style={s.panel} testID="browse-odds">
    <Text style={s.title}>Choose your lines</Text>
    <Text style={s.note}>Select a sport, date and game. Tap a sportsbook line to add it to your parlay.</Text>
    <View style={s.row}>{sports.map(v=>button(v.title,()=>{if(v.key!==sport){setSport(v.key);setEvent('');setDate('');setPart('');setPage(0);}},'sport-'+v.key,sport===v.key))}</View>
    {sport?<View style={s.row}>{([['h2h','Moneyline'],['spreads','Spread'],['totals','Total']] as const)
      .map(([key,label])=>button(label,()=>setMarket(key),'market-'+key,market===key))}</View>:null}
    {loading?<Text accessibilityRole="status" style={s.note}>Loading games…</Text>:null}
    {error?<Text style={s.error} accessibilityRole="alert">{error}</Text>:null}
    {!loading&&!error&&sport&&!games.length?<Text style={s.note}>No current pregame lines are available. Try another market or refresh.</Text>:null}
    {!loading&&!error&&dates.length?<>
      <Text style={s.label}>Game date · {timeZone.replace(/_/g,' ')}</Text>
      <ScrollView horizontal contentContainerStyle={s.dates} accessibilityLabel="Available game dates">
        {dates.map(day=>button(dayLabel(day),()=>{setDate(day);setPart('');setEvent('');setPage(0);},'date-'+day,day===chosenDate))}
      </ScrollView>
      <View style={s.row}>{dayParts.map(value=>{const count=dated.filter(q=>gamePart(q.startAt,timeZone)===value).length;
        return button(value[0].toUpperCase()+value.slice(1)+' ('+count+')',()=>{setPart(value);setEvent('');setPage(0);},'part-'+value,value===chosenPart,!count);})}</View>
      <Text style={s.note}>Morning before noon · afternoon noon–4:59 PM · night from 5 PM. Available dates reflect the current feed.</Text>
      {visible.map(q=>button(`${q.event}\n${gameTime(q.startAt,timeZone)}`,()=>setEvent(q.eventId),'game-'+q.eventId,event===q.eventId))}
      {pages>1?<View style={s.row}>
        {button('Previous',()=>{setPage(currentPage-1);setEvent('');},'games-previous',false,currentPage===0)}
        <Text style={s.note}>{currentPage*8+1}–{Math.min((currentPage+1)*8,filtered.length)} of {filtered.length}</Text>
        {button('Next games',()=>{setPage(currentPage+1);setEvent('');},'games-next',false,currentPage===pages-1)}
      </View>:null}
    </>:null}
    {!loading&&!error&&selected?<View style={s.lines}>
      <Text style={s.label}>{selected.event} · {gameTime(selected.startAt,timeZone)}</Text>
      {quotes.filter(q=>q.eventId===selected.eventId).map(q=><View key={q.id} style={s.quote}>
        {button(`${selectedIds.includes(q.id)?'Added · ':''}${q.label} · ${Number(q.americanOdds)>0?'+':''}${q.americanOdds} · ${q.bookmaker}`,()=>{
          try{checkQuote(q);onChoose(q);}catch(e){setError((e as Error).message);}
        },'quote-'+q.id,selectedIds.includes(q.id))}
        <Text style={s.note}>Updated {localTimestamp(q.updatedAt,timeZone)} · The Odds API</Text>
      </View>)}
    </View>:null}
    {button('Refresh games',()=>setRefresh(v=>v+1),'refresh-odds')}
    <Text style={s.note}>Prices use a five-minute shared cache and can change. Confirm with your sportsbook.</Text>
  </View>;
}
const s=StyleSheet.create({panel:{backgroundColor:'#151E29',padding:18,borderRadius:18,gap:12},
  row:{flexDirection:'row',flexWrap:'wrap',alignItems:'center',gap:8},dates:{gap:8,paddingVertical:4},
  button:{backgroundColor:'#0E151E',padding:12,borderRadius:10,minHeight:44,borderWidth:1,borderColor:'#344252'},
  selected:{borderColor:'#C9F84A'},text:{color:'#F1F5F9',fontSize:14,lineHeight:21},label:{color:'#F1F5F9',fontWeight:'600',fontSize:14},
  title:{color:'#F1F5F9',fontWeight:'700',fontSize:18},note:{color:'#AFBDC9',fontSize:12,lineHeight:19},
  error:{color:'#FFB4AC'},quote:{gap:5},lines:{borderTopWidth:1,borderColor:'#344252',paddingTop:14,gap:12}});
