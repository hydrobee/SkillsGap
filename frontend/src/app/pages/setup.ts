import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { Api } from '../core/api';
import { ConfirmDialog } from '../components/confirm-dialog';
import { ItemSelect } from '../components/item-select';
import { CycleSummary, SetupOverview } from '../core/models';
import { errMsg } from '../core/util';

@Component({
  selector: 'app-setup',
  imports: [FormsModule, ItemSelect, ConfirmDialog],
  template: `
    <div class="page-head">
      <div>
        <span class="eyebrow">Administration</span>
        <h1>HR setup</h1>
        <p class="subtitle">Manage assessment cycles, job scopes, required levels and survey questions.</p>
      </div>
    </div>
    @if (error()) { <p class="alert error" role="alert">{{ error() }}</p> }

    <section class="card">
      <div class="card-head">
        <div>
          <h2>Assessment cycles</h2>
          <p class="muted small">Staff and supervisors can change answers and ratings only while a cycle is open.</p>
        </div>
        <div class="toolbar">
          <label class="field">New cycle year
            <input type="number" min="2000" max="2100" [(ngModel)]="newYear" />
          </label>
          <label class="field">Copy required levels from
            <select [ngModel]="copyFrom()" (ngModelChange)="copyFrom.set($event)">
              <option [ngValue]="null">Start empty</option>
              @for (c of cycles(); track c.id) { <option [ngValue]="c.id">{{ c.year }}</option> }
            </select>
          </label>
          <button class="btn primary" type="button" (click)="addCycle()">Add cycle</button>
        </div>
      </div>
      <div class="table-wrap cards">
        <table>
          <thead><tr><th>Year</th><th>Status</th><th class="actions-col"><span class="sr-only">Actions</span></th></tr></thead>
          <tbody>
            @for (c of cycles(); track c.id) {
              <tr>
                <td class="strong row-title">{{ c.year }}</td>
                <td data-label="Status"><span class="chip" [class.good]="c.is_open" [class.closed]="!c.is_open">{{ c.is_open ? 'Open' : 'Closed' }}</span></td>
                <td class="row-actions">
                  <div class="cell-actions">
                    <button class="btn sm" type="button" (click)="toggleCycle(c)">{{ c.is_open ? 'Close cycle' : 'Reopen' }}</button>
                  </div>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </section>

    @if (data(); as d) {
      <section class="card">
        <div class="card-head">
          <div>
            <h2>Job scopes, competencies and required levels</h2>
            <p class="muted small">Required levels are set per year. Pick a year and a job scope to edit its required levels; survey questions are the same every year.</p>
          </div>
        </div>
        <div class="toolbar">
          <label class="field">Year
            <select [ngModel]="yearId()" (ngModelChange)="pickYear($event)">
              @for (c of cycles(); track c.id) { <option [ngValue]="c.id">{{ c.year }}</option> }
            </select>
          </label>
          <button class="btn danger" type="button" (click)="deleteYear()" [disabled]="cycles().length <= 1"
                  [attr.title]="cycles().length <= 1 ? 'The only remaining year cannot be deleted' : null">Delete year cycle</button>
          <span class="spacer"></span>
          <div class="field">Job scope
            <app-item-select label="Job scope" placeholder="No job scopes" [items]="scopeItems()" [value]="scopeId()"
                             (valueChange)="scopeId.set($event)" (remove)="askDeleteScope($event)" />
          </div>
          <span class="spacer"></span>
          <label class="field">New job scope
            <input placeholder="e.g. Data Analyst" [(ngModel)]="newScope" />
          </label>
          <button class="btn" type="button" (click)="addScope()" [disabled]="!newScope().trim()">Add job scope</button>
        </div>

        @if (selectedYear(); as y) {
          @if (y.levels === 0 && otherYears().length) {
            <div class="alert" role="status">
              <p>No required levels are set for {{ y.year }} yet.</p>
              <div class="toolbar">
                <label class="field">Copy from
                  <select [ngModel]="copySource() ?? otherYears()[0].id" (ngModelChange)="copySource.set($event)">
                    @for (c of otherYears(); track c.id) { <option [ngValue]="c.id">{{ c.year }}</option> }
                  </select>
                </label>
                <button class="btn" type="button" (click)="copyIntoYear()">Copy required levels</button>
              </div>
            </div>
          }
        }

        @if (scope(); as s) {
          <div class="card-section">
            <h3>Required levels for {{ s.name }} · {{ data()?.cycle?.year }}</h3>
            <p class="muted small">1 = basic, 5 = expert. Changes here apply to {{ data()?.cycle?.year }} only.</p>
            <div class="table-wrap cards">
              <table>
                <thead><tr><th>Competency</th><th>Required level</th><th class="actions-col"><span class="sr-only">Actions</span></th></tr></thead>
                <tbody>
                  @for (c of s.competencies; track c.competency_id) {
                    <tr>
                      <td class="strong row-title">{{ c.name }}</td>
                      <td data-label="Required level">
                        <select class="sm" [attr.aria-label]="'Required level for ' + c.name" [ngModel]="c.required_level"
                                (ngModelChange)="run(api.setLevel(s.id, c.competency_id, $event, yearId()))">
                          @for (n of levels; track n) { <option [ngValue]="n">{{ n }}</option> }
                        </select>
                      </td>
                      <td class="row-actions">
                        <div class="cell-actions">
                          <button class="btn danger sm" type="button" (click)="removeComp(s.id, c.competency_id, c.name)">Remove</button>
                        </div>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>

            <div class="toolbar note">
              <div class="field">Add existing competency
                <app-item-select label="Existing competency" placeholder="Select competency…" [items]="compItems()"
                                 [value]="addComp()" (valueChange)="addComp.set($event)" (remove)="askDeleteComp($event)" />
              </div>
              <label class="field">Level
                <select [ngModel]="addLevel()" (ngModelChange)="addLevel.set($event)">
                  @for (n of levels; track n) { <option [ngValue]="n">Level {{ n }}</option> }
                </select>
              </label>
              <button class="btn" type="button" (click)="attachComp(s.id)" [disabled]="addComp() === null">Add to scope</button>
              <span class="spacer"></span>
              <label class="field">Create new competency
                <input placeholder="e.g. Data literacy" [(ngModel)]="newComp" />
              </label>
              <button class="btn" type="button" (click)="addNewComp()" [disabled]="!newComp().trim()">Create</button>
            </div>
          </div>

          <div class="card-section">
            <h3>Survey questions for {{ s.name }}</h3>
            <div class="table-wrap cards wide">
              <table>
                <thead><tr><th>Competency</th><th>Question</th><th>Wording</th><th class="actions-col"><span class="sr-only">Actions</span></th></tr></thead>
                <tbody>
                  @for (q of s.questions; track q.id) {
                    <tr>
                      <td class="strong row-title">{{ q.competency }}</td>
                      <td class="stacked" data-label="Question">
                        @if (editingId() === q.id) {
                          <input class="wide" [attr.aria-label]="'Edit question ' + q.id" [(ngModel)]="editText" />
                        } @else { {{ q.text }} }
                      </td>
                      <td class="nowrap" data-label="Wording">
                        <div>
                          <span class="chip" [class.closed]="q.is_negative">{{ q.is_negative ? 'Negative' : 'Positive' }}</span>
                          @if (q.answer_count) { <div class="muted small">{{ q.answer_count }} answers</div> }
                        </div>
                      </td>
                      <td class="row-actions">
                        <div class="cell-actions">
                          @if (editingId() === q.id) {
                            <button class="btn primary sm" type="button" (click)="saveEdit(q.id)">Save</button>
                            <button class="btn ghost sm" type="button" (click)="editingId.set(null)">Cancel</button>
                          } @else {
                            <button class="btn ghost sm" type="button" (click)="startEdit(q.id, q.text)">Edit</button>
                            <button class="btn danger sm" type="button" (click)="removeQuestion(q.id, q.answer_count)">Delete</button>
                          }
                        </div>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>

          <div class="card-section">
            <h3>Add a question</h3>
            <div class="toolbar">
              <label class="field">Competency
                <select [ngModel]="qComp()" (ngModelChange)="qComp.set($event)">
                  <option [ngValue]="null">Select…</option>
                  @for (c of s.competencies; track c.competency_id) { <option [ngValue]="c.competency_id">{{ c.name }}</option> }
                </select>
              </label>
              <label class="field grow">Question text
                <input placeholder="e.g. I can explain my work to non-technical people." [(ngModel)]="qText" />
              </label>
            </div>
            <div class="between note">
              <label class="check"><input type="checkbox" [ngModel]="qNeg()" (ngModelChange)="qNeg.set($event)" />
                Negatively worded (e.g. "I struggle to…")</label>
              <button class="btn primary" type="button" (click)="addQuestion(s.id)"
                      [disabled]="qComp() === null || qText().trim().length < 3">Add question</button>
            </div>
            <p class="muted small note">Negatively worded answers are reversed (5 becomes 1) before scoring.
              A competency must have a required level in the scope before you can add questions for it.</p>
          </div>
        }
      </section>
    }

    @if (pending(); as p) {
      <app-confirm-dialog [title]="p.kind === 'scope' ? 'Delete job scope?' : 'Delete competency?'" [blocked]="!!p.blocked"
                          confirmLabel="Delete permanently" (confirm)="confirmDelete()" (cancel)="pending.set(null)">
        @if (p.blocked) { <p>{{ p.blocked }}</p> } @else { @for (l of p.lines; track l) { <p>{{ l }}</p> } }
      </app-confirm-dialog>
    }
  `,
})
export class SetupPage implements OnInit {
  api = inject(Api);
  levels = [1, 2, 3, 4, 5];
  data = signal<SetupOverview | null>(null);
  cycles = signal<CycleSummary[]>([]);
  yearId = signal<number | null>(null);          // the year shown in the required-levels editor
  selectedYear = computed(() => this.cycles().find((c) => c.id === this.yearId()) ?? null);
  otherYears = computed(() => this.cycles().filter((c) => c.id !== this.yearId()));
  copyFrom = signal<number | null>(null);        // "copy levels from" when adding a year
  copySource = signal<number | null>(null);      // same, when filling an empty year
  private copyFromSet = false;
  scopeId = signal<number | null>(null);
  scope = computed(() => this.data()?.job_scopes.find((s) => s.id === this.scopeId()) ?? null);
  scopeItems = computed(() => (this.data()?.job_scopes ?? []).map((s) => ({ id: s.id, label: s.name })));
  compItems = computed(() => this.availableComps().map((c) => ({ id: c.id, label: c.name })));
  pending = signal<{ kind: 'scope' | 'competency'; id: number; name: string; blocked: string | null; lines: string[] } | null>(null);
  availableComps = computed(() => {
    const s = this.scope();
    const used = new Set(s?.competencies.map((c) => c.competency_id));
    return (this.data()?.competencies ?? []).filter((c) => !used.has(c.id));
  });
  error = signal('');

