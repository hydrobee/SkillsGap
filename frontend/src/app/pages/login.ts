import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ThemeToggle } from '../components/theme-toggle';
import { Auth } from '../core/auth';
import { errMsg } from '../core/util';

@Component({
  selector: 'app-login',
  imports: [FormsModule, ThemeToggle],
  template: `
    <div class="auth-wrap">
      <section class="card auth-card">
        <div class="auth-top">
          <span class="brand">
            <span class="brand-mark" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>
            </span>
            SkillsGap
          </span>
          <app-theme-toggle />
        </div>
        <h1>Welcome back</h1>
        <p class="lead">Sign in to the competency gap assessment for staff, supervisors and HR.</p>
        <form (ngSubmit)="submit()">
          <label for="email">Email</label>
          <input id="email" class="wide" name="email" type="email" autocomplete="username"
                 placeholder="you@company.com" [(ngModel)]="email" required />
          <label for="password">Password</label>
          <div class="password-field">
            <input id="password" class="wide" name="password" [type]="showPassword() ? 'text' : 'password'"
                   autocomplete="current-password" placeholder="••••••••" [(ngModel)]="password" required />
            <button class="password-toggle" type="button" (click)="showPassword.set(!showPassword())"
                    [attr.aria-label]="showPassword() ? 'Hide password' : 'Show password'"
                    [title]="showPassword() ? 'Hide password' : 'Show password'">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                   stroke-linejoin="round" aria-hidden="true">
                @if (showPassword()) {
                  <path d="M10.6 5.1A10.4 10.4 0 0 1 12 5c6.5 0 10 7 10 7a17.6 17.6 0 0 1-3.2 4.2"/>
                  <path d="M6.6 6.6A17.4 17.4 0 0 0 2 12s3.5 7 10 7a9.7 9.7 0 0 0 5.4-1.6"/>
                  <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>
                  <path d="M2 2l20 20"/>
                } @else {
                  <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/>
                  <circle cx="12" cy="12" r="3"/>
                }
              </svg>
            </button>
          </div>
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
  showPassword = signal(false);
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
