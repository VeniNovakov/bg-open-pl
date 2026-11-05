import { KeyValuePipe } from '@angular/common';
import { Component, computed, inject, input } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { combineLatest, map, switchMap } from 'rxjs';

import { ApiService, Lifter, MeetSummary } from '../api';
import { buildResults, personalBests, pointsHistory } from '../athlete-stats';
import { SEX_LABEL, kg, placeText, points } from '../format';
import { Loaded, load } from '../load';
import { AttemptsComponent } from '../shared/attempts';
import { PointsChartComponent } from '../shared/points-chart';
import { StatusBadgeComponent } from '../shared/status-badge';

@Component({
  selector: 'app-athlete-page',
  imports: [RouterLink, KeyValuePipe, AttemptsComponent, PointsChartComponent, StatusBadgeComponent],
  template: `
    <p><a routerLink="/">← All meets</a></p>
    @let s = state();
    @switch (s.status) {
      @case ('loading') { <p class="state">Loading…</p> }
      @case ('error') { <p class="state error">{{ s.message }}</p> }
      @case ('ready') {
        <h1>{{ name() }}</h1>
        <p class="sub">{{ sexLabel() }}@if (clubs().length) { · {{ clubs().join(', ') }} }
          · {{ results().length }} meet{{ results().length === 1 ? '' : 's' }}</p>

        @for (e of bests() | keyvalue; track e.key) {
          @if (e.value.length) {
            <h2>Personal bests <span class="sub">· {{ e.key }}</span></h2>
            <div class="tiles">
              @for (b of e.value; track b.label) {
                <div class="tile">
                  <div class="k">{{ b.label }}</div>
                  <div class="v">{{ b.isPoints ? points(b.value) : kg(b.value) + ' kg' }}</div>
                  <div class="s"><a [routerLink]="['/meets', b.meet]">{{ b.meet }}</a></div>
                </div>
              }
            </div>
          }
        }

        @if (history().length >= 2) {
          <h2>Progress <span class="sub">· IPF GL points</span></h2>
          <app-points-chart [points]="history()" />
        }

        <h2>Results</h2>
        @for (r of results(); track r.lifter.meet + r.lifter.equipment) {
          <section class="card" style="margin-bottom: 16px">
            <h3>
              <a [routerLink]="['/meets', r.lifter.meet]">{{ r.meet?.title ?? r.lifter.meet }}</a>
              <span class="sub">· {{ r.meet?.date }}</span>
              <app-status-badge [status]="r.lifter.status" />
            </h3>
            <div class="tiles">
              <div class="tile"><div class="k">Place</div><div class="v">{{ place(r.lifter) }}</div></div>
              <div class="tile"><div class="k">Class</div>
                <div class="v">{{ r.lifter.weight_class ? r.lifter.weight_class + ' kg' : '–' }}</div>
                <div class="s">{{ r.lifter.division }} · {{ r.lifter.equipment }}</div></div>
              <div class="tile"><div class="k">Bodyweight</div><div class="v">{{ kg(r.lifter.body_weight_kg) }}</div><div class="s">kg</div></div>
              <div class="tile"><div class="k">Total</div><div class="v">{{ kg(r.lifter.total_kg) }}</div><div class="s">kg</div></div>
              <div class="tile"><div class="k">Points</div><div class="v">{{ points(r.lifter.points) }}</div>
                <div class="s">{{ r.lifter.points !== null ? r.lifter.points_kind : '' }}</div></div>
            </div>
            <div class="wrap"><table>
              <tr><th>Lift</th><th>Attempts</th><th class="n">Best</th><th>Share of total</th></tr>
              @for (l of lifts; track l.key; let i = $index) {
                <tr>
                  <td>{{ l.label }}</td>
                  <td><app-attempts [lift]="r.lifter[l.key]" /></td>
                  <td class="n">{{ kg(r.shares[i].best) }}</td>
                  <td><span class="bar-track" [attr.title]="r.shares[i].percent + '%'"><i [style.width.%]="r.shares[i].percent"></i></span></td>
                </tr>
              }
            </table></div>
            <p class="muted">{{ r.good }} of {{ r.made }} attempts good</p>
          </section>
        }
      }
    }
  `,
})
export class AthletePage {
  private readonly api = inject(ApiService);
  /** Bound from the route parameters :sex and :name. */
  readonly sex = input.required<string>();
  readonly name = input.required<string>();

  protected readonly lifts = [
    { key: 'squat', label: 'Squat' },
    { key: 'bench', label: 'Bench press' },
    { key: 'deadlift', label: 'Deadlift' },
  ] as const;

  protected readonly state = toSignal(
    combineLatest([toObservable(this.sex), toObservable(this.name)]).pipe(
      switchMap(([sex, name]) =>
        load(
          combineLatest([this.api.athlete(sex, name), this.api.meets()]).pipe(
            map(([lifters, meets]) => ({ lifters, meets })),
          ),
        ),
      ),
    ),
    { initialValue: { status: 'loading' } as Loaded<{ lifters: Lifter[]; meets: MeetSummary[] }> },
  );

  private readonly data = computed(() => {
    const s = this.state();
    return s.status === 'ready' ? s.data : { lifters: [], meets: [] };
  });
  protected readonly results = computed(() => buildResults(this.data().lifters, this.data().meets));
  protected readonly bests = computed(() => personalBests(this.data().lifters));
  protected readonly history = computed(() => pointsHistory(this.data().lifters, this.data().meets));
  protected readonly clubs = computed(() => [
    ...new Set(this.data().lifters.map((l) => l.club).filter(Boolean)),
  ]);
  protected readonly sexLabel = computed(() => SEX_LABEL[this.sex()] ?? '');

  protected readonly kg = kg;
  protected readonly points = points;
  protected readonly place = placeText;
}
