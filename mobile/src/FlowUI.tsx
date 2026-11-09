import React,{useState} from 'react';
import {Pressable,StyleSheet,Text,View} from 'react-native';
import {levels,ticketPrice} from './tickets';
import type {Pick} from './math';

export function Fold({title,id,children}:{title:string;id:string;children:React.ReactNode}) {
  const [open,setOpen]=useState(false);
  return <View style={flow.card}><Pressable testID={id} accessibilityRole="button" accessibilityState={{expanded:open}} aria-expanded={open}
    onPress={()=>setOpen(!open)} style={flow.row}><Text style={flow.subtitle}>{title}</Text><Text style={flow.accent}>{open?'−':'+'}</Text></Pressable>
    {open?<View style={flow.stack}>{children}</View>:null}</View>;
}
export function Meter({picks,now}:{picks:Pick[];now:number}) {
  const price=ticketPrice(picks,now),level=price?levels[Math.min(4,Math.floor(price.score/20))]:null;
  return <View style={flow.stack} testID="confidence-meter"><Text style={flow.subtitle}>Odds-based confidence</Text>
    {price&&level?<><Text style={[flow.score,{color:level.color}]}>{price.score<.1?'<0.1':price.score.toFixed(1)}/100 · {level.label}</Text>
      <View style={flow.spectrum} accessibilityRole="progressbar" accessibilityLabel="Price-implied score" accessibilityValue={{min:0,max:100,now:price.score}}>
        {levels.map(l=><View key={l.label} style={{flex:1,height:8,backgroundColor:l.color}}/>)}
        <View style={[flow.marker,{left:`${Math.min(99,price.score)}%`}]}/>
      </View><Text style={flow.note}>Based on sportsbook odds. {picks.length>1?'Estimated from individual prices; confirm the combined quote. ':''}Includes the bookmaker’s margin; this is not a forecast or a measure of bet value.</Text></>:
      <Text style={flow.note}>{picks.length?'A same-game or mixed-book ticket needs a current combined sportsbook quote for this score. Expired lines need refreshing.':'Add current lines to see the score.'}</Text>}
  </View>;
}
export const flow=StyleSheet.create({stack:{gap:12},card:{backgroundColor:'#151E29',borderWidth:1,borderColor:'#344252',borderRadius:16,padding:16,gap:12},
  row:{flexDirection:'row',alignItems:'center',justifyContent:'space-between',gap:10,minHeight:44},wrap:{flexDirection:'row',flexWrap:'wrap',gap:8},
  title:{color:'#F1F5F9',fontSize:27,fontWeight:'800'},subtitle:{color:'#F1F5F9',fontSize:16,fontWeight:'700'},text:{color:'#F1F5F9',fontSize:14,lineHeight:21},
  note:{color:'#AFBDC9',fontSize:12,lineHeight:19},accent:{color:'#C9F84A',fontSize:16},error:{color:'#FFB4AC',fontSize:14,lineHeight:21},
  chip:{padding:12,minHeight:44,borderRadius:10,borderWidth:1,borderColor:'#344252',backgroundColor:'#0E151E'},selected:{borderColor:'#C9F84A'},
  action:{padding:15,minHeight:48,borderRadius:10,backgroundColor:'#C9F84A'},actionText:{color:'#162005',fontSize:15,fontWeight:'700',textAlign:'center'},
  input:{backgroundColor:'#0E151E',borderColor:'#344252',borderWidth:1,borderRadius:10,color:'#F1F5F9',padding:12,minHeight:48,fontSize:16},
  score:{fontSize:23,fontWeight:'800'},spectrum:{flexDirection:'row',position:'relative',marginVertical:5},marker:{position:'absolute',height:18,width:3,backgroundColor:'#FFFFFF',top:-5}});
