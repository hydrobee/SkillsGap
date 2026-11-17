import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { Auth } from './auth';
import { Role } from './models';

/** Allow the route only for logged-in users, optionally limited to some roles. */
export const roleGuard = (...roles: Role[]): CanActivateFn => () => {
  const auth = inject(Auth);
  const router = inject(Router);
  const role = auth.role();
  if (!role) return router.parseUrl('/login');
  if (roles.length && !roles.includes(role)) return router.parseUrl(auth.homePath());
  return true;
};

/** Attach the JWT to every request; a 401 elsewhere means the session expired. */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(Auth);
  const token = auth.user()?.token;
  const authed = token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;
  return next(authed).pipe(
    catchError((err) => {
      if (err.status === 401 && !req.url.endsWith('/auth/login')) auth.logout();
      return throwError(() => err);
    }),
  );
};
