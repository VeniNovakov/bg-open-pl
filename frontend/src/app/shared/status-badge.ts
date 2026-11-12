import { Component, input } from '@angular/core';

import { Status } from '../api';

@Component({
  selector: 'app-status-badge',
  template: `
    @if (status() === 'guest') {
      <span class="badge">guest</span>
    } @else if (status() === 'disqualified') {
      <span class="badge warn" title="no valid total">no total</span>
    }
  `,
})
export class StatusBadgeComponent {
  readonly status = input.required<Status>();
}
