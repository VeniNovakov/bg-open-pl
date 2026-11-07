import { Component, computed, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { switchMap } from 'rxjs';

import { ApiService, RankingRow } from '../api';
import { athleteLink, kg, points } from '../format';
import { Loaded, load } from '../load';

type SortKey = 'rank' | 'name' | 'club' | 'class' | 'bw' | 'total' | 'points' | 'meet';

const SORT_VALUE: Record<SortKey, (r: RankingRow) => string | number> = {
  rank: (r) => r.rank,
  name: (r) => r.lifter.name,
  club: (r) => r.lifter.club,
  class: (r) => parseFloat(r.lifter.weight_class ?? '0') + (r.lifter.weight_class?.endsWith('+') ? 1000 : 0),
  bw: (r) => r.lifter.body_weight_kg ?? 0,
  total: (r) => r.lifter.total_kg ?? 0,
  points: (r) => r.lifter.points ?? 0,
  meet: (r) => r.lifter.meet,
};

@Component({
  selector: 'app-rankings-page',
  imports: [RouterLink],
  template: `
    <h1>Rankings</h1>
    <p class="sub">Best IPF GL result of each ranked lifter. Click a column to sort.</p>
    <div class="filters">
      <label>Sex
        <select [value]="sex()" (change)="sex.set($any($event.target).value)">
          <option value="M">Men</option>
          <option value="F">Women</option>
          <option value="">Both</option>
        </select>
      </label>
      <label>Equipment
        <select [value]="equipment()" (change)="equipment.set($any($event.target).value)">
          <option value="classic">Classic</option>
          <option value="equipped">Equipped</option>
        </select>
      </label>
      <label>Division
        <select [value]="division()" (change)="division.set($any($event.target).value)">
          <option value="">All</option>
          @for (d of divisions; track d) { <option [value]="d">{{ d }}</option> }
        </select>
      </label>
      <label>Show
        <select [value]="limit()" (change)="limit.set(+$any($event.target).value)">
          @for (n of [25, 50, 100, 250]; track n) { <option [value]="n">{{ n }}</option> }
        </select>
      </label>
    </div>
    @let s = state();
    @switch (s.status) {
      @case ('loading') { <p class="state">Loading…</p> }
      @case ('error') { <p class="state error">{{ s.message }}</p> }
      @case ('ready') {
        <div class="wrap"><table>
          <tr>
            @for (c of columns; track c.key) {
              <th [class.n]="c.numeric" [attr.aria-sort]="ariaSort(c.key)">
                <button type="button" (click)="sortBy(c.key)">{{ c.label }}{{ arrow(c.key) }}</button>
              </th>
            }
          </tr>
          @for (r of rows(); track r.lifter.name + r.lifter.meet) {
            <tr>
              <td>{{ r.rank }}</td>
              <td><a [routerLink]="link(r.lifter)">{{ r.lifter.name }}</a></td>
              <td>{{ r.lifter.club }}</td>
              <td>{{ r.lifter.weight_class }}</td>
              <td class="n">{{ kg(r.lifter.body_weight_kg) }}</td>
              <td class="n">{{ kg(r.lifter.total_kg) }}</td>
              <td class="n"><strong>{{ points(r.lifter.points) }}</strong></td>
              <td><a [routerLink]="['/meets', r.lifter.meet]">{{ r.lifter.meet }}</a></td>
            </tr>
          } @empty {
            <tr><td colspan="8" class="state">No results for this selection.</td></tr>
          }
        </table></div>
      }
    }
  `,
})
export class RankingsPage {
  private readonly api = inject(ApiService);
  protected readonly divisions = ['Open', 'SJR', 'JR', 'M1', 'M2', 'M3', 'M4'];
  protected readonly columns: { key: SortKey; label: string; numeric: boolean }[] = [
    { key: 'rank', label: '#', numeric: false },
    { key: 'name', label: 'Name', numeric: false },
    { key: 'club', label: 'Club', numeric: false },
    { key: 'class', label: 'Class', numeric: false },
    { key: 'bw', label: 'BW', numeric: true },
    { key: 'total', label: 'Total', numeric: true },
    { key: 'points', label: 'IPF GL', numeric: true },
    { key: 'meet', label: 'Meet', numeric: false },
  ];

  protected readonly sex = signal<'F' | 'M' | ''>('M');
  protected readonly equipment = signal('classic');
  protected readonly division = signal('');
  protected readonly limit = signal(50);
  protected readonly sort = signal<{ key: SortKey; dir: 1 | -1 }>({ key: 'rank', dir: 1 });

  private readonly query = computed(() => ({
    sex: this.sex(), equipment: this.equipment(), division: this.division(), limit: this.limit(),
  }));

  protected readonly state = toSignal(
    toObservable(this.query).pipe(switchMap((q) => load(this.api.rankings(q)))),
    { initialValue: { status: 'loading' } as Loaded<RankingRow[]> },
  );

  protected readonly rows = computed(() => {
    const s = this.state();
    if (s.status !== 'ready') return [];
    const { key, dir } = this.sort();
    const value = SORT_VALUE[key];
    return [...s.data].sort((a, b) => {
      const x = value(a), y = value(b);
      return (typeof x === 'string' ? x.localeCompare(y as string) : x - (y as number)) * dir;
    });
  });

  protected readonly kg = kg;
  protected readonly points = points;
  protected readonly link = athleteLink;

  protected sortBy(key: SortKey): void {
    this.sort.update((s) =>
      s.key === key
        ? { key, dir: s.dir === 1 ? -1 : 1 }
        : { key, dir: key === 'name' || key === 'club' || key === 'rank' ? 1 : -1 },
    );
  }

  protected arrow(key: SortKey): string {
    const s = this.sort();
    return s.key === key ? (s.dir === 1 ? ' ▲' : ' ▼') : '';
  }

  protected ariaSort(key: SortKey): 'ascending' | 'descending' | 'none' {
    const s = this.sort();
    return s.key !== key ? 'none' : s.dir === 1 ? 'ascending' : 'descending';
  }
}
