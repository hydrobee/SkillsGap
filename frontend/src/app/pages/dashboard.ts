import { DecimalPipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Api } from '../core/api';
import { Category, Cycle, Dashboard } from '../core/models';
import { errMsg, initials } from '../core/util';

interface Tip { x: number; y: number; title: string; lines: string[]; }

@Component({
  selector: 'app-dashboard',
  imports: [FormsModule, DecimalPipe, RouterLink],
  template: `
    <div class="page-head">
      <div>
        <span class="eyebrow">Overview</span>
        <h1>HR dashboard</h1>
        @if (data(); as d) {
          <p class="subtitle">Assessment cycle {{ d.cycle.year }}
            <span class="chip" [class.good]="d.cycle.is_open" [class.closed]="!d.cycle.is_open">{{ d.cycle.is_open ? 'Open' : 'Closed' }}</span></p>
        }
      </div>
      <div class="toolbar">
        <label class="field">Cycle
          <select [ngModel]="cycleId()" (ngModelChange)="pickCycle($event)">
            @for (c of cycles(); track c.id) { <option [ngValue]="c.id">{{ c.year }}</option> }
          </select>
        </label>
        <a class="btn" routerLink="/setup">Manage cycles &amp; setup</a>
      </div>
    </div>

    @if (error()) { <p class="alert error" role="alert">{{ error() }}</p> }

    @if (data(); as d) {
      <!-- KPI tiles -->
      <section class="kpis" aria-label="Key figures">
        <div class="card kpi">
          <span class="kpi-label">Survey completion</span>
          <span class="kpi-value">{{ pct(d.totals.survey_complete, d.totals.staff) }}<small>%</small></span>
          <div class="progress" aria-hidden="true"><span [style.width.%]="pct(d.totals.survey_complete, d.totals.staff)"></span></div>
          <span class="kpi-sub">{{ d.totals.survey_complete }} of {{ d.totals.staff }} staff finished ·
            {{ d.totals.survey_in_progress }} in progress · {{ d.totals.survey_not_started }} not started</span>
        </div>
        <div class="card kpi">
          <span class="kpi-label">Supervisor ratings</span>
          <span class="kpi-value">{{ pct(d.totals.rating_complete, d.totals.rating_needed) }}<small>%</small></span>
          <div class="progress" aria-hidden="true"><span [style.width.%]="pct(d.totals.rating_complete, d.totals.rating_needed)"></span></div>
          <span class="kpi-sub">{{ d.totals.rating_complete }} of {{ d.totals.rating_needed }} staff fully rated by their supervisor</span>
        </div>
        <div class="card kpi">
          <span class="kpi-label">Staff with a Critical gap</span>
          <span class="kpi-value">{{ d.totals.staff_with_critical }}</span>
          <span class="kpi-sub">of {{ d.totals.assessed }} assessed staff have at least one competency 2+ levels below required</span>
        </div>
        <div class="card kpi">
          <span class="kpi-label">Average gap</span>
          <span class="kpi-value">{{ d.totals.avg_gap === null ? '—' : (d.totals.avg_gap | number: '1.2-2') }}</span>
          <span class="kpi-sub">levels below required, across every assessed competency (0 = meets requirement)</span>
        </div>
      </section>

      @if (d.totals.assessed === 0) {
        <section class="card">
          <div class="empty"><div class="empty-icon" aria-hidden="true">📊</div>
            <p>No one has answered the survey for {{ d.cycle.year }} yet, so there are no gaps to show.</p></div>
        </section>
      } @else {
        <div class="dash-grid">
          <!-- gap distribution: stacked bar, status colours always paired with labels + counts -->
          <section class="card">
            <div class="card-head">
              <div>
                <h2>Gap distribution</h2>
                <p class="muted small">All assessed staff × competency results ({{ catTotal() }})</p>
              </div>
            </div>
            <div class="stack" role="img"
                 [attr.aria-label]="'Critical ' + d.categories.Critical + ', Moderate ' + d.categories.Moderate + ', Minor ' + d.categories.Minor">
              @for (c of cats; track c) {
                @if (d.categories[c]) {
                  <span class="seg" [class]="'seg ' + c" [style.flex-grow]="d.categories[c]"
                        (mouseenter)="showTip($event, c, [d.categories[c] + ' results', pct(d.categories[c], catTotal()) + '% of all results'])"
                        (mousemove)="moveTip($event)" (mouseleave)="tip.set(null)"></span>
                }
              }
            </div>
            <ul class="legend">
              @for (c of cats; track c) {
                <li>
                  <span class="swatch" [class]="'swatch ' + c" aria-hidden="true"></span>
                  <span class="legend-name">{{ c }}</span>
                  <span class="legend-val">{{ d.categories[c] }}</span>
                  <span class="muted small">{{ pct(d.categories[c], catTotal()) }}%</span>
                </li>
              }
            </ul>
            <p class="muted small note">Critical = gap of 2 or more · Moderate = 1 to 2 · Minor = under 1.</p>
          </section>

          <!-- organisation-wide priorities: one series, magnitude -> single accent hue -->
          <section class="card">
            <div class="card-head">
              <div>
                <h2>Organisation training priorities</h2>
                <p class="muted small">Competencies with the largest average gap across all departments</p>
              </div>
            </div>
            @if (d.priorities.length) {
              <ol class="hbars">
                @for (p of d.priorities; track p.competency) {
                  <li (mouseenter)="showTip($event, p.competency, priorityTip(p))"
                      (mousemove)="moveTip($event)" (mouseleave)="tip.set(null)">
                    <div class="hbar-top">
                      <span class="hbar-name"><span class="muted">{{ p.rank }}.</span> {{ p.competency }}</span>
                      <span class="hbar-val">{{ p.avg_gap | number: '1.2-2' }}</span>
                    </div>
                    <div class="hbar-track"><span [style.width.%]="(p.avg_gap / maxGap()) * 100"></span></div>
                    <span class="muted small">{{ p.critical }} Critical · {{ p.moderate }} Moderate</span>
                  </li>
                }
              </ol>
            } @else {
              <p class="muted">No competency has a gap. Everyone assessed meets the required levels.</p>
            }
          </section>
        </div>
      }

      <!-- departments -->
      <section class="card">
        <div class="card-head">
          <div>
            <h2>Departments</h2>
            <p class="muted small">Progress and gaps per department. Open a department for the full report.</p>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>Department</th><th class="num">Staff</th><th>Survey done</th><th>Ratings done</th>
                <th class="num">Avg gap</th><th class="num">Critical staff</th><th>Top priority</th>
                <th class="actions-col"><span class="sr-only">Actions</span></th></tr>
            </thead>
            <tbody>
              @for (x of d.departments; track x.id) {
                <tr>
                  <td class="strong nowrap">{{ x.name }}</td>
                  <td class="num">{{ x.staff_total }}</td>
                  <td>
                    <div class="mini-progress">
                      <div class="progress"><span [style.width.%]="pct(x.survey_complete, x.staff_total)"></span></div>
                      <span class="small nowrap">{{ x.survey_complete }}/{{ x.staff_total }}</span>
                    </div>
                  </td>
                  <td>
                    @if (x.rating_needed) {
                      <div class="mini-progress">
                        <div class="progress"><span [style.width.%]="pct(x.rating_complete, x.rating_needed)"></span></div>
                        <span class="small nowrap">{{ x.rating_complete }}/{{ x.rating_needed }}</span>
                      </div>
                    } @else { <span class="muted small">—</span> }
                  </td>
                  <td class="num">{{ x.avg_gap === null ? '—' : (x.avg_gap | number: '1.2-2') }}</td>
                  <td class="num"><span class="count Critical" [class.zero]="x.critical_staff === 0">{{ x.critical_staff }}</span></td>
                  <td class="nowrap">{{ x.top_priority ?? '—' }}</td>
                  <td>
                    <div class="cell-actions">
                      <a class="btn ghost sm" [routerLink]="['/reports/department']" [queryParams]="{ dept: x.id, cycle: d.cycle.id }">View</a>
                    </div>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </section>

      <div class="dash-grid">
        <!-- follow-ups -->
        <section class="card">
          <div class="card-head">
            <div>
              <h2>Needs follow-up</h2>
              <p class="muted small">Who to remind so the {{ d.cycle.year }} results are complete</p>
            </div>
          </div>

          <h3 class="sub-head">Supervisor ratings outstanding <span class="chip plain neutral">{{ d.pending_supervisors.length }}</span></h3>
          @if (d.pending_supervisors.length) {
            <ul class="people">
              @for (s of d.pending_supervisors; track s.id) {
                <li>
                  <span class="avatar" aria-hidden="true">{{ initials(s.name) }}</span>
                  <span class="list-text"><span class="list-title">{{ s.name }}</span>
                    <span class="list-sub">{{ s.pending }} of {{ s.team }} team {{ s.team === 1 ? 'member' : 'members' }} not fully rated</span></span>
                  <span class="chip closed">{{ s.pending }} pending</span>
                </li>
              }
            </ul>
          } @else { <p class="muted small">All supervisors have finished rating. ✓</p> }

          <h3 class="sub-head">Surveys not finished <span class="chip plain neutral">{{ d.survey_pending.length }}</span></h3>
          @if (d.survey_pending.length) {
            <ul class="people">
              @for (p of shownPending(); track p.id) {
                <li>
                  <span class="avatar" aria-hidden="true">{{ initials(p.name) }}</span>
                  <span class="list-text"><span class="list-title">{{ p.name }}</span>
                    <span class="list-sub">{{ p.department ?? 'No department' }} · {{ p.answered }}/{{ p.questions }} answered</span></span>
                  <span class="chip" [class.neutral]="p.survey === 'Not started'">{{ p.survey }}</span>
                </li>
              }
            </ul>
            @if (d.survey_pending.length > pendingLimit) {
              <button type="button" class="btn ghost sm" (click)="showAll.set(!showAll())">
                {{ showAll() ? 'Show fewer' : 'Show all ' + d.survey_pending.length }}
              </button>
            }
          } @else { <p class="muted small">Everyone has finished their survey. ✓</p> }
        </section>

        <!-- staff needing attention -->
        <section class="card">
          <div class="card-head">
            <div>
              <h2>Staff needing attention</h2>
              <p class="muted small">Most Critical gaps first. Open a name for the individual report.</p>
            </div>
          </div>
          @if (d.attention.length) {
            <ul class="people">
              @for (p of d.attention; track p.id) {
                <li>
                  <a class="person-link" [routerLink]="['/reports/individual']" [queryParams]="{ person: p.id, cycle: d.cycle.id }">
                    <span class="avatar" aria-hidden="true">{{ initials(p.name) }}</span>
                    <span class="list-text"><span class="list-title">{{ p.name }}</span>
                      <span class="list-sub">{{ p.department ?? 'No department' }} · avg gap {{ p.avg_gap | number: '1.2-2' }}</span></span>
                  </a>
                  <span class="person-counts">
                    <span class="count Critical">{{ p.critical }} Critical</span>
                    @if (p.moderate) { <span class="count Moderate">{{ p.moderate }} Moderate</span> }
                  </span>
                </li>
              }
            </ul>
          } @else {
            <p class="muted small">No assessed staff have a Critical gap. ✓</p>
          }
        </section>
      </div>

      @if (tip(); as t) {
        <div class="chart-tip" role="tooltip" [style.left.px]="t.x" [style.top.px]="t.y">
          <strong>{{ t.title }}</strong>
          @for (l of t.lines; track $index) { <span>{{ l }}</span> }
        </div>
      }
    }
  `,
})
export class DashboardPage implements OnInit {
  private api = inject(Api);
  cycles = signal<Cycle[]>([]);
  cycleId = signal<number | null>(null);
  data = signal<Dashboard | null>(null);
  error = signal('');
  tip = signal<Tip | null>(null);
  showAll = signal(false);

