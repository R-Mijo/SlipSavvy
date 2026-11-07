import React,{useMemo,useState} from 'react';
import {Pressable,ScrollView,StyleSheet,Text,TextInput,View} from 'react-native';
import {deviceZone,timeZones,validZone} from './games';

export default function TimeZoneChoice({zone,onChange}:{zone:string;onChange:(zone:string)=>void}) {
  const [open,setOpen]=useState(false),[search,setSearch]=useState('');
  const zones=useMemo(timeZones,[]),needle=search.trim().toLowerCase().replace(/ /g,'_');
  const matches=zones.filter(z=>z.toLowerCase().includes(needle));
  // Runtimes without a complete zone inventory can still accept any valid IANA zone.
  if(search.trim()&&validZone(search.trim())&&!matches.includes(search.trim()))matches.unshift(search.trim());
  const choose=(value:string)=>{onChange(value);setOpen(false);setSearch('');};
  return <View style={s.panel}>
    <Pressable testID="timezone-toggle" accessibilityRole="button" accessibilityState={{expanded:open}} onPress={()=>setOpen(!open)} style={s.button}>
      <Text style={s.text}>Time zone: {zone.replace(/_/g,' ')} · Change</Text>
    </Pressable>
    {open?<View style={s.stack}>
      <Text style={s.note}>Starts with your device time zone. Dates and morning, afternoon and night groups use your choice. This choice lasts for this session.</Text>
      <Pressable testID="timezone-device" accessibilityRole="button" onPress={()=>choose(deviceZone())} style={s.button}><Text style={s.text}>Use device time zone</Text></Pressable>
      <TextInput testID="timezone-search" accessibilityLabel="Find a time zone by city" value={search} onChangeText={setSearch} placeholder="Search city, e.g. New York" placeholderTextColor="#AFBDC9" autoCapitalize="none" style={s.input}/>
      <ScrollView style={{maxHeight:240}} nestedScrollEnabled keyboardShouldPersistTaps="handled" accessibilityLabel="Time zones">
        {matches.map(value=><Pressable key={value} testID={'timezone-'+value} accessibilityRole="button" accessibilityState={{selected:zone===value}} onPress={()=>choose(value)} style={s.button}>
          <Text style={[s.text,zone===value&&{color:'#C9F84A'}]}>{value.replace(/_/g,' ')}</Text>
        </Pressable>)}
        {!matches.length?<Text style={s.note}>No matching time zones. Try another city.</Text>:null}
      </ScrollView>
    </View>:null}
  </View>;
}
const s=StyleSheet.create({panel:{gap:10},stack:{gap:8},button:{minHeight:44,justifyContent:'center',padding:10},text:{color:'#F1F5F9',fontSize:14,lineHeight:21},note:{color:'#AFBDC9',fontSize:12,lineHeight:19},input:{backgroundColor:'#0E151E',borderColor:'#344252',borderWidth:1,borderRadius:10,padding:12,minHeight:48,color:'#F1F5F9',fontSize:16}});
