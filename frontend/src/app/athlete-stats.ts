import { Lifter, MeetSummary } from './api';

export interface PersonalBest {
  label: string;
  value: number;
  meet: string;
  isPoints: boolean;
}

export interface Result {
  lifter: Lifter;
  meet: MeetSummary | undefined;
  good: number;
  made: number;
  shares: { label: string; best: number | null; percent: number }[];
}

const LIFTS = [
  { key: 'squat', label: 'Squat' },
  { key: 'bench', label: 'Bench press' },
  { key: 'deadlift', label: 'Deadlift' },
] as const;

/** One card per meet, newest first (the API order): attempt counts and share of the total. */
export function buildResults(lifters: Lifter[], meets: MeetSummary[]): Result[] {
  const bySlug = new Map(meets.map((m) => [m.slug, m]));
  return lifters.map((lifter) => {
    const attempts = LIFTS.flatMap((l) => lifter[l.key].attempts).filter((a) => a.weight_kg !== null);
    const total = LIFTS.reduce((sum, l) => sum + (lifter[l.key].best_kg ?? 0), 0);
    return {
      lifter,
      meet: bySlug.get(lifter.meet),
      made: attempts.length,
      good: attempts.filter((a) => a.result !== 'fail').length,
      shares: LIFTS.map((l) => {
        const best = lifter[l.key].best_kg;
        return { label: l.label, best, percent: best && total ? Math.round((best / total) * 100) : 0 };
      }),
    };
  });
}

/** Best lifts per equipment. Total and points count only ranked results. */
export function personalBests(lifters: Lifter[]): Map<string, PersonalBest[]> {
  const out = new Map<string, PersonalBest[]>();
  for (const equipment of [...new Set(lifters.map((l) => l.equipment))].sort()) {
    const mine = lifters.filter((l) => l.equipment === equipment);
    const ranked = mine.filter((l) => l.status === 'ranked');
    const bests: PersonalBest[] = [];
    const top = (items: Lifter[], pick: (l: Lifter) => number | null) => {
      let best: { value: number; lifter: Lifter } | null = null;
      for (const l of items) {
        const v = pick(l);
        if (v !== null && (best === null || v > best.value)) best = { value: v, lifter: l };
      }
      return best;
    };
    for (const l of LIFTS) {
      const b = top(mine, (x) => x[l.key].best_kg);
      if (b) bests.push({ label: l.label, value: b.value, meet: b.lifter.meet, isPoints: false });
    }
    const total = top(ranked, (x) => x.total_kg);
    if (total) bests.push({ label: 'Total', value: total.value, meet: total.lifter.meet, isPoints: false });
    const pts = top(ranked, (x) => x.points);
    if (pts) bests.push({ label: 'IPF GL points', value: pts.value, meet: pts.lifter.meet, isPoints: true });
    out.set(equipment, bests);
  }
  return out;
}

/** Ranked results with points, oldest first; the chart needs at least two. */
export function pointsHistory(lifters: Lifter[], meets: MeetSummary[]): { label: string; value: number }[] {
  const bySlug = new Map(meets.map((m) => [m.slug, m]));
  return lifters
    .filter((l) => l.status === 'ranked' && l.points !== null)
    .map((l) => ({ label: bySlug.get(l.meet)?.date ?? l.meet, value: l.points as number, slug: l.meet }))
    .sort((a, b) => a.slug.localeCompare(b.slug))
    .map(({ label, value }) => ({ label, value }));
}
