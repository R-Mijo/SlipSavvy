import React, { useState } from 'react';
import {
  KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet,
  Switch, Text, TextInput, View, type TextInputProps,
} from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { compare, type Comparison, type Pick } from './src/math';
import { blankDraft, replacePick, reviewedPick, type Draft } from './src/review';
import BrowseOdds from './src/BrowseOdds';
import { checkQuote, quotePick, type Quote } from './src/odds';

const c = {
  bg: '#0B1016', panel: '#151E29', field: '#0E151E', border: '#344252',
  text: '#F1F5F9', muted: '#AFBDC9', lime: '#C9F84A', ink: '#162005', error: '#FFB4AC',
};
let nextId = 0;
type Editor = { draft: Draft; id: string; step: 'entry' | 'review'; quote?: Quote };

function Button({ title, onPress, secondary = false, disabled = false, testID }: {
  title: string; onPress: () => void; secondary?: boolean; disabled?: boolean; testID?: string;
}) {
  return <Pressable accessibilityRole="button" accessibilityLabel={title}
    accessibilityState={{ disabled }} disabled={disabled} testID={testID} onPress={onPress}
    style={({ pressed }) => [styles.button, secondary && styles.secondary,
      { opacity: disabled ? 0.45 : pressed ? 0.75 : 1 }]}>
    <Text style={[styles.buttonText, secondary && { color: c.text }]}>{title}</Text>
  </Pressable>;
}

function Field({ title, hint, ...props }: TextInputProps & { title: string; hint?: string }) {
  return <View style={styles.fieldGroup}>
    <Text style={styles.label}>{title}</Text>
    <TextInput {...props} accessibilityLabel={title} placeholderTextColor={c.muted}
      style={styles.input} selectionColor={c.lime} />
    {hint ? <Text style={styles.hint}>{hint}</Text> : null}
  </View>;
}

function Detail({ title, value }: { title: string; value: string }) {
  return <View style={styles.detail}><Text style={styles.muted}>{title}</Text>
    <Text selectable style={styles.detailValue}>{value}</Text></View>;
}

function Learn() {
  return <View style={styles.stack}>
    <Text accessibilityRole="header" style={styles.title}>Learn the odds</Text>
    <Text style={styles.body}>Know what the numbers mean before you put money behind them.</Text>
    <View style={styles.card}>
      <Text style={styles.cardTitle}>American odds, in dollars</Text>
      <Detail title="+100" value="$10 stake → $20 total return" />
      <Detail title="+150" value="$10 stake → $25 total return" />
      <Detail title="−110" value="$10 stake → about $19.09 total return" />
      <Text style={styles.body}>Positive odds show the profit on $100. Negative odds show the stake needed for $100 profit. Total return includes your original stake.</Text>
    </View>
    <View style={styles.card}>
      <Text style={styles.cardTitle}>A price is not a prediction</Text>
      <Text style={styles.body}>At −110, you need to win more than 52.38% of identical bets to make a profit over time. That break-even rate comes from the price. It does not tell you how often the selection will actually win, and includes the effect of the bookmaker’s margin.</Text>
    </View>
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Combining selections</Text>
      <Text style={styles.body}>All selections must win. Two independent 50% selections win together 25% of the time. Six independent 60% selections win together about 4.67% of the time.</Text>
      <Text style={styles.body}>Multiply decimal prices, not American odds. Two +100 prices give a hypothetical combined price of +300. A sportsbook may offer a different combined price.</Text>
      <Text style={styles.body}>Different games can still be related. Same-game relationships, pushes, voids, promotions and sportsbook settlement rules are outside this calculator.</Text>
    </View>
    <View style={styles.card}>
      <Text style={styles.cardTitle}>What a /100 estimate means</Text>
      <Text style={styles.body}>A 60/100 hit estimate means an assumed 60% chance. It is not a quality grade or proof that the model is reliable. A 100,000-run simulation reduces sampling noise; it cannot fix a bad assumption.</Text>
      <Text style={styles.body}>This phone preview calculates exact payout scenarios. It does not run the full simulation engine or supply forecasts.</Text>
    </View>
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Keep it affordable</Text>
      <Text style={styles.body}>Only use money you can afford to lose. Set a limit before you start, take breaks, and never chase a loss. This tool does not place bets or guarantee winnings.</Text>
    </View>
  </View>;
}