  cats: Category[] = ['Critical', 'Moderate', 'Minor'];
  pendingLimit = 6;
  initials = initials;

  catTotal = computed(() => {
    const c = this.data()?.categories;
    return c ? c.Critical + c.Moderate + c.Minor : 0;
  });
  /** Bars share one scale; at least 1 level so a tiny max gap doesn't look huge. */
  maxGap = computed(() => Math.max(1, ...(this.data()?.priorities ?? []).map((p) => p.avg_gap)));
  shownPending = computed(() => {
    const all = this.data()?.survey_pending ?? [];
    return this.showAll() ? all : all.slice(0, this.pendingLimit);
  });

  ngOnInit() {
    this.api.cycles().subscribe({
      next: (cycles) => {
        this.cycles.set(cycles);
        this.cycleId.set(cycles[0]?.id ?? null);
        this.load();
      },
      error: (e) => this.error.set(errMsg(e)),
    });
  }

  pickCycle(id: number) { this.cycleId.set(id); this.load(); }

  private load() {
    this.error.set('');
    this.api.dashboard(this.cycleId()).subscribe({
      next: (d) => { this.data.set(d); this.showAll.set(false); },
      error: (e) => { this.data.set(null); this.error.set(errMsg(e)); },
    });
  }

  priorityTip(p: Dashboard['priorities'][number]) {
    return [`Avg gap ${p.avg_gap.toFixed(2)}`,
      `${p.critical} Critical · ${p.moderate} Moderate · ${p.minor} Minor`, `${p.staff_count} staff assessed`];
  }

  pct(n: number, of: number) { return of ? Math.round((n / of) * 100) : 0; }

  showTip(e: MouseEvent, title: string, lines: string[]) {
    this.tip.set({ title, lines, ...this.tipPos(e) });
  }
  moveTip(e: MouseEvent) {
    const t = this.tip();
    if (t) this.tip.set({ ...t, ...this.tipPos(e) });
  }
  /** Keep the tooltip next to the cursor but inside the viewport. */
  private tipPos(e: MouseEvent) {
    const w = 220;
    const x = e.clientX + 14 + w > window.innerWidth ? e.clientX - w - 14 : e.clientX + 14;
    return { x: Math.max(8, x), y: e.clientY + 14 };
  }
}