  newYear = signal(new Date().getFullYear() + 1);
  newScope = signal('');
  newComp = signal('');
  addComp = signal<number | null>(null);
  addLevel = signal(3);
  qComp = signal<number | null>(null);
  qText = signal('');
  qNeg = signal(false);
  editingId = signal<number | null>(null);
  editText = signal('');

  ngOnInit() { this.refresh(); }

  private seq = 0;  // only the latest refresh may update the screen (responses can arrive out of order)

  refresh() {
    const n = ++this.seq;
    this.api.listCycles().subscribe({
      next: (c) => {
        if (n !== this.seq) return;
        this.cycles.set(c);
        if (!this.copyFromSet) { this.copyFrom.set(c[0]?.id ?? null); this.copyFromSet = true; }
        if (!c.some((x) => x.id === this.yearId())) this.yearId.set(c[0]?.id ?? null);
        this.api.overview(this.yearId()).subscribe({
          next: (d) => {
            if (n !== this.seq) return;
            this.data.set(d);
            if (!d.job_scopes.some((s) => s.id === this.scopeId())) this.scopeId.set(d.job_scopes[0]?.id ?? null);
          },
          error: (e) => this.error.set(errMsg(e)),
        });
      },
      error: (e) => this.error.set(errMsg(e)),
    });
  }

