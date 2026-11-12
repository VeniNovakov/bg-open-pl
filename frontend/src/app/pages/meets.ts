import { Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

import { ApiService } from '../api';
import { load } from '../load';

@Component({
  selector: 'app-meets-page',
  imports: [RouterLink],
  template: `
    <h1>Meets</h1>
    <p class="sub">Results of the national championship rounds, as published by the federation.</p>
    @let s = state();
    @switch (s.status) {
      @case ('loading') { <p class="state">Loading meets…</p> }
      @case ('error') { <p class="state error">{{ s.message }}</p> }
      @case ('ready') {
        @if (s.data.length === 0) {
          <p class="state">No meets loaded. Put normalised .xlsx files in the data folder.</p>
        }
        <div class="cards">
          @for (m of s.data; track m.slug) {
            <a class="card" [routerLink]="['/meets', m.slug]">
              <h2>{{ m.title ?? m.slug }}</h2>
              <p class="muted">{{ m.date }}@if (m.city) { · {{ m.city }} }</p>
              <p>
                {{ m.lifters }} lifters
                @if (m.errors) { <span class="badge bad">{{ m.errors }} errors</span> }
                @if (m.warnings) { <span class="badge warn">{{ m.warnings }} warnings</span> }
              </p>
            </a>
          }
        </div>
      }
    }
  `,
})
export class MeetsPage {
  protected readonly state = toSignal(load(inject(ApiService).meets()), {
    initialValue: { status: 'loading' } as const,
  });
}
