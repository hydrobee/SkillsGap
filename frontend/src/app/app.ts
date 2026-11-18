import { Component, ElementRef, inject, signal, viewChild } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ThemeToggle } from './components/theme-toggle';
import { Auth } from './core/auth';
import { initials } from './core/util';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, ThemeToggle],
  host: { '(document:keydown.escape)': 'onEscape()' },
  template: `
    @if (auth.user(); as u) {
      <header class="topbar no-print">
        <div class="topbar-inner">
          <a class="brand" routerLink="/" (click)="menuOpen.set(false)">
            <span class="brand-mark" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>
            </span>
            SkillsGap
          </a>
          <!-- Inline on large screens; on small screens this is the panel the burger button opens. -->
          <div class="topbar-menu" id="main-menu" [class.open]="menuOpen()">
            <nav class="nav" aria-label="Main" (click)="onNavClick($event)">
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
              <button class="btn ghost sm" type="button" (click)="logout()" title="Log out">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>
                Log out
              </button>
            </div>
          </div>
          <div class="bar-actions">
            <app-theme-toggle />
            <button #menuButton class="menu-toggle" type="button" aria-controls="main-menu"
                    [attr.aria-expanded]="menuOpen()" [attr.aria-label]="menuOpen() ? 'Close menu' : 'Open menu'"
                    [title]="menuOpen() ? 'Close menu' : 'Open menu'" (click)="menuOpen.set(!menuOpen())">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                   stroke-linejoin="round" aria-hidden="true">
                @if (menuOpen()) { <path d="M6 6l12 12M18 6L6 18"/> } @else { <path d="M4 7h16M4 12h16M4 17h16"/> }
              </svg>
            </button>
          </div>
        </div>
      </header>
      @if (menuOpen()) { <div class="menu-scrim no-print" aria-hidden="true" (click)="menuOpen.set(false)"></div> }
    }
    <main><router-outlet /></main>
  `,
})
export class App {
  auth = inject(Auth);
  initials = initials;
  menuOpen = signal(false);
  private menuButton = viewChild<ElementRef<HTMLButtonElement>>('menuButton');

  constructor() {
    // Rotating or resizing up to the full nav must not leave the panel open for later.
    matchMedia('(max-width: 860px)').addEventListener('change', () => this.menuOpen.set(false));
  }

  onNavClick(e: Event) {
    if ((e.target as HTMLElement).closest('a')) this.menuOpen.set(false);
  }

  onEscape() {
    if (!this.menuOpen()) return;
    this.menuOpen.set(false);
    this.menuButton()?.nativeElement.focus();
  }

  logout() {
    this.menuOpen.set(false);
    this.auth.logout();
  }
}
