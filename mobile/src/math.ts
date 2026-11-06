/** Apache-2.0. Copyright 2026 Marco Armijo (R-Mijo).
 * Small, exact mobile calculator. The Python package remains the full scenario engine.
 */
export type Ratio = { n: bigint; d: bigint };
const gcd = (a: bigint, b: bigint): bigint => b === 0n ? (a < 0n ? -a : a) : gcd(b, a % b);
export function ratio(n: bigint, d = 1n): Ratio {
  if (!d) throw Error('A denominator cannot be zero.');
  if (d < 0n) { n = -n; d = -d; }
  const g = gcd(n, d); return { n: n / g, d: d / g };
}
export const mul = (a: Ratio, b: Ratio) => ratio(a.n * b.n, a.d * b.d);
export const sub = (a: Ratio, b: Ratio) => ratio(a.n * b.d - b.n * a.d, a.d * b.d);
export const inverse = (a: Ratio) => ratio(a.d, a.n);
export const number = (a: Ratio) => Number(a.n) / Number(a.d);
export function decimal(value: string): Ratio {
  if (typeof value !== 'string' || !/^\d{1,9}(?:\.\d{1,6})?$/.test(value.trim())) throw Error('Enter a positive number with up to six decimal places.');
  const [a, b = ''] = value.trim().split('.'); return ratio(BigInt(a + b), 10n ** BigInt(b.length));
}
export function american(value: string): Ratio {
  if (typeof value !== 'string' || !/^[+-]?\d{3,6}$/.test(value.trim())) throw Error('Use American odds, such as -110 or +150.');
  const odds = BigInt(value.trim());
  if (odds > -100n && odds < 100n || odds > 100000n || odds < -100000n) throw Error('Odds must be -100 or lower, or +100 or higher, within 100000.');
  return odds > 0n ? ratio(odds + 100n, 100n) : ratio(-odds + 100n, -odds);
}
export const percent = (a: Ratio) => `${(number(a) * 100).toFixed(2)}%`;
export function money(a: Ratio): string {
  const sign = a.n < 0n ? '-' : ''; const n = a.n < 0n ? -a.n : a.n;
  const cents = (n * 100n * 2n + a.d) / (2n * a.d);
  return `${sign}$${cents / 100n}.${String(cents % 100n).padStart(2, '0')}`;
}
export type Pick = {
  id: string; label: string; event: string; odds: string; fairPercent: string;
  source: string; sourceUrl: string; capturedAt: string; kind: 'manual' | 'screenshot' | 'example'; confirmed: boolean;
};
export function validatePick(p: Pick): Pick {
  if (!p || typeof p !== 'object' || !['id','label','event','source','sourceUrl','capturedAt','odds','fairPercent'].every(k => typeof (p as any)[k] === 'string')) throw Error('The pick is incomplete.');
  if (!p.label.trim() || !p.event.trim() || !p.source.trim()) throw Error('Add a selection, event and source.');
  if ([p.id,p.label,p.event,p.source,p.sourceUrl].some(v => v.length > 300) || !p.id || p.fairPercent.length > 20 || p.odds.length > 10) throw Error('A field is too long.');
  american(p.odds);
  if (p.fairPercent.trim()) { const p1 = decimal(p.fairPercent); if (p1.n > p1.d * 100n) throw Error('Estimated chance must be between 0 and 100%.'); }
  if (p.sourceUrl && !/^https?:\/\/[^\s]+$/i.test(p.sourceUrl)) throw Error('Source links must start with https:// or http://.');
  if (!Number.isFinite(Date.parse(p.capturedAt))) throw Error('Add a valid capture date.');
  if (!['manual','screenshot','example'].includes(p.kind) || p.confirmed !== true) throw Error('Review and confirm each pick before adding it.');
  return { ...p, label: p.label.trim(), event: p.event.trim(), source: p.source.trim(), odds: p.odds.trim(), fairPercent: p.fairPercent.trim() };
}
export type Comparison = { ids: string[]; label: string; legs: number; gross: string; net: string; breakEven: string; estimatedChance: string | null; expectedNet: string | null; multiplier: string };
export function compare(picks: Pick[], stakeText: string, independent: boolean): Comparison[] {
  if (!Array.isArray(picks) || picks.length > 8) throw Error('Compare up to eight selections at once.');
  picks = picks.map(validatePick);
  if (new Set(picks.map(p => p.id)).size !== picks.length) throw Error('Selections must have unique IDs.');
  const stake = decimal(stakeText);
  if (!stake.n || stake.n > stake.d * 10000n) throw Error('Use a stake above zero and at most $10,000.');
  const groups: Pick[][] = picks.map(p => [p]);
  if (independent === true) {
    for (let i=0;i<picks.length;i++) for (let j=i+1;j<picks.length;j++) {
      groups.push([picks[i],picks[j]]);
      for (let k=j+1;k<picks.length;k++) groups.push([picks[i],picks[j],picks[k]]);
    }
  }
  return groups.filter(group => new Set(group.map(p => p.event.trim().toLowerCase().replace(/\s+/g,' '))).size === group.length).map(group => {
    const price = group.reduce((a,p) => mul(a,american(p.odds)), ratio(1n));
    const gross = mul(stake,price);
    const fair = group.every(p => p.fairPercent.trim()) ? group.reduce((a,p) => mul(a,mul(decimal(p.fairPercent),ratio(1n,100n))),ratio(1n)) : null;
    return { ids:group.map(p=>p.id),label:group.map(p=>p.label).join(' + '),legs:group.length,gross:money(gross),net:money(sub(gross,stake)),breakEven:percent(inverse(price)),estimatedChance:fair ? percent(fair) : null,expectedNet:fair ? money(sub(mul(fair,gross),stake)) : null,multiplier:number(price).toFixed(3)+'×' };
  });
}
export function extractOddsCandidates(text: string): { label: string; odds: string }[] {
  if (typeof text !== 'string' || text.length > 100000) throw Error('Screenshot text exceeds the limit.');
  // OCR suggestions are deliberately unconfirmed. Standalone numbers never become picks.
  const found: {label:string;odds:string}[] = [];
  for (const line of text.split(/\r?\n/)) {
    const match = line.match(/^(.{2,160}?)\s+([+-]\d{3,6})(?:\s|$)/);
    if (match) { try { american(match[2]); found.push({label:match[1].trim(),odds:match[2]}); } catch {} }
  }
  return found.slice(0,8);
}
export function importPicks(text: string): Pick[] {
  if (text.length > 1024 * 1024) throw Error('Import exceeds 1 MiB.');
  const data = JSON.parse(text);
  if (data.format !== 'slipsavvy-picks-v1' || !Array.isArray(data.picks) || data.picks.length > 8) throw Error('Use a SlipSavvy picks export with up to eight selections.');
  const picks = data.picks.map(validatePick);
  if (new Set(picks.map((p:Pick) => p.id)).size !== picks.length) throw Error('Duplicate selection IDs.');
  return picks;
}
