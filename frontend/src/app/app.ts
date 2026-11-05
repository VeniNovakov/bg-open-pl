import { Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { catchError, of } from 'rxjs';

import { ApiService } from './api';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <header>
      <div class="bar">
        <a class="brand" routerLink="/">BG Open Powerlifting</a>
        <nav>
          <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }"
            >Meets</a
          >
        </nav>
      </div>
    </header>
    <main><router-outlet /></main>
    <footer>
      <div class="bar">
        Results from the Bulgarian Powerlifting Federation (БФСТ) protocols, shown as published.
        Request removal of your data: {{ info()?.contact ?? '(contact address not set)' }}.
      </div>
    </footer>
  `,
})
export class App {
  private readonly api = inject(ApiService);
  protected readonly info = toSignal(this.api.info().pipe(catchError(() => of(null))));
}
