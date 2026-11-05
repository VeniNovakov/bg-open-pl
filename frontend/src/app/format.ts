import { Lift, Lifter } from './api';

export function kg(value: number | null | undefined): string {
  return value === null || value === undefined ? '-' : String(Number(value.toFixed(2)));
}

export function points(value: number | null | undefined): string {
  return value === null || value === undefined ? '-' : value.toFixed(2);
}

export const LIFTS: { key: 'squat' | 'bench' | 'deadlift'; label: string }[] = [
  { key: 'squat', label: 'Squat' },
  { key: 'bench', label: 'Bench press' },
  { key: 'deadlift', label: 'Deadlift' },
];

export const SEX_LABEL: Record<string, string> = { F: 'Women', M: 'Men' };

export function liftOf(lifter: Lifter, key: 'squat' | 'bench' | 'deadlift'): Lift {
  return lifter[key];
}

export function athleteLink(lifter: Lifter): string[] {
  return ['/athletes', lifter.sex ?? 'U', lifter.name];
}

export function placeText(lifter: Lifter): string {
  if (lifter.status === 'ranked') return lifter.place === null ? '-' : String(lifter.place);
  return lifter.status === 'guest' ? 'guest' : 'no total';
}
