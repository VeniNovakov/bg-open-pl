import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface Attempt {
  weight_kg: number | null;
  result: 'good' | 'fail' | null;
}

export interface Lift {
  attempts: Attempt[];
  best_kg: number | null;
}

export type Status = 'ranked' | 'guest' | 'disqualified';

export interface Lifter {
  name: string;
  sex: 'F' | 'M' | null;
  club: string;
  division: string;
  weight_class: string | null;
  equipment: string;
  status: Status;
  place: number | null;
  body_weight_kg: number | null;
  squat: Lift;
  bench: Lift;
  deadlift: Lift;
  total_kg: number | null;
  points: number | null;
  points_kind: string;
  meet: string;
}

export interface MeetSummary {
  slug: string;
  title: string | null;
  federation: string | null;
  city: string | null;
  date: string | null;
  lifters: number;
  errors: number;
  warnings: number;
}

export interface ClassGroup {
  header: string;
  lifters: Lifter[];
}

export interface Meet extends MeetSummary {
  classes: ClassGroup[];
}

export interface Finding {
  code: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
  row: number | null;
}

export interface RankingRow {
  rank: number;
  lifter: Lifter;
}

export interface Info {
  contact: string;
  meets: number;
  unreadable_files: number;
}

export interface RankingQuery {
  sex?: 'F' | 'M' | '';
  equipment?: string;
  division?: string;
  limit?: number;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  info(): Observable<Info> {
    return this.http.get<Info>('/api/info');
  }

  meets(): Observable<MeetSummary[]> {
    return this.http.get<MeetSummary[]>('/api/meets');
  }

  meet(slug: string): Observable<Meet> {
    return this.http.get<Meet>(`/api/meets/${encodeURIComponent(slug)}`);
  }

  findings(slug: string): Observable<Finding[]> {
    return this.http.get<Finding[]>(`/api/meets/${encodeURIComponent(slug)}/findings`);
  }

  rankings(query: RankingQuery): Observable<RankingRow[]> {
    let params = new HttpParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== '') params = params.set(key, String(value));
    }
    return this.http.get<RankingRow[]>('/api/rankings', { params });
  }

  athlete(sex: string, name: string): Observable<Lifter[]> {
    return this.http.get<Lifter[]>(
      `/api/athletes/${encodeURIComponent(sex)}/${encodeURIComponent(name)}`,
    );
  }
}
