import { Injectable, signal } from '@angular/core';

export type ThemeName = 'light' | 'dark';

const KEY = 'skillsgap.theme'; // also read by the inline script in index.html

function hasSavedChoice(): boolean {
  try {
    return localStorage.getItem(KEY) !== null;
  } catch {
    return false;
  }
}

@Injectable({ providedIn: 'root' })
export class Theme {
  /** index.html has already applied the saved or OS theme, so the page never flashes the wrong one. */
  current = signal<ThemeName>(document.documentElement.dataset['theme'] === 'dark' ? 'dark' : 'light');

  constructor() {
    // Until the user picks a theme, keep following the OS setting.
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      if (!hasSavedChoice()) this.apply(e.matches ? 'dark' : 'light');
    });
  }

  toggle() {
    const next: ThemeName = this.current() === 'dark' ? 'light' : 'dark';
    this.apply(next);
    try { localStorage.setItem(KEY, next); } catch { /* storage blocked: the choice lasts for this page only */ }
  }

  private apply(theme: ThemeName) {
    this.current.set(theme);
    document.documentElement.dataset['theme'] = theme;
  }
}
