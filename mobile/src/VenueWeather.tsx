import React,{useState} from 'react';
import {Pressable,StyleSheet,Text,View} from 'react-native';
import type {EventReport} from './reports';
import {localTimestamp} from './games';

export default function VenueWeather({event,timeZone,SourceLink}:{event?:EventReport;timeZone:string;SourceLink:React.ComponentType<{url:string;label:string}>}){
  const [open,setOpen]=useState(false),venue=event?.venue,w=event?.weather;
  const v=w?.values;
  const value=(n:number|null|undefined,unit:string)=>n===null||n===undefined?'Unavailable':`${Math.round(n*10)/10}${unit}`;
  const nws=w?.provider==='NWS',wind=w?.windRangeMph?`${w.windRangeMph.low}–${w.windRangeMph.high} mph`:value(v?.[nws?'windSpeedMph':'wind_speed_10m'],' mph');
  return <View style={s.stack} testID="venue-weather">
    <Text style={s.title}>Venue & kickoff weather</Text>
    {venue?.status==='matched_catalog'?<><Text style={s.text}>{venue.name} · {venue.roof==='outdoor'?'Open-air field':venue.roof==='indoor'?'Fixed indoor roof':'Retractable roof; current state unknown'}</Text>
      <Text style={s.note}>Matched to this game's reported stadium ID and name.</Text></>:null}
    {w?.status==='available'?<>
      <Text style={s.text}>Temperature: {value(v?.[nws?'temperatureF':'temperature_2m'],'°F')} · wind: {wind}</Text>
      <Text style={s.text}>Precipitation chance: {value(v?.[nws?'precipitationChance':'precipitation_probability'],'%')} · gusts: {value(v?.[nws?'windGustMph':'wind_gusts_10m'],' mph')}</Text>
      <Text style={s.note}>Kickoff-hour forecast · {w.attribution}. A grid forecast is not a stadium observation or a change to the win estimate.</Text>
      {w.providerUpdatedAt?<Text style={s.note}>Forecast updated {localTimestamp(w.providerUpdatedAt,timeZone)} · retrieved {localTimestamp(w.retrievedAt!,timeZone)}</Text>:null}
      {w.missingFields?.length?<Text style={s.note}>Some forecast fields are unavailable; missing values are not zero.</Text>:null}
      {w.sourceUrl?<SourceLink url={w.sourceUrl} label="Weather source"/>:null}
    </>:<Text style={s.note}>{w?.status==='not_applicable'?'Verified indoor or closed roof: outdoor weather is not applied to play.':
      w?.reason==='roof_state_unknown'?'The retractable roof state is unverified. Weather applicability is unknown.':
      w?.reason==='weather_forecast_stale'?'The forecast is stale. No weather values are shown.':
      venue?.status==='unavailable'?'This venue is not currently verified for weather. No home-city forecast is substituted.':'Verified venue/roof or kickoff-hour forecast is unavailable.'}</Text>}
    {venue?.status==='matched_catalog'?<>
      <Pressable accessibilityRole="button" accessibilityState={{expanded:open}} testID="venue-sources-toggle" style={s.button} onPress={()=>setOpen(!open)}><Text style={s.link}>{open?'Hide venue sources':'Venue sources'}</Text></Pressable>
      {open?<View style={s.stack}>{venue.sources.map(source=><SourceLink key={source.url} url={source.url} label={source.publisher}/>)}
        <Text style={s.note}>Venue facts checked {localTimestamp(venue.checkedAt,timeZone)}. Catalog coverage is limited; a retractable roof requires current event evidence.</Text></View>:null}
    </>:null}
  </View>;
}
const s=StyleSheet.create({stack:{gap:8},title:{color:'#F1F5F9',fontSize:15,fontWeight:'700'},text:{color:'#F1F5F9',fontSize:14,lineHeight:21},
  note:{color:'#AFBDC9',fontSize:12,lineHeight:19},button:{padding:12,minHeight:44,borderWidth:1,borderColor:'#344252',borderRadius:10},link:{color:'#C9F84A',fontSize:14}});
