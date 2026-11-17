import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Auth } from '../core/auth';
import { errMsg } from '../core/util';

@Component({
  selector: 'app-login',
  imports: [FormsModule],
  template: `
    <div class="auth-wrap">
      <section class="card auth-card">
        <span class="brand">
          <span class="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>
          </span>
          SkillsGap
        </span>
        <h1>Welcome back</h1>
        <p class="lead">Sign in to the competency gap assessment for staff, supervisors and HR.</p>
        <form (ngSubmit)="submit()">
          <label for="email">Email</label>
          <input id="email" class="wide" name="email" type="email" autocomplete="username"
                 placeholder="you@company.com" [(ngModel)]="email" required />
          <label for="password">Password</label>
          <input id="password" class="wide" name="password" type="password" autocomplete="current-password"
                 placeholder="••••••••" [(ngModel)]="password" required />
          <button class="btn primary lg block" type="submit" [disabled]="busy()">
            {{ busy() ? 'Signing in…' : 'Sign in' }}
          </button>
          @if (error()) { <p class="alert error note" role="alert">{{ error() }}</p> }
        </form>
        <div class="divider">Demo accounts</div>
        <div class="demo-grid">
          <button class="btn" type="button" (click)="fill('hr@demo.com')">HR</button>
          <button class="btn" type="button" (click)="fill('aiman@demo.com')">Supervisor</button>
          <button class="btn" type="button" (click)="fill('bella@demo.com')">Staff</button>
        </div>
        <p class="muted small demo-hint">Password for all: <code>password123</code></p>
      </section>
    </div>
  `,
})
export class LoginPage {
  private auth = inject(Auth);
  private router = inject(Router);
  email = signal('');
  password = signal('');
  busy = signal(false);
  error = signal('');

  fill(email: string) {
    this.email.set(email);
    this.password.set('password123');
  }

  submit() {
    this.busy.set(true);
    this.error.set('');
    this.auth.login(this.email(), this.password()).subscribe({
      next: () => this.router.navigateByUrl(this.auth.homePath()),
      error: (e) => { this.error.set(errMsg(e)); this.busy.set(false); },
    });
  }
}
