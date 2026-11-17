import { DecimalPipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { Api } from '../core/api';
import { Category, Cycle, DeptReport, DeptStaff, NamedItem } from '../core/models';
import { downloadCsv, errMsg, initials } from '../core/util';

@Component({
  selector: 'app-department-report',
  imports: [FormsModule, DecimalPipe, RouterLink],
  template: `
    <div class="page-head no-print">
      <div>
        <span class="eyebrow">Reports</span>
        <h1>Department report</h1>
      </div>
      <div class="toolbar">
        <label class="field">Department
          <select [ngModel]="deptId()" (ngModelChange)="pickDept($event)">
            @for (d of depts(); track d.id) { <option [ngValue]="d.id">{{ d.name }}</option> }
          </select>
        </label>
        <label class="field">Cycle
          <select [ngModel]="cycleId()" (ngModelChange)="pickCycle($event)">
            @for (c of cycles(); track c.id) { <option [ngValue]="c.id">{{ c.year }}</option> }
          </select>
        </label>
        <div class="btn-group">
          <button class="btn" type="button" (click)="csv()" [disabled]="!report()?.competencies?.length"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg> CSV</button>
          <button class="btn" type="button" (click)="print()" [disabled]="!report()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2M6 14h12v8H6z"/></svg> Print / PDF</button>
        </div>
      </div>
    </div>

    @if (error()) { <p class="alert error" role="alert">{{ error() }}</p> }

    @if (report(); as r) {
      <section class="card report">
        <h2 class="print-title">Department competency gap report</h2>
        <dl class="meta">
          <div><dt>Department</dt><dd>{{ r.header.department }}</dd></div>
          <div><dt>Assessment cycle</dt><dd>{{ r.header.cycle.year }} ({{ r.header.cycle.is_open ? 'open' : 'closed' }})</dd></div>
          <div><dt>Staff assessed</dt><dd>{{ r.header.staff_assessed }} of {{ r.header.staff_total }} staff</dd></div>
        </dl>

        @if (r.competencies.length) {
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Competency</th><th class="num">Required</th><th class="num">Avg actual</th>
                  <th class="num">Avg gap</th><th class="num">Critical</th><th class="num">Moderate</th><th class="num">Minor</th></tr>
              </thead>
              <tbody>
                @for (c of r.competencies; track c.competency) {
                  <tr>
                    <td class="strong">{{ c.competency }}</td>
                    <td class="num">{{ c.required | number: '1.0-2' }}</td>
                    <td class="num">{{ c.avg_actual | number: '1.0-2' }}</td>
                    <td class="num"><b>{{ c.avg_gap | number: '1.0-2' }}</b></td>
                    <td class="num"><span class="count Critical" [class.zero]="c.critical === 0">{{ c.critical }}</span></td>
                    <td class="num"><span class="count Moderate" [class.zero]="c.moderate === 0">{{ c.moderate }}</span></td>
                    <td class="num"><span class="count Minor" [class.zero]="c.minor === 0">{{ c.minor }}</span></td>
                  </tr>
                }
              </tbody>
            </table>
          </div>

          <h3>Top 3 training priorities <span class="muted small">(ranked by average gap)</span></h3>
          @if (r.top_priorities.length) {
            <p class="muted small no-print">Select a priority to see which staff are Critical or Moderate.</p>
            <ol class="priorities">
              @for (p of r.top_priorities; track p.competency) {
                <li>
                  <button type="button" class="priority-btn" [class.on]="open() === p.competency"
                          [attr.aria-expanded]="open() === p.competency" aria-controls="priority-staff"
                          (click)="toggle(p.competency)">
                    <span class="rank">{{ p.rank }}</span>
                    <span class="p-body">
                      <span class="p-title">{{ p.competency }}</span>
                      <span class="p-sub">Avg gap {{ p.avg_gap | number: '1.0-2' }}</span>
                      <span class="p-counts">
                        <span class="count Critical" [class.zero]="p.critical === 0">{{ p.critical }} Critical</span>
                        <span class="count Moderate" [class.zero]="p.moderate === 0">{{ p.moderate }} Moderate</span>
                      </span>
                    </span>
                    <svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>
                  </button>
                </li>
              }
            </ol>

            @if (openRow(); as p) {
              <div class="staff-panel" id="priority-staff">
                <div class="between">
                  <h3>Who needs training in {{ p.competency }}</h3>
                  <button type="button" class="btn ghost sm no-print" (click)="open.set(null)">Close</button>
                </div>
                <div class="staff-groups">
                  @for (cat of focusCats; track cat) {
                    <div class="staff-group">
                      <div class="staff-group-head">
                        <span class="badge" [class]="cat">{{ cat }}</span>
                        <span class="muted small">{{ inCat(p.staff, cat).length }} staff</span>
                      </div>
                      <ul class="staff-list">
                        @for (s of inCat(p.staff, cat); track s.id) {
                          <li>
                            <a [routerLink]="['/reports/individual']" [queryParams]="{ person: s.id, cycle: cycleId() }">
                              <span class="avatar" aria-hidden="true">{{ initials(s.name) }}</span>
                              <span class="list-title">{{ s.name }}</span>
                            </a>
                            <span class="muted small nowrap">actual {{ s.actual | number: '1.0-2' }} · gap <b>{{ s.gap | number: '1.0-2' }}</b></span>
                          </li>
                        } @empty {
                          <li class="muted small">No staff in this category.</li>
                        }
                      </ul>
                    </div>
                  }
                </div>
                @if (p.minor) {
                  <p class="muted small note">{{ p.minor }} other staff are Minor for this competency.</p>
                }
              </div>
            }
          } @else {
            <p class="muted">No competency has a gap, so no training priorities.</p>
          }
          @if (r.header.supervisor_ratings_incomplete > 0) {
            <p class="muted small note">{{ r.header.supervisor_ratings_incomplete }} assessed staff
              still have missing supervisor ratings. Their results use the self score where a rating is missing.</p>
          }
        } @else {
          <div class="empty"><div class="empty-icon" aria-hidden="true">📊</div>
            <p>Nobody in this department has answered the survey yet.</p></div>
        }
      </section>
    }
  `,
})
export class DepartmentReportPage implements OnInit {
  private api = inject(Api);
  depts = signal<NamedItem[]>([]);
  cycles = signal<Cycle[]>([]);
  deptId = signal<number | null>(null);
  cycleId = signal<number | null>(null);
  report = signal<DeptReport | null>(null);
  error = signal('');

  /** Which top-priority competency has its staff list expanded. */
  open = signal<string | null>(null);
  openRow = computed(() => this.report()?.top_priorities.find((p) => p.competency === this.open()) ?? null);
  focusCats: Category[] = ['Critical', 'Moderate'];
  initials = initials;

  toggle(competency: string) { this.open.update((c) => (c === competency ? null : competency)); }
  inCat(staff: DeptStaff[], cat: Category) { return staff.filter((s) => s.category === cat); }

  ngOnInit() {
    forkJoin({ depts: this.api.departments(), cycles: this.api.cycles() }).subscribe({
      next: ({ depts, cycles }) => {
        this.depts.set(depts);
        this.cycles.set(cycles);
        this.deptId.set(depts[0]?.id ?? null);
        this.cycleId.set(cycles[0]?.id ?? null);
        this.load();
      },
      error: (e) => this.error.set(errMsg(e)),
    });
  }

  pickDept(id: number) { this.deptId.set(id); this.load(); }
  pickCycle(id: number) { this.cycleId.set(id); this.load(); }

  private load() {
    const id = this.deptId();
    if (id === null) return;
    this.error.set('');
    this.api.department(id, this.cycleId()).subscribe({
      next: (r) => { this.report.set(r); this.open.set(null); },
      error: (e) => { this.report.set(null); this.error.set(errMsg(e)); },
    });
  }

  print() { window.print(); }

  csv() {
    const r = this.report();
    if (!r) return;
    downloadCsv(`department-report-${r.header.department.replace(/\W+/g, '_')}-${r.header.cycle.year}.csv`,
      ['Competency', 'Required', 'Avg actual', 'Avg gap', 'Critical', 'Moderate', 'Minor'],
      r.competencies.map((c) => [c.competency, c.required, c.avg_actual, c.avg_gap, c.critical, c.moderate, c.minor]));
  }
}
