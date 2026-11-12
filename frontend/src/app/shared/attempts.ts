import { Component, input } from '@angular/core';

import { Lift } from '../api';
import { kg } from '../format';

@Component({
  selector: 'app-attempts',
  template: `
    @for (a of lift().attempts; track $index) {
      @if (a.weight_kg === null) {
        <span class="none" aria-label="not taken">-</span>
      } @else {
        <span class="chip" [class.ok]="a.result !== 'fail'" [class.x]="a.result === 'fail'"
          [attr.title]="a.result === 'fail' ? 'failed' : 'good lift'">{{ fmt(a.weight_kg) }}</span>
      }
    }
  `,
  styles: `
    :host { display: inline-flex; gap: 4px; align-items: center; }
    .chip { padding: 0 6px; font-size: .88rem; border-radius: 10px; border: 1px solid var(--line); }
    .ok { color: var(--ok); border-color: var(--ok); background: color-mix(in srgb, var(--ok) 12%, transparent); }
    .x { color: var(--bad); border-color: var(--bad); text-decoration: line-through;
         background: color-mix(in srgb, var(--bad) 10%, transparent); }
    .none { color: var(--muted); padding: 0 6px; }
  `,
})
export class AttemptsComponent {
  readonly lift = input.required<Lift>();
  protected readonly fmt = kg;
}