  /** Run any change, then reload the screen; show the server's message if it is refused. */
  run(call: Observable<unknown>, after?: () => void) {
    this.error.set('');
    call.subscribe({
      next: () => { after?.(); this.refresh(); },
      error: (e) => { this.error.set(errMsg(e)); window.scrollTo({ top: 0, behavior: 'smooth' }); this.refresh(); },
    });
  }

  pickYear(id: number) {
    this.yearId.set(id);
    this.data.set(null);   // rebuild the editor from scratch so no dropdown keeps another year's choice
    this.refresh();
  }

  copyIntoYear() {
    const to = this.yearId(), from = this.copySource() ?? this.otherYears()[0]?.id;
    if (to !== null && from !== undefined) this.run(this.api.copyLevels(to, from));
  }

  deleteYear() {
    const y = this.selectedYear();
    if (!y) return;
    const extra = y.answers || y.ratings
      ? `, plus ${y.answers} survey answer(s) and ${y.ratings} supervisor rating(s) recorded for ${y.year}`
      : '';
    const msg = `Delete the ${y.year} year cycle?\n\nThis will permanently remove its ${y.levels} required level(s)${extra}. `
      + 'Job scopes, competencies, survey questions and other years are kept.\n\nThis cannot be undone.';
    if (confirm(msg)) this.run(this.api.deleteCycle(y.id, y.answers + y.ratings > 0), () => this.yearId.set(null));
  }

