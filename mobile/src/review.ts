import { validatePick, type Pick } from './math';

export type Draft = {
  label: string; event: string; odds: string; fairPercent: string;
  source: string; sourceUrl: string;
};
export const blankDraft = (): Draft => ({
  label: '', event: '', odds: '', fairPercent: '', source: '', sourceUrl: '',
});

export function pickDraft(pick: Pick): Draft {
  const { label, event, odds, fairPercent, source, sourceUrl } = pick;
  return { label, event, odds, fairPercent, source, sourceUrl };
}

// Capture time records entry/review, never the time a provider verified the odds.
export function reviewedPick(draft: Draft, id: string, capturedAt: string): Pick {
  return validatePick({
    ...draft, id, capturedAt, source: draft.source.trim() || 'Manual entry (unverified)',
    kind: 'manual', confirmed: true, quote: undefined,
  });
}

export function replacePick(picks: Pick[], pick: Pick, replaceId = pick.id): Pick[] {
  validatePick(pick);
  const existing = picks.some(p => p.id === replaceId);
  if (picks.some(p => p.id === pick.id && p.id !== replaceId)) throw Error('Selections must have unique IDs.');
  if (!existing && picks.length >= 8) throw Error('Keep up to eight selections at a time.');
  return existing ? picks.map(p => p.id === replaceId ? pick : p) : [...picks, pick];
}
