import { HttpErrorResponse } from '@angular/common/http';

/** Turn a failed HTTP call into a short message a person can read. */
export function errMsg(e: unknown): string {
  const err = e as HttpErrorResponse;
  const d = err?.error?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((x) => x.msg).join('; ');
  if (err?.status === 0) return 'Cannot reach the server. Is the backend running on port 8000?';
  return 'Something went wrong. Please try again.';
}

/** Download rows as a CSV file (opens in Excel). */
export function downloadCsv(filename: string, header: string[], rows: (string | number | null)[][]) {
  const esc = (v: string | number | null) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const text = [header, ...rows].map((r) => r.map(esc).join(',')).join('\r\n');
  const blob = new Blob(['﻿' + text], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

/** "Aiman Bin Ali" -> "AB" for avatar badges. */
export function initials(name: string): string {
  // ignore bracketed / punctuation words, e.g. "Dayang (Academic Supervisor)" -> "DA"
  const words = name.replace(/[()[\]]/g, ' ').split(/\s+/).filter((w) => /^\p{L}/u.test(w));
  return words.slice(0, 2).map((w) => w[0].toUpperCase()).join('') || '?';
}
