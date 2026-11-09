import React,{useEffect,useState} from 'react';
import {Pressable,ScrollView,Text,View} from 'react-native';
import {oddsRequest} from './odds';
import {flow} from './FlowUI';
const icon=(key:string)=>key.startsWith('americanfootball')?'🏈':key.startsWith('basketball')?'🏀':key.startsWith('baseball')?'⚾':key.startsWith('icehockey')?'🏒':key.startsWith('soccer')?'⚽':'🏆';
export default function SportPicker({sport,onChange}:{sport:string;onChange:(s:string)=>void}) {
  const [sports,setSports]=useState<{key:string;title:string}[]>([]),[error,setError]=useState(''),[retry,setRetry]=useState(0);
  useEffect(()=>{let active=true;const c=new AbortController(),timer=setTimeout(()=>c.abort(),30000);setError('');
    void oddsRequest('/api/sports',c.signal).then(data=>{
      if(!Array.isArray(data.sports))throw Error('Sports are temporarily unavailable.');
      if(active)setSports(data.sports.filter((s:any)=>s&&typeof s.key==='string'&&typeof s.title==='string'));
    }).catch(e=>{if(active)setError(c.signal.aborted?'Sports took too long to load.':e.message);}).finally(()=>clearTimeout(timer));
    return()=>{active=false;c.abort();clearTimeout(timer);};
  },[retry]);
  return <View style={flow.stack}><ScrollView horizontal contentContainerStyle={{gap:8}} accessibilityLabel="Select sport">
    {sports.map(s=><Pressable key={s.key} testID={'sport-'+s.key} accessibilityRole="button" accessibilityLabel={s.title} accessibilityState={{selected:s.key===sport}}
      onPress={()=>onChange(s.key)} style={[flow.chip,s.key===sport&&flow.selected]}><Text style={flow.text}>{icon(s.key)} {s.title}</Text></Pressable>)}
  </ScrollView>{!sports.length&&!error?<Text style={flow.note}>Loading sports…</Text>:null}
    {error?<><Text accessibilityRole="alert" style={flow.error}>{error}</Text><Pressable accessibilityRole="button" style={flow.chip} onPress={()=>setRetry(v=>v+1)}><Text style={flow.text}>Retry sports</Text></Pressable></>:null}</View>;
}
