import { DecimalPipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { forkJoin } from 'rxjs';
import { Api } from '../core/api';
import { Auth } from '../core/auth';
import { Cycle, IndividualReport, Person } from '../core/models';
import { downloadCsv, errMsg, initials } from '../core/util';

@Component({
  selector: 'app-individual-report',
  imports: [FormsModule, DecimalPipe],
  template: `
    <div class="page-head no-print">
      <div>
        <span class="eyebrow">Reports</span>
        <h1>Individual report</h1>
      </div>
      <div class="toolbar">
        @if (canPick()) {
          <div class="field search-field">
            <label class="sr-only" for="staff-search">Search staff</label>
            <span aria-hidden="true">Staff</span>
            <div class="combo">
              <svg class="combo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
              <input id="staff-search" type="search" autocomplete="off" role="combobox"
                     aria-controls="staff-results" [attr.aria-expanded]="open()"
                     [attr.aria-activedescendant]="open() && matches().length ? 'staff-opt-' + active() : null"
                     placeholder="Search by name, department or job scope…"
                     [value]="open() ? query() : selectedName()"
                     (focus)="openList()" (input)="onQuery($any($event.target).value)"
                     (keydown)="onKey($event)" (blur)="closeList()" />
              @if (open()) {
                <ul class="combo-list" id="staff-results" role="listbox">
                  @for (p of matches(); track p.id; let i = $index) {
                    <li role="option" [id]="'staff-opt-' + i" [attr.aria-selected]="p.id === personId()"
                        [class.active]="i === active()" [class.selected]="p.id === personId()"
                        (mousedown)="$event.preventDefault(); choose(p)" (mouseenter)="active.set(i)">
                      <span class="avatar" aria-hidden="true">{{ initials(p.name) }}</span>
                      <span class="list-text">
                        <span class="list-title">{{ p.name }}</span>
                        <span class="list-sub">{{ subtitle(p) }}</span>
                      </span>
                    </li>
                  } @empty {
                    <li class="combo-empty">No staff match “{{ query() }}”.</li>
                  }
                </ul>
              }
            </div>
          </div>
        }
        <label class="field">Cycle
          <select [ngModel]="cycleId()" (ngModelChange)="pickCycle($event)">
            @for (c of cycles(); track c.id) { <option [ngValue]="c.id">{{ c.year }}</option> }
          </select>
        </label>
        <div class="btn-group">
          <button class="btn" type="button" (click)="csv()" [disabled]="!report()?.rows?.length"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg> CSV</button>
          <button class="btn" type="button" (click)="print()" [disabled]="!report()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2M6 14h12v8H6z"/></svg> Print / PDF</button>
        </div>
      </div>
    </div>

    @if (error()) { <p class="alert error" role="alert">{{ error() }}</p> }

    @if (report(); as r) {
      <section class="card report">
        <h2 class="print-title">Individual competency gap report</h2>
        <dl class="meta">
          <div><dt>Staff</dt><dd>{{ r.header.staff_name }}</dd></div>
          <div><dt>Job scope</dt><dd>{{ r.header.job_scope }}</dd></div>
          <div><dt>Department</dt><dd>{{ r.header.department ?? '—' }}</dd></div>
          <div><dt>Assessment cycle</dt><dd>{{ r.header.cycle.year }} ({{ r.header.cycle.is_open ? 'open' : 'closed' }})</dd></div>
          <div><dt>Supervisor rating</dt>
            <dd><span class="chip" [class.good]="r.header.supervisor_rating_status === 'Complete'">{{ r.header.supervisor_rating_status }}</span></dd></div>
          <div><dt>Survey</dt><dd>{{ r.header.survey_progress }}</dd></div>
        </dl>

        @if (r.rows.length) {
          <div class="table-wrap cards">
            <table>
              <thead>
                <tr><th>Competency</th><th class="num">Required</th>
                <th class="num">Actual</th><th class="num">Gap</th><th>Category</th></tr>
              </thead>
              <tbody>
                @for (row of r.rows; track row.competency_id) {
                  <tr>
                    <td class="strong row-title">{{ row.competency }}</td>
                    <td class="num" data-label="Required">{{ row.required }}</td>
                    <!-- <td class="num muted">{{ row.self | number: '1.0-2' }}</td> -->
                    <!-- <td class="num muted">{{ row.supervisor === null ? 'pending' : row.supervisor }}</td> -->
                    <td class="num" data-label="Actual">{{ row.actual | number: '1.0-2' }}</td>
                    <td class="num" data-label="Gap"><b>{{ row.gap | number: '1.0-2' }}</b></td>
                    <td data-label="Category"><span class="badge" [class]="row.category">{{ row.category }}</span></td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
          <p class="summary">{{ r.summary }}</p>
          @if (hasPending(r)) {
            <p class="muted small note">Where the supervisor has not rated yet, Actual uses the self score only.</p>
          }
        } @else {
          <div class="empty"><div class="empty-icon" aria-hidden="true">📋</div>
            <p>No survey answers yet ({{ r.header.survey_progress }}).</p></div>
        }
      </section>
    }
  `,
})
export class IndividualReportPage implements OnInit {
  private api = inject(Api);
  private auth = inject(Auth);
  private route = inject(ActivatedRoute);
  people = signal<Person[]>([]);
  cycles = signal<Cycle[]>([]);
  personId = signal<number | null>(null);
  cycleId = signal<number | null>(null);
  report = signal<IndividualReport | null>(null);
  error = signal('');

  ngOnInit() {
    forkJoin({ people: this.api.people(), cycles: this.api.cycles() }).subscribe({
      next: ({ people, cycles }) => {
        this.people.set(people);
        this.cycles.set(cycles);
        // ?person=…&cycle=… lets other pages (e.g. the department report) link straight to someone
        const q = this.route.snapshot.queryParamMap;
        const want = Number(q.get('person')) || this.auth.user()?.user_id;
        const wantCycle = Number(q.get('cycle'));
        this.personId.set(people.find((p) => p.id === want)?.id ?? people[0]?.id ?? null);
        this.cycleId.set(cycles.find((c) => c.id === wantCycle)?.id ?? cycles[0]?.id ?? null);
        this.load();
      },
      error: (e) => this.error.set(errMsg(e)),
    });
  }

  /** Staff only ever see their own report, so only HR and supervisors get the staff search. */
  canPick = computed(() => this.auth.role() !== 'staff');
  initials = initials;
  subtitle(p: Person) { return [p.job_scope, p.department].filter(Boolean).join(' · ') || p.role; }

  query = signal('');
  open = signal(false);
  active = signal(0);
  selectedName = computed(() => this.people().find((p) => p.id === this.personId())?.name ?? '');
  matches = computed(() => {
    const words = this.query().toLowerCase().split(/\s+/).filter(Boolean);
    return this.people().filter((p) => {
      const hay = [p.name, p.department, p.job_scope, p.role].filter(Boolean).join(' ').toLowerCase();
      return words.every((w) => hay.includes(w));
    });
  });

  openList() { this.query.set(''); this.active.set(0); this.open.set(true); }
  closeList() { this.open.set(false); }
  onQuery(v: string) { this.query.set(v); this.active.set(0); this.open.set(true); }

  choose(p: Person) {
    this.open.set(false);
    (document.activeElement as HTMLElement | null)?.blur();
    if (p.id !== this.personId()) this.pickPerson(p.id);
  }

  onKey(e: KeyboardEvent) {
    const n = this.matches().length;
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (!this.open()) { this.openList(); return; }
      if (n) this.active.update((i) => (i + (e.key === 'ArrowDown' ? 1 : n - 1)) % n);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const p = this.matches()[this.active()];
      if (this.open() && p) this.choose(p);
    } else if (e.key === 'Escape') {
      this.closeList();
    }
  }

  pickPerson(id: number) { this.personId.set(id); this.load(); }
  pickCycle(id: number) { this.cycleId.set(id); this.load(); }

  private load() {
    const id = this.personId();
    if (id === null) return;
    this.error.set('');
    this.api.individual(id, this.cycleId()).subscribe({
      next: (r) => this.report.set(r),
      error: (e) => { this.report.set(null); this.error.set(errMsg(e)); },
    });
  }

  hasPending(r: IndividualReport) { return r.rows.some((x) => x.supervisor_pending); }
  print() { window.print(); }

  csv() {
    const r = this.report();
    if (!r) return;
    downloadCsv(`gap-report-${r.header.staff_name.replace(/\W+/g, '_')}-${r.header.cycle.year}.csv`,
      ['Competency', 'Required', 'Self', 'Supervisor', 'Actual', 'Gap', 'Category'],
      r.rows.map((x) => [x.competency, x.required, x.self, x.supervisor ?? 'pending', x.actual, x.gap, x.category]));
  }
}
