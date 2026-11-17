import { Component, Injectable, inject, input, signal } from '@angular/core';

export type Theme = 'light' | 'dark';
const KEY = 'skillsgap.theme';

function saved(): Theme | null {
  try {
    const v = localStorage.getItem(KEY);
    return v === 'light' || v === 'dark' ? v : null;
  } catch {
    return null;
  }
}

function systemTheme(): Theme {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/** Light / dark mode. Follows the OS until the user picks one; the pick is remembered. */
@Injectable({ providedIn: 'root' })
export class ThemeService {
  theme = signal<Theme>(saved() ?? systemTheme());

  constructor() {
    if (saved()) document.documentElement.dataset['theme'] = this.theme();
    // keep following the OS while the user hasn't chosen
    window.matchMedia?.('(prefers-color-scheme: dark)').addEventListener?.('change', () => {
      if (!saved()) this.theme.set(systemTheme());
    });
  }

  toggle() {
    const next: Theme = this.theme() === 'dark' ? 'light' : 'dark';
    const root = document.documentElement;
    root.classList.add('theme-anim');
    this.theme.set(next);
    root.dataset['theme'] = next;
    try { localStorage.setItem(KEY, next); } catch { /* storage blocked: applies to this page only */ }
    setTimeout(() => root.classList.remove('theme-anim'), 300);
  }
}

@Component({
  selector: 'app-theme-toggle',
  host: { style: 'display: contents' },
  template: `
    <button type="button" class="theme-toggle" [class.floating]="floating()" (click)="t.toggle()"
            [attr.aria-label]="t.theme() === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
            [title]="t.theme() === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'">
      @if (t.theme() === 'dark') {
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>
      } @else {
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
      }
    </button>
  `,
})
export class ThemeToggle {
  t = inject(ThemeService);
  floating = input(false);
}