  toggleCycle(c: CycleSummary) { this.run(c.is_open ? this.api.closeCycle(c.id) : this.api.openCycle(c.id)); }
  addCycle() { this.run(this.api.createCycle(Number(this.newYear()), this.copyFrom()), () => this.yearId.set(null)); }
  addScope() { this.run(this.api.createScope(this.newScope().trim()), () => this.newScope.set('')); }
  addNewComp() { this.run(this.api.createCompetency(this.newComp().trim()), () => this.newComp.set('')); }

  attachComp(scopeId: number) {
    const id = this.addComp();
    if (id !== null) this.run(this.api.setLevel(scopeId, id, this.addLevel(), this.yearId()), () => this.addComp.set(null));
  }

  removeComp(scopeId: number, compId: number, name: string) {
    if (confirm(`Remove ${name} from this job scope?`)) this.run(this.api.removeLevel(scopeId, compId, this.yearId()));
  }

  /** Open the delete confirmation for a job scope, or explain why it cannot be deleted. */
  askDeleteScope(id: number) {
    const s = this.data()?.job_scopes.find((x) => x.id === id);
    if (!s) return;
    const answers = s.questions.reduce((n, q) => n + q.answer_count, 0);
    const blocked = s.staff_count
      ? `${s.staff_count} staff member(s) are assigned to “${s.name}”. Move them to another job scope before deleting it.`
      : answers
        ? `${answers} survey answer(s) were recorded for the questions of “${s.name}”, so it cannot be deleted without changing past reports.`
        : null;
    this.pending.set({
      kind: 'scope', id, name: s.name, blocked,
      lines: [
        `This will permanently delete the job scope “${s.name}”, its ${s.questions.length} survey question(s) and its required levels in every year.`,
        'Competencies and other job scopes are kept. This cannot be undone.',
      ],
    });
  }

  /** Open the delete confirmation for a competency, or explain why it cannot be deleted. */
  askDeleteComp(id: number) {
    const c = this.data()?.competencies.find((x) => x.id === id);
    if (!c) return;
    const blocked = c.used_by.length
      ? `“${c.name}” is used by ${c.used_by.length} job scope(s): ${c.used_by.join(', ')}. Remove it from them first.`
      : null;
    this.pending.set({
      kind: 'competency', id, name: c.name, blocked,
      lines: [`This will permanently delete the competency “${c.name}”. This cannot be undone.`],
    });
  }

  confirmDelete() {
    const p = this.pending();
    this.pending.set(null);
    if (!p) return;
    if (p.kind === 'scope') {
      this.run(this.api.deleteScope(p.id), () => {
        // update the list now; the reload that follows just confirms it
        const left = (this.data()?.job_scopes ?? []).filter((s) => s.id !== p.id);
        this.data.update((d) => (d ? { ...d, job_scopes: left } : d));
        if (this.scopeId() === p.id) this.scopeId.set(left[0]?.id ?? null);
      });
    } else {
      this.run(this.api.deleteCompetency(p.id), () => {
        this.data.update((d) => (d ? { ...d, competencies: d.competencies.filter((c) => c.id !== p.id) } : d));
        if (this.addComp() === p.id) this.addComp.set(null);
        if (this.qComp() === p.id) this.qComp.set(null);
      });
    }
  }

  addQuestion(scopeId: number) {
    const comp = this.qComp();
    if (comp === null) return;
    this.run(
      this.api.createQuestion({ job_scope_id: scopeId, competency_id: comp, text: this.qText().trim(), is_negative: this.qNeg() }),
      () => { this.qText.set(''); this.qNeg.set(false); },
    );
  }

  startEdit(id: number, text: string) { this.editingId.set(id); this.editText.set(text); }
  saveEdit(id: number) { this.run(this.api.updateQuestion(id, { text: this.editText().trim() }), () => this.editingId.set(null)); }
  removeQuestion(id: number, answerCount: number) {
    const msg = answerCount
      ? `${answerCount} answer(s) from staff exist for this question.\n\nDeleting it will also permanently delete those answers and change past reports. Delete anyway?`
      : 'Delete this question?';
    if (confirm(msg)) this.run(this.api.deleteQuestion(id, answerCount > 0));
  }
}
