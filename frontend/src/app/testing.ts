import { Lifter, MeetSummary } from './api';

const lift = (weights: [number, 'good' | 'fail'][] , best: number | null) => ({
  attempts: weights.map(([w, r]) => ({ weight_kg: w, result: r })),
  best_kg: best,
});

export function lifter(over: Partial<Lifter> = {}): Lifter {
  return {
    name: 'Тест Лифтър', sex: 'M', club: 'Клуб', division: 'Open', weight_class: '83',
    equipment: 'classic', status: 'ranked', place: 1, body_weight_kg: 80,
    squat: lift([[200, 'good'], [210, 'good'], [220, 'fail']], 210),
    bench: lift([[130, 'good'], [140, 'fail'], [140, 'fail']], 130),
    deadlift: lift([[240, 'good'], [250, 'good'], [260, 'good']], 260),
    total_kg: 600, points: 80, points_kind: 'IPF GL', meet: '2026-01-01', ...over,
  };
}

export function meet(slug: string, over: Partial<MeetSummary> = {}): MeetSummary {
  return { slug, title: `Meet ${slug}`, federation: 'БФСТ', city: 'София', date: slug,
           lifters: 10, errors: 0, warnings: 0, ...over };
}
