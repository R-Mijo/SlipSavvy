import React,{useEffect,useRef,useState} from 'react';
import {Pressable,Text,TextInput,View} from 'react-native';
import {checkQuote,oddsRequest,quotePick,type Quote} from './odds';
import type {Pick} from './math';
import {candidates,eventKey,selectionReason} from './tickets';
import {Fold,flow} from './FlowUI';
import {researchCandidates,reviewCandidate,type ReviewedCandidate} from './candidateResearch';
import type {GameReports} from './reports';

export default function SavvyBuilder({sport,stake,target,onStake,onTarget,onChoose}:{sport:string;stake:string;target:string;onStake:(v:string)=>void;onTarget:(v:string)=>void;onChoose:(p:Pick[],report?:GameReports)=>void}) {
  const [legs,setLegs]=useState(3),[book,setBook]=useState('fanduel'),[props,setProps]=useState(false),[alts,setAlts]=useState(false);
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notes,setNotes]=useState(''),[results,setResults]=useState<ReviewedCandidate[]>([]),[offers,setOffers]=useState<Quote[]>([]);
  const controller=useRef<AbortController|null>(null),seq=useRef(0);
  const key=JSON.stringify([sport,stake,target,legs,book,props,alts]),currentKey=useRef(key);currentKey.current=key;
  useEffect(()=>{seq.current++;controller.current?.abort();setBusy(false);setResults([]);setError('');setNotes('');
    return()=>{seq.current++;controller.current?.abort();};},[key]);
  const choose=(c:ReviewedCandidate)=>{try{const current=reviewCandidate(c,c.report);if(current.review.blocked)throw Error('This ticket has a line or availability concern. Choose another candidate or refresh.');onChoose(c.quotes.map(q=>quotePick(q)),current.report);}catch(e){setError((e as Error).message);setResults([]);}};
  const build=async()=>{
    // Validate before making any requests that could use the existing odds quota.
    try{candidates([],sport,book,legs,Number(stake),Number(target));}catch(e){setError((e as Error).message);return;}
    const id=++seq.current,c=new AbortController();controller.current?.abort();controller.current=c;
    const timer=setTimeout(()=>c.abort(),150000);setBusy(true);setError('');setNotes('');setResults([]);
    try {
      const pool:Quote[]=[],missing:string[]=[];
      const batches=await Promise.allSettled(['h2h','spreads','totals'].map(async market=>{
        const data=await oddsRequest(`/api/odds?sport=${encodeURIComponent(sport)}&market=${market}`,c.signal);
        if(!Array.isArray(data.quotes)||data.quotes.length>4096)throw Error('Invalid market response.');
        return data.quotes.filter((q:Quote)=>{try{checkQuote(q);return q.sport===sport&&q.market===market&&q.bookmakerKey===book;}catch{return false;}}) as Quote[];
      }));
      batches.forEach((r,i)=>r.status==='fulfilled'?pool.push(...r.value):missing.push(['moneyline','spread','total'][i]));
      if(id!==seq.current||c.signal.aborted)return;
      // Explicit opt-in, four earliest exact events maximum; no whole-slate props crawl.
      if(props&&sport==='americanfootball_nfl') {
        const games=[...new Map(pool.slice().sort((a,b)=>Date.parse(a.startAt)-Date.parse(b.startAt)).map(q=>[eventKey(q),q])).values()].slice(0,4);
        for(const game of games)for(const suffix of alts?['','_alternate']:['']){
          if(id!==seq.current||c.signal.aborted)return;
          try {
            const markets=['player_pass_yds'+suffix,'player_rush_yds'+suffix];
            const data=await oddsRequest(`/api/odds/props?sport=${encodeURIComponent(sport)}&eventId=${encodeURIComponent(game.eventId)}`+markets.map(m=>'&market='+m).join(''),c.signal);
            if(!Array.isArray(data.quotes)||data.quotes.length>256)throw Error('Invalid prop response.');
            pool.push(...data.quotes.filter((q:Quote)=>{try{checkQuote(q);return q.sport===sport&&q.bookmakerKey===book&&q.eventId===game.eventId&&q.startAt===game.startAt&&q.homeTeam===game.homeTeam&&q.awayTeam===game.awayTeam&&markets.includes(q.market);}catch{return false;}}));
          }catch{missing.push('some player props');}
        }
      }
      if(id!==seq.current||currentKey.current!==key||c.signal.aborted)return;
      const found=candidates(pool,sport,book,legs,Number(stake),Number(target));
      if(!found.length)throw Error(`There are not ${legs} usable games at this sportsbook. Try fewer legs or choose your own lines.`);
      setNotes('Reviewing current prices, injuries, weather and context…');
      const reviewed=await researchCandidates(found,stake,target,c.signal);
      if(id!==seq.current||currentKey.current!==key||c.signal.aborted)return;
      setOffers(pool);setResults(reviewed);setNotes(missing.length?'Some markets were unavailable: '+[...new Set(missing)].join(', ')+'. Candidates use only the available offers.':'');
      const usable=reviewed.find(r=>!r.review.blocked);
      if(usable)choose(usable);else setError('The checked tickets have changed lines or listed availability concerns. Review below or try another sport/book.');
    }catch(e){if(id===seq.current)setError(c.signal.aborted?'Building took too long. Try again.':(e as Error).message);}
    finally{clearTimeout(timer);if(id===seq.current){setBusy(false);if(c.signal.aborted)setError('Building took too long. Try again.');}}
  };
  const chip=(label:string,id:string,selected:boolean,fn:()=>void)=><Pressable key={id} testID={id} accessibilityRole="button" accessibilityState={{selected}} style={[flow.chip,selected&&flow.selected]} onPress={fn}><Text style={flow.text}>{label}</Text></Pressable>;
  return <View style={flow.stack} testID="savvy-builder"><Text style={flow.title}>Your ticket. Your target.</Text>
    <Text style={flow.note}>Choose your preferences. We’ll suggest a ticket and research its lines.</Text>
    <View style={flow.card}>
      <Text style={flow.subtitle}>Sportsbook</Text><View style={flow.wrap}>{chip('FanDuel','book-fanduel',book==='fanduel',()=>setBook('fanduel'))}{chip('DraftKings','book-draftkings',book==='draftkings',()=>setBook('draftkings'))}</View>
      <Text style={flow.subtitle}>Legs</Text><View style={flow.wrap}>{[2,3,4].map(n=>chip(String(n),'builder-legs-'+n,legs===n,()=>setLegs(n)))}</View>
      <Text style={flow.subtitle}>Stake</Text><View style={flow.wrap}>{['5','10','20'].map(v=>chip('$'+v,'stake-'+v,stake===v,()=>onStake(v)))}</View>
      <Text style={flow.subtitle}>Desired total return ($)</Text><TextInput testID="builder-target" accessibilityLabel="Desired total return including stake" keyboardType="decimal-pad" value={target} onChangeText={onTarget} maxLength={9} style={flow.input}/>
      <Text style={flow.note}>Includes your stake. The target guides selection; it is not a promised payout.</Text>
      {sport==='americanfootball_nfl'?<><View style={flow.wrap}>{chip('Include player props','builder-props',props,()=>setProps(!props))}{props?chip('Include alternate props','builder-alts',alts,()=>setAlts(!alts)):null}</View>
        {props?<Text style={flow.note}>Checks passing and rushing props for up to four upcoming games using your connected feed. Unclear milestone settlement is excluded from generated tickets.</Text>:null}</>:null}
      <Pressable testID="build-savvy" accessibilityRole="button" disabled={!sport||busy} accessibilityState={{disabled:!sport||busy}} style={[flow.action,(!sport||busy)&&{opacity:.45}]} onPress={()=>{void build();}}><Text style={flow.actionText}>{busy?'Building & checking your ticket…':'Build & research my parlay'}</Text></Pressable>
      {!sport?<Text style={flow.note}>Select a sport above to begin.</Text>:null}
      {busy&&notes?<Text role="status" style={flow.note}>{notes}</Text>:null}
      {busy?<Pressable testID="cancel-builder" accessibilityRole="button" style={flow.chip} onPress={()=>{seq.current++;controller.current?.abort();setBusy(false);}}><Text style={flow.text}>Cancel</Text></Pressable>:null}
      {error?<Text testID="builder-error" accessibilityRole="alert" style={flow.error}>{error}</Text>:null}
    </View>
    {results.length?<View style={flow.card} testID="builder-results"><Text style={flow.subtitle}>Ticket options ready</Text>
      <Text style={flow.note}>We check up to three price-matched candidates, then prefer current verified prices with fewer research gaps, then fewer listed concerns. This is a source-check ranking, not a prediction of the winning ticket.</Text>
      {notes?<Text style={flow.note}>{notes}</Text>:null}
      <Text style={flow.text}>First eligible suggestion: {results.find(r=>!r.review.blocked)?'$'+results.find(r=>!r.review.blocked)!.returnAmount.toFixed(2)+' estimated total return':'none from the checked candidates'}</Text>
      {results.find(r=>!r.review.blocked)?<Text style={flow.note}>{Math.abs(results.find(r=>!r.review.blocked)!.returnAmount-Number(target)).toFixed(2)} dollars {results.find(r=>!r.review.blocked)!.returnAmount>=Number(target)?'above':'below'} target.</Text>:null}
      <Fold title="Compare candidates & reasons" id="candidate-comparisons">{results.map((r,i)=><View key={r.quotes.map(q=>q.id).join('|')} style={flow.stack}>
        <Text style={flow.text}>{r.review.blocked?'Needs attention':i===0?'Suggested ticket':'Alternative '+i} · estimated total return ${r.returnAmount.toFixed(2)}</Text>
        <Text style={flow.note}>{r.returnAmount>=Number(target)?'$'+(r.returnAmount-Number(target)).toFixed(2)+' above target':'$'+(Number(target)-r.returnAmount).toFixed(2)+' below target'} · confirm the combined price in {book==='fanduel'?'FanDuel':'DraftKings'}.</Text>
        {r.review.reasons.map((reason,j)=><Text key={j} style={flow.note}>{reason}</Text>)}
        {r.quotes.map(q=><View key={q.id} style={flow.stack}><Text style={flow.text}>{q.label} · {Number(q.americanOdds)>0?'+':''}{q.americanOdds}</Text><Text style={flow.note}>{selectionReason(q,r,offers,Number(stake),Number(target))}</Text></View>)}
        <Pressable testID={'use-candidate-'+i} accessibilityRole="button" disabled={r.review.blocked} accessibilityState={{disabled:r.review.blocked}} style={[flow.chip,r.review.blocked&&{opacity:.45}]} onPress={()=>choose(r)}><Text style={flow.text}>Use & research this ticket</Text></Pressable>
      </View>)}</Fold>
    </View>:null}
  </View>;
}
