import { kg, placeText, points } from './format';
import { lifter } from './testing';

describe('format', () => {
  it('trims weights and marks missing ones', () => {
    expect(kg(100)).toBe('100');
    expect(kg(102.5)).toBe('102.5');
    expect(kg(null)).toBe('-');
  });

  it('shows points with two decimals', () => {
    expect(points(80)).toBe('80.00');
    expect(points(null)).toBe('-');
  });

  it('describes the place by status', () => {
    expect(placeText(lifter({ place: 3 }))).toBe('3');
    expect(placeText(lifter({ status: 'guest', place: null }))).toBe('guest');
    expect(placeText(lifter({ status: 'disqualified', place: null }))).toBe('no total');
  });
});