export default function App() {
  const [tab, setTab] = useState<'check' | 'learn'>('check');
  const [picks, setPicks] = useState<Pick[]>([]);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [stake, setStake] = useState('10');
  const [independent, setIndependent] = useState(false);
  const [results, setResults] = useState<Comparison[] | null>(null);
  const [error, setError] = useState('');

  const invalidate = () => { setResults(null); setError(''); };
  const openEditor = (pick?: Pick) => {
    invalidate();
    setEditor({ draft: pick ? { ...pick } : blankDraft(),
      id: pick?.id ?? `manual-${Date.now()}-${++nextId}`, step: 'entry', quote:pick?.quote });
  };
  const change = (key: keyof Draft, value: string) => {
    if (editor) setEditor({ ...editor, quote:undefined, draft: { ...editor.draft,
      ...(editor.quote?{source:'Edited entry (unverified)',sourceUrl:''}:{}), [key]: value }, step: 'entry' });
    invalidate();
  };
  const review = () => {
    if (!editor) return;
    try {
      reviewedPick(editor.draft, editor.id, new Date().toISOString());
      setError(''); setEditor({ ...editor, step: 'review' });
    } catch (e) { setError((e as Error).message); }
  };
  const confirm = () => {
    if (!editor || editor.step !== 'review') return;
    try {
      const pick = editor.quote ? quotePick(editor.quote) : reviewedPick(editor.draft, editor.id, new Date().toISOString());
      setPicks(replacePick(picks, pick)); setEditor(null); invalidate();
    } catch (e) { setError((e as Error).message); }
  };
  const calculate = () => {
    try {
      if (!picks.length) throw Error('Add and review a selection first.');
      picks.forEach(p=>{if(p.kind==='feed'&&p.quote)checkQuote(p.quote);});
      setResults(compare(picks, stake, independent)); setError('');
    } catch (e) { setResults(null); setError((e as Error).message); }
  };

  return <SafeAreaProvider><SafeAreaView style={styles.safe}>
    <StatusBar style="light" />
    <View style={styles.brandRow}>
      <Text style={styles.brand}>Slip<Text style={{ color: c.lime }}>Savvy</Text></Text>
      <Text style={styles.badge}>PHONE PREVIEW</Text>
    </View>
    <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        {tab === 'learn' ? <Learn /> : <View style={styles.stack}>
          <View>
            <Text accessibilityRole="header" style={styles.title}>Your bets.{"\n"}We’ll do the math.</Text>
            <Text style={styles.body}>Check the price. Understand the tradeoff.</Text>
          </View>
          {error ? <Text accessibilityRole="alert" testID="error" style={styles.error}>{error}</Text> : null}
          {editor ? <View style={styles.card}>
            <Text accessibilityRole="header" style={styles.cardTitle}>
              {editor.step === 'entry' ? '1. Enter a selection' : '2. Review your selection'}
            </Text>
            {editor.step === 'entry' ? <>
              <Field title="Selection" testID="selection" value={editor.draft.label}
                placeholder="Example: Home team to win" maxLength={160} onChangeText={v => change('label', v)} />
              <Field title="Game or event" testID="event" value={editor.draft.event}
                placeholder="Example: Away at Home, Nov 8" maxLength={160} onChangeText={v => change('event', v)}
                hint="Use the same game name for selections from the same event." />
              <Field title="American odds" testID="odds" value={editor.draft.odds}
                placeholder="−110 or +150" maxLength={10} autoCapitalize="none" autoCorrect={false}
                onChangeText={v => change('odds', v)} hint="Use the minus key (-) for negative odds." />
              <Text style={styles.sectionLabel}>OPTIONAL CONTEXT</Text>
              <Field title="Your estimated win chance (%)" testID="chance" value={editor.draft.fairPercent}
                placeholder="Leave blank if unknown" keyboardType="decimal-pad" maxLength={20}
                onChangeText={v => change('fairPercent', v)}
                hint="Your assumption, not a SlipSavvy forecast. No estimate is inferred from the price." />
              <Field title="Source name" testID="source" value={editor.draft.source}
                placeholder="Where you found the price" maxLength={200} onChangeText={v => change('source', v)} />
              <Field title="Source URL" testID="source-url" value={editor.draft.sourceUrl}
                placeholder="https://…" keyboardType="url" autoCapitalize="none" autoCorrect={false}
                maxLength={300} onChangeText={v => change('sourceUrl', v)}
                hint="Reference only. Prices and source contents are not fetched or verified." />
              <Button title="Review selection" testID="review" onPress={review} />
            </> : <>
              <Detail title="Selection" value={editor.draft.label.trim()} />
              <Detail title="Game" value={editor.draft.event.trim()} />
              <Detail title="Odds" value={editor.draft.odds.trim()} />
              <Detail title="Your estimated chance" value={editor.draft.fairPercent.trim() ? `${editor.draft.fairPercent.trim()}% (assumed)` : 'Unknown — payout math only'} />
              <Detail title="Source" value={editor.draft.source.trim() || 'Manual entry (unverified)'} />
              {editor.draft.sourceUrl.trim() ? <Detail title="Reference" value={editor.draft.sourceUrl.trim()} /> : null}
              <Text style={styles.body}>Check the selection, game and sign on the odds. This preview covers win-or-lose outcomes. Prices can change; verify with your sportsbook. Pushes, voids and promotions are excluded.</Text>
              <Button title="Confirm selection" testID="confirm" onPress={confirm} />
              <Button title="Edit details" secondary testID="back-to-edit"
                onPress={() => { setEditor({ ...editor, step: 'entry' }); setError(''); }} />
            </>}
            <Button title="Cancel changes" secondary testID="cancel" onPress={() => { setEditor(null); setError(''); }} />
          </View> : <>
            <BrowseOdds onChoose={quote=>{const p=quotePick(quote);invalidate();setEditor({draft:{...p},id:p.id,step:'review',quote});}} />
            <View style={styles.row}>
              <Text style={styles.cardTitle}>Your selections</Text>
              <Text style={styles.muted}>{picks.length}/8</Text>
            </View>
            {!picks.length ? <View style={styles.card}>
              <Text style={styles.cardTitle}>Start with one selection</Text>
              <Text style={styles.body}>Enter the price you see. Review it, then check what a win and a loss would mean.</Text>
            </View> : picks.map((pick, i) => <View key={pick.id} style={styles.card} testID={`pick-${i}`}>
              <View style={styles.row}><Text style={styles.selectionTitle}>{pick.label}</Text>
                <Text style={styles.price}>{pick.odds}</Text></View>
              <Text style={styles.muted}>{pick.event}</Text>
              <Text style={styles.hint}>{pick.source} · Entered {new Date(pick.capturedAt).toLocaleString()}</Text>
              <Text style={styles.hint}>{pick.fairPercent ? `Your win estimate: ${pick.fairPercent}% (assumed)` : 'Win chance unknown'}</Text>
              <View style={styles.actionRow}>
                <Button title={`Edit selection ${i + 1}`} secondary testID={`edit-${i}`} onPress={() => openEditor(pick)} />
                <Button title={`Remove selection ${i + 1}`} secondary testID={`remove-${i}`}
                  onPress={() => { setPicks(picks.filter(p => p.id !== pick.id)); invalidate(); }} />
              </View>
            </View>)}
            <Button title="Add selection" testID="add" disabled={picks.length >= 8} onPress={() => openEditor()} />
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Check the payout</Text>
              <Field title="Stake per scenario ($)" testID="stake" value={stake} maxLength={20}
                keyboardType="decimal-pad" onChangeText={v => { setStake(v); invalidate(); }}
                hint="Each result uses this stake separately. No money is placed or allocated." />
              <View style={styles.switchRow}>
                <Text style={[styles.body, styles.flex]}>Compare combinations of 2 or 3 selections from different games</Text>
                <Switch accessibilityLabel="Compare independent combinations" testID="independent"
                  value={independent} trackColor={{ false: c.border, true: c.lime }}
                  thumbColor={c.text} onValueChange={v => { setIndependent(v); invalidate(); }} />
              </View>
              <Text style={styles.hint}>Turning this on assumes different games are independent. Same-game combinations are excluded based on the game names you enter. Combined prices are hypothetical; check the sportsbook’s actual offer.</Text>
              <Button title="Check my bets" testID="calculate" disabled={!picks.length} onPress={calculate} />
            </View>
            {results ? <View style={styles.stack} testID="results">
              <Text accessibilityRole="header" style={styles.title}>The math, explained</Text>
              <Text style={styles.body}>Each card is a separate what-if scenario. A loss costs the full ${stake} stake. Returns are rounded to cents; the calculation uses exact fractions.</Text>
              {results.map(result => <View style={styles.card} key={result.ids.join('|')}>
                <Text style={styles.sectionLabel}>{result.legs === 1 ? 'ONE SELECTION' : `${result.legs} SELECTIONS · ALL MUST WIN`}</Text>
                <Text style={styles.cardTitle}>{result.label}</Text>
                <Text style={styles.hint}>{result.legs > 1 ? 'Hypothetical combined price' : 'Entered price'}: {result.multiplier} decimal</Text>
                <Detail title="Total returned if you win" value={result.gross} />
                <Detail title="Profit if you win" value={result.net} />
                <Detail title="Break-even win rate" value={result.breakEven} />
                <Text style={styles.hint}>Break-even is a price threshold, not a win forecast.</Text>
                <Detail title="Chance under your assumptions" value={result.estimatedChance ?? 'Unknown'} />
                {result.expectedNet !== null ? <>
                  <Detail title="Average net under your assumptions" value={result.expectedNet} />
                  <Text style={styles.hint}>A long-run model average per scenario, not your likely next return. It depends on your estimates{result.legs > 1 ? ' and the independence assumption' : ''}.</Text>
                </> : <Text style={styles.hint}>Add your own win estimates to explore an assumed chance and average net. SlipSavvy has not verified a predictive edge.</Text>}
              </View>)}
            </View> : null}
          </>}
          <Text style={styles.footer}>Private session · Entries stay in memory and clear when the app reloads. No account, payment or bet placement. For adults of legal betting age where permitted.</Text>
        </View>}
      </ScrollView>
    </KeyboardAvoidingView>
    <View style={styles.nav}>
      {(['check', 'learn'] as const).map(t => <Pressable key={t} accessibilityRole="tab"
        accessibilityState={{ selected: tab === t }} testID={`tab-${t}`}
        onPress={() => setTab(t)} style={[styles.navItem, tab === t && styles.navSelected]}>
        <Text style={[styles.navText, tab === t && { color: c.lime }]}>{t === 'check' ? 'Check My Bets' : 'Learn the Odds'}</Text>
      </Pressable>)}
    </View>
  </SafeAreaView></SafeAreaProvider>;
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: c.bg }, flex: { flex: 1 },
  brandRow: { paddingHorizontal: 20, paddingVertical: 14, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10, borderBottomWidth: 1, borderColor: c.border },
  brand: { color: c.text, fontSize: 24, fontWeight: '800', letterSpacing: -1 },
  badge: { color: c.lime, fontSize: 10, letterSpacing: 1.1, fontWeight: '700' },
  content: { padding: 20, width: '100%', maxWidth: 720, alignSelf: 'center', paddingBottom: 36 },
  stack: { gap: 18 }, title: { color: c.text, fontSize: 30, lineHeight: 36, fontWeight: '800', letterSpacing: -0.8 },
  body: { color: c.muted, fontSize: 15, lineHeight: 23 }, muted: { color: c.muted, fontSize: 14, lineHeight: 21, flexShrink: 1 },
  hint: { color: c.muted, fontSize: 12, lineHeight: 19 }, footer: { color: c.muted, fontSize: 12, lineHeight: 19, paddingVertical: 10 },
  card: { backgroundColor: c.panel, borderRadius: 18, borderWidth: 1, borderColor: c.border, padding: 18, gap: 14 },
  cardTitle: { color: c.text, fontSize: 18, lineHeight: 25, fontWeight: '700', flexShrink: 1 },
  selectionTitle: { color: c.text, fontSize: 18, lineHeight: 25, fontWeight: '700', flex: 1 },
  price: { color: c.lime, fontWeight: '800', fontSize: 21 },
  sectionLabel: { color: c.lime, fontSize: 11, fontWeight: '700', letterSpacing: 1.1 },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 },
  actionRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  fieldGroup: { gap: 7 }, label: { color: c.text, fontSize: 14, fontWeight: '600' },
  input: { borderColor: c.border, borderWidth: 1, borderRadius: 10, paddingHorizontal: 13, paddingVertical: 13, color: c.text, backgroundColor: c.field, fontSize: 16, minHeight: 48 },
  button: { minHeight: 48, backgroundColor: c.lime, paddingVertical: 13, paddingHorizontal: 16, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  secondary: { backgroundColor: c.field, borderWidth: 1, borderColor: c.border },
  buttonText: { color: c.ink, fontWeight: '700', fontSize: 14, textAlign: 'center' },
  switchRow: { flexDirection: 'row', alignItems: 'center', gap: 16 },
  detail: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: 8, borderBottomWidth: 1, borderColor: c.border, paddingBottom: 10 },
  detailValue: { color: c.text, fontSize: 15, lineHeight: 22, fontWeight: '600', flexShrink: 1 },
  error: { color: c.error, padding: 14, backgroundColor: '#342125', borderRadius: 10, fontSize: 14, lineHeight: 21 },
  nav: { flexDirection: 'row', borderTopWidth: 1, borderColor: c.border, padding: 10, gap: 8 },
  navItem: { flex: 1, minHeight: 48, justifyContent: 'center', alignItems: 'center', borderRadius: 10, padding: 8 },
  navSelected: { backgroundColor: c.panel }, navText: { color: c.muted, fontWeight: '700', fontSize: 14 },
});
