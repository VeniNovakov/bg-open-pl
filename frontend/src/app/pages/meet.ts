import { Component, computed, inject, input, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { switchMap } from 'rxjs';

import { ApiService, ClassGroup, Finding } from '../api';
import { athleteLink, kg, placeText, points } from '../format';
import { Loaded, load } from '../load';
import { AttemptsComponent } from '../shared/attempts';
import { StatusBadgeComponent } from '../shared/status-badge';

@Component({
  selector: 'app-meet-page',
  imports: [RouterLink, AttemptsComponent, StatusBadgeComponent],
  template: `
    <p><a routerLink="/">← All meets</a></p>
    @let s = state();
    @switch (s.status) {
      @case ('loading') { <p class="state">Loading meet…</p> }
      @case ('error') { <p class="state error">{{ s.message }}</p> }
      @case ('ready') {
        <h1>{{ s.data.title ?? slug() }}</h1>
        <p class="sub">
          {{ s.data.federation }} · {{ s.data.city }} · {{ s.data.date }} · {{ s.data.lifters }} lifters
        </p>

        <div class="filters">
          <label>Sex
            <select [value]="sex()" (change)="sex.set($any($event.target).value)">
              <option value="">All</option>
              <option value="F">Women</option>
              <option value="M">Men</option>
            </select>
          </label>
          <label>Find a lifter
            <input type="search" placeholder="Name" [value]="query()"
              (input)="query.set($any($event.target).value)" />
          </label>
          <button class="btn" type="button" (click)="toggleNotes()">
            Data notes ({{ s.data.errors + s.data.warnings }})
          </button>
        </div>

        @if (showNotes()) {
          @let n = notes();
          @if (n.status === 'ready') {
            @for (f of n.data; track $index) {
              <div class="note"><strong>{{ f.severity }}</strong> {{ f.code }}
                @if (f.row) { (row {{ f.row }}) } — {{ f.message }}</div>
            } @empty { <p class="muted">No findings.</p> }
          } @else if (n.status === 'loading') { <p class="state">Loading…</p> }
        }

        <div class="jump">
          @for (c of visible(); track c.header; let i = $index) {
            <button type="button" (click)="jump(i)">{{ c.header }}</button>
          }
        </div>

        @for (c of visible(); track c.header; let i = $index) {
          <h2 [id]="'class-' + i">{{ c.header }}</h2>
          <div class="wrap"><table>
            <tr>
              <th>Place</th><th>Name</th><th>Club</th><th class="n">BW</th>
              <th>Squat</th><th>Bench</th><th>Deadlift</th><th class="n">Total</th><th class="n">Points</th>
            </tr>
            @for (l of c.lifters; track $index) {
              <tr>
                <td>{{ place(l) }}</td>
                <td><a [routerLink]="link(l)">{{ l.name }}</a> <app-status-badge [status]="l.status" /></td>
                <td>{{ l.club }}</td>
                <td class="n">{{ kg(l.body_weight_kg) }}</td>
                <td><app-attempts [lift]="l.squat" /></td>
                <td><app-attempts [lift]="l.bench" /></td>
                <td><app-attempts [lift]="l.deadlift" /></td>
                <td class="n"><strong>{{ kg(l.total_kg) }}</strong></td>
                <td class="n">{{ points(l.points) }}</td>
              </tr>
            }
          </table></div>
        } @empty {
          <p class="state">No lifter matches.</p>
        }
      }
    }
  `,
})

export class MeetPage {
  private readonly api = inject(ApiService);
  readonly slug = input.required<string>();

  protected readonly sex = signal('');
  protected readonly query = signal('');
  protected readonly showNotes = signal(false);

  protected readonly state = toSignal(
    toObservable(this.slug).pipe(switchMap((slug) => load(this.api.meet(slug)))),
    { initialValue: { status: 'loading' } as Loaded<never> },
  );

  protected readonly notes = toSignal(
    toObservable(this.slug).pipe(switchMap((slug) => load(this.api.findings(slug)))),
    { initialValue: { status: 'loading' } as Loaded<Finding[]> },
  );

  protected readonly visible = computed<ClassGroup[]>(() => {
    const s = this.state();
    if (s.status !== 'ready') return [];
    const sex = this.sex();
    const q = this.query().trim().toLowerCase();
    return s.data.classes
      .map((c) => ({
        header: c.header,
        lifters: c.lifters.filter(
          (l) => (!sex || l.sex === sex) && (!q || l.name.toLowerCase().includes(q)),
        ),
      }))
      .filter((c) => c.lifters.length > 0);
  });
  

  protected readonly kg = kg;
  protected readonly points = points;
  protected readonly place = placeText;
  protected readonly link = athleteLink;

  protected toggleNotes(): void {
    this.showNotes.update((v) => !v);
  }

  protected jump(index: number): void {
    document.getElementById(`class-${index}`)?.scrollIntoView({ behavior: 'smooth' });
  }
}
