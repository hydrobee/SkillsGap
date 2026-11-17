import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { tap } from 'rxjs';
import { Api } from './api';
import { Role, Session } from './models';

const KEY = 'skillsgap.session';

function load(): Session | null {
  try {
    const raw = sessionStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

@Injectable({ providedIn: 'root' })
export class Auth {
  private api = inject(Api);
  private router = inject(Router);

  user = signal<Session | null>(load());
  role = computed<Role | null>(() => this.user()?.role ?? null);

  login(email: string, password: string) {
    return this.api.login(email, password).pipe(
      tap((r) => {
        const s: Session = { token: r.access_token, role: r.role, name: r.name, user_id: r.user_id };
        this.user.set(s);
        try { sessionStorage.setItem(KEY, JSON.stringify(s)); } catch { /* storage blocked: stay logged in for this page only */ }
      }),
    );
  }

  logout() {
    this.user.set(null);
    try { sessionStorage.removeItem(KEY); } catch { /* ignore */ }
    this.router.navigateByUrl('/login');
  }

  /** Where each role lands after login. */
  homePath(): string {
    switch (this.role()) {
      case 'hr': return '/dashboard';
      case 'supervisor': return '/rating';
      case 'staff': return '/survey';
      default: return '/login';
    }
  }
}
