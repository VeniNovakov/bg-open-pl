import { Component, computed, input } from '@angular/core';

export interface ChartPoint {
  label: string;
  value: number;
}

/** A small line chart in SVG: labelled y axis, dots with tooltips, dates under the first and last. */
@Component({
  selector: 'app-points-chart',
  template: `
    <svg [attr.viewBox]="'0 0 ' + w + ' ' + h" role="img" [attr.aria-label]="title()">
      @for (t of yTicks(); track t.value) {
        <line [attr.x1]="left" [attr.x2]="w - 8" [attr.y1]="t.y" [attr.y2]="t.y" class="grid" />
        <text [attr.x]="left - 6" [attr.y]="t.y + 4" text-anchor="end" class="axis">{{ t.label }}</text>
      }
      <polyline [attr.points]="line()" class="line" />
      @for (p of dots(); track $index) {
        <circle [attr.cx]="p.x" [attr.cy]="p.y" r="4" class="dot">
          <title>{{ p.label }}: {{ p.text }}</title>
        </circle>
      }
      <text [attr.x]="left" [attr.y]="h - 6" class="axis">{{ points()[0]?.label }}</text>
      <text [attr.x]="w - 8" [attr.y]="h - 6" text-anchor="end" class="axis">{{ lastLabel() }}</text>
    </svg>
  `,
  styles: `
    svg { width: 100%; max-width: 560px; height: auto; display: block; }
    .grid { stroke: var(--line); stroke-width: 1; }
    .axis { fill: var(--muted); font-size: 11px; }
    .line { fill: none; stroke: var(--accent); stroke-width: 2; stroke-linejoin: round; }
    .dot { fill: var(--accent); }
  `,
})
export class PointsChartComponent {
  readonly points = input.required<ChartPoint[]>();
  readonly title = input('Points over time');
  protected readonly w = 560;
  protected readonly h = 190;
  protected readonly left = 40;
  private readonly top = 12;
  private readonly bottom = 26;

  private readonly range = computed(() => {
    const values = this.points().map((p) => p.value);
    const low = Math.min(...values);
    const high = Math.max(...values);
    const pad = (high - low || 4) * 0.15;
    return { min: Math.floor(low - pad), max: Math.ceil(high + pad) };
  });

  private y(value: number): number {
    const { min, max } = this.range();
    return this.top + (1 - (value - min) / (max - min)) * (this.h - this.top - this.bottom);
  }

  private x(index: number): number {
    const n = this.points().length;
    return n < 2 ? this.w / 2 : this.left + (index * (this.w - this.left - 14)) / (n - 1);
  }

  protected readonly dots = computed(() =>
    this.points().map((p, i) => ({
      x: this.x(i), y: this.y(p.value), label: p.label, text: p.value.toFixed(2),
    })),
  );
  protected readonly line = computed(() => this.dots().map((d) => `${d.x},${d.y}`).join(' '));
  protected readonly lastLabel = computed(() => this.points().at(-1)?.label ?? '');
  protected readonly yTicks = computed(() => {
    const { min, max } = this.range();
    return [min, (min + max) / 2, max].map((value) => ({
      value, y: this.y(value), label: String(Math.round(value)),
    }));
  });
}
