import { HttpErrorResponse } from '@angular/common/http';
import { Observable, catchError, map, of, startWith } from 'rxjs';

export type Loaded<T> =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: T };

export function messageOf(err: unknown): string {
  if (err instanceof HttpErrorResponse) {
    if (err.status === 404) return 'Not found.';
    if (err.status === 0) return 'The API cannot be reached.';
    return `The API answered with an error (${err.status}).`;
  }
  return 'Something went wrong.';
}

export function load<T>(source: Observable<T>): Observable<Loaded<T>> {
  return source.pipe(
    map((data): Loaded<T> => ({ status: 'ready', data })),
    startWith({ status: 'loading' } as Loaded<T>),
    catchError((err) => of({ status: 'error', message: messageOf(err) } as Loaded<T>)),
  );
}
