import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    title: 'Meets · BG Open Powerlifting',
    loadComponent: () => import('./pages/meets').then((m) => m.MeetsPage),
  },
  {
    path: 'meets/:slug',
    title: 'Meet · BG Open Powerlifting',
    loadComponent: () => import('./pages/meet').then((m) => m.MeetPage),
  },
  {
    path: 'athletes/:sex/:name',
    title: 'Athlete · BG Open Powerlifting',
    loadComponent: () => import('./pages/athlete').then((m) => m.AthletePage),
  },
  { path: '**', redirectTo: '' },
];
