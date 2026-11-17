import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { Auth } from './core/auth';
import { initials } from './core/util';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    @if (auth.user(); as u) {
      <header class="topbar no-print">
        <div class="topbar-inner">
          <a class="brand" routerLink="/">
            <span class="brand-mark" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>
            </span>
            SkillsGap
          </a>
          <nav class="nav" aria-label="Main">
            @if (u.role === 'hr') { <a routerLink="/dashboard" routerLinkActive="active">Dashboard</a> }
            @if (u.role !== 'hr') { <a routerLink="/survey" routerLinkActive="active">My survey</a> }
            @if (u.role === 'supervisor') { <a routerLink="/rating" routerLinkActive="active">Rate my team</a> }
            <a routerLink="/reports/individual" routerLinkActive="active">Individual report</a>
            @if (u.role !== 'staff') {
              <a routerLink="/reports/department" routerLinkActive="active">Department report</a>
            }
            @if (u.role === 'hr') { <a routerLink="/setup" routerLinkActive="active">HR setup</a> }
          </nav>
          <div class="who">
            <span class="avatar" aria-hidden="true">{{ initials(u.name) }}</span>
            <span class="who-text">
              <span class="who-name">{{ u.name }}</span>
              <span class="who-role">{{ u.role === 'hr' ? 'HR' : u.role }}</span>
            </span>
            <button class="btn ghost sm" type="button" (click)="auth.logout()" title="Log out">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>
              Log out
            </button>
          </div>
        </div>
      </header>
    }
    <main><router-outlet /></main>
  `,
})
export class App {
  auth = inject(Auth);
  initials = initials;
}
