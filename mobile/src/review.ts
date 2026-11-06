import { validatePick, type Pick } from './math';

export type Draft = {
  label: string; event: string; odds: string; fairPercent: string;
  source: string; sourceUrl: string;
};
export const blankDraft = (): Draft => ({
  label: '', event: '', odds: '', fairPercent: '', source: '', sourceUrl: '',
});

// Capture time records entry/review, never the time a provider verified the odds.
export function reviewedPick(draft: Draft, id: string, capturedAt: string): Pick {
  return validatePick({
    ...draft, id, capturedAt, source: draft.source.trim() || 'Manual entry (unverified)',
    kind: 'manual', confirmed: true,
  });
}

export function replacePick(picks: Pick[], pick: Pick): Pick[] {
  validatePick(pick);
  const existing = picks.some(p => p.id === pick.id);
  if (!existing && picks.length >= 8) throw Error('Keep up to eight selections at a time.');
  return existing ? picks.map(p => p.id === pick.id ? pick : p) : [...picks, pick];
}
