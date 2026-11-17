import { inject } from '@angular/core';
import { Routes } from '@angular/router';

import { Auth } from './core/auth';
import { roleGuard } from './core/guards';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: () => inject(Auth).homePath() },
  { path: 'login', loadComponent: () => import('./pages/login').then((m) => m.LoginPage) },
  {
    path: 'survey', canActivate: [roleGuard('staff', 'supervisor')],
    loadComponent: () => import('./pages/survey').then((m) => m.SurveyPage),
  },
  {
    path: 'rating', canActivate: [roleGuard('supervisor')],
    loadComponent: () => import('./pages/rating').then((m) => m.RatingPage),
  },
  {
    path: 'reports/individual', canActivate: [roleGuard('staff', 'supervisor', 'hr')],
    loadComponent: () => import('./pages/individual-report').then((m) => m.IndividualReportPage),
  },
  {
    path: 'reports/department', canActivate: [roleGuard('supervisor', 'hr')],
    loadComponent: () => import('./pages/department-report').then((m) => m.DepartmentReportPage),
  },
  {
    path: 'setup', canActivate: [roleGuard('hr')],
    loadComponent: () => import('./pages/setup').then((m) => m.SetupPage),
  },
  { path: '**', redirectTo: '' },
];
