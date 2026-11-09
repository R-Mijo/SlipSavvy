import React,{useEffect,useRef,useState} from 'react';
import {Pressable,ScrollView,StyleSheet,Text,View} from 'react-native';
import {checkQuote,isProp,marketLabel,oddsRequest,propThresholdNotice,type Quote} from './odds';
import {localTimestamp} from './games';

/** Mounted with the exact event identity as its key. No background prop requests. */
export default function PlayerProps({game,onChoose,selectedIds,timeZone}:{game:Quote;onChoose:(q:Quote)=>void;selectedIds:string[];timeZone:string}) {
  const [alternate,setAlternate]=useState(false),[category,setCategory]=useState('pass'),[player,setPlayer]=useState('');
  const [quotes,setQuotes]=useState<Quote[]|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState('');
  const controller=useRef<AbortController|null>(null),sequence=useRef(0);
  useEffect(()=>()=>{sequence.current++;controller.current?.abort();},[]);
  const button=(label:string,id:string,fn:()=>void,selected=false,disabled=false)=><Pressable key={id} testID={id}
    accessibilityRole="button" accessibilityState={{selected,disabled}} disabled={disabled} onPress={fn}
    style={[s.button,selected&&s.selected,disabled&&{opacity:.45}]}><Text style={s.text}>{label}</Text></Pressable>;
  const changeMode=(value:boolean)=>{
    sequence.current++;controller.current?.abort();setLoading(false);setError('');setQuotes(null);setPlayer('');setAlternate(value);
  };
  const load=async()=>{
    const id=++sequence.current;controller.current?.abort();const c=new AbortController();controller.current=c;
    const timer=setTimeout(()=>c.abort(),90000);
    setLoading(true);setQuotes(null);setError('');setPlayer('');
    const suffix=alternate?'_alternate':'',markets=['player_pass_yds'+suffix,'player_rush_yds'+suffix];
    try {
      const data=await oddsRequest(`/api/odds/props?sport=${encodeURIComponent(game.sport)}&eventId=${encodeURIComponent(game.eventId)}`+
        markets.map(m=>'&market='+encodeURIComponent(m)).join(''),c.signal);
      if(!Array.isArray(data.quotes)||data.quotes.length>256)throw Error('Player props are unavailable.');
      const valid:Quote[]=data.quotes.filter((q:Quote)=>{
        try{checkQuote(q);return isProp(q.market)&&markets.includes(q.market)&&q.eventId===game.eventId&&q.sport===game.sport&&
          q.homeTeam===game.homeTeam&&q.awayTeam===game.awayTeam&&Date.parse(q.startAt)===Date.parse(game.startAt)&&
          ['fanduel','draftkings'].includes(q.bookmakerKey??'');}catch{return false;}
      });
      // Duplicate provider IDs cannot become distinct selectable offers.
      const counts=new Map<string,number>();valid.forEach(q=>counts.set(q.id,(counts.get(q.id)??0)+1));
      if(id===sequence.current)setQuotes(valid.filter(q=>counts.get(q.id)===1));
    }catch(e){if(id===sequence.current)setError(c.signal.aborted?'Props took too long. Try again.':(e as Error).message);}
    finally{clearTimeout(timer);if(id===sequence.current)setLoading(false);}
  };
  const market=`player_${category}_yds${alternate?'_alternate':''}`;
  const relevant=quotes?.filter(q=>q.market===market)??[],players=[...new Set(relevant.map(q=>q.playerName!))].sort();
  const chosen=players.includes(player)?player:players[0];
  return <View style={s.panel} testID="player-props">
    <Text style={s.title}>NFL player props</Text>
    <Text style={s.note}>Choose a market, then load offered lines for this game. Availability varies by player and sportsbook.</Text>
    <View style={s.row}>
      {button('Passing yards','props-pass',()=>{setCategory('pass');setPlayer('');},category==='pass')}
      {button('Rushing yards','props-rush',()=>{setCategory('rush');setPlayer('');},category==='rush')}
    </View>
    <View style={s.row}>
      {button('Main lines','props-main',()=>changeMode(false),!alternate)}
      {button('Alternate lines','props-alternate',()=>changeMode(true),alternate)}
    </View>
    {button(loading?'Loading props…':quotes?'Refresh player props':'Load player props','load-props',()=>{void load();},false,loading)}
    {loading?<Text role="status" accessibilityLiveRegion="polite" style={s.note}>Loading this game's player props…</Text>:null}
    {error?<Text accessibilityRole="alert" style={s.error}>{error}</Text>:null}
    {quotes&&!relevant.length?<Text style={s.note}>No current {marketLabel(market).toLowerCase()} are offered in this feed. No substitute line has been added.</Text>:null}
    <ScrollView horizontal contentContainerStyle={s.row} accessibilityLabel="Available players">
      {players.map((name,i)=>button(name,'prop-player-'+i,()=>setPlayer(name),name===chosen))}
    </ScrollView>
    {relevant.filter(q=>q.playerName===chosen).map(q=><View key={q.id} style={s.line}>
      {button(`${selectedIds.includes(q.id)?'Added · ':''}${q.label} · ${Number(q.americanOdds)>0?'+':''}${q.americanOdds} · ${q.bookmaker}`,
        'prop-quote-'+q.id,()=>{try{checkQuote(q);onChoose(q);}catch(e){setQuotes(null);setError((e as Error).message);}},selectedIds.includes(q.id))}
      <Text style={s.note}>Updated {localTimestamp(q.updatedAt,timeZone)} · The Odds API</Text>
      {propThresholdNotice(q)?<Text testID={'prop-settlement-'+q.id} style={s.note}>{propThresholdNotice(q)}</Text>:null}
    </View>)}
    <Text style={s.note}>Player lines can join team lines in your parlay. Participation, push and void rules still need verification. Offered prices do not establish a win forecast or a combined same-game payout.</Text>
  </View>;
}
const s=StyleSheet.create({panel:{borderTopWidth:1,borderColor:'#344252',paddingTop:14,gap:10},row:{flexDirection:'row',gap:8,flexWrap:'wrap'},
  button:{padding:12,minHeight:44,borderWidth:1,borderColor:'#344252',borderRadius:10,backgroundColor:'#0E151E'},selected:{borderColor:'#C9F84A'},
  text:{color:'#F1F5F9',fontSize:14,lineHeight:21},title:{color:'#F1F5F9',fontSize:16,fontWeight:'700'},
  note:{color:'#AFBDC9',fontSize:12,lineHeight:19},line:{gap:5},error:{color:'#FFB4AC'}});
