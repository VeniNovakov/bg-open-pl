import { TestBed } from '@angular/core/testing';

import { lifter } from '../testing';
import { AttemptsComponent } from './attempts';

describe('AttemptsComponent', () => {
  it('marks good lifts green and failed ones struck through', () => {
    const fixture = TestBed.createComponent(AttemptsComponent);
    fixture.componentRef.setInput('lift', lifter().squat);
    fixture.detectChanges();
    const chips = Array.from<HTMLElement>(fixture.nativeElement.querySelectorAll('.chip'));
    expect(chips.map((c) => c.textContent?.trim())).toEqual(['200', '210', '220']);
    expect(chips.map((c) => c.classList.contains('x'))).toEqual([false, false, true]);
  });

  it('shows a dash for an attempt that was not taken', () => {
    const fixture = TestBed.createComponent(AttemptsComponent);
    fixture.componentRef.setInput('lift', {
      attempts: [{ weight_kg: 100, result: 'good' }, { weight_kg: null, result: null }],
      best_kg: 100,
    });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.none')?.textContent).toContain('-');
  });
});
