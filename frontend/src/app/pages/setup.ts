import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { Api } from '../core/api';
import { Cycle, SetupOverview } from '../core/models';
import { errMsg } from '../core/util';

@Component({
  selector: 'app-setup',
  imports: [FormsModule],
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
          <button class="btn primary" type="button" (click)="addCycle()">Add cycle</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Year</th><th>Status</th><th class="actions-col"><span class="sr-only">Actions</span></th></tr></thead>
          <tbody>
            @for (c of cycles(); track c.id) {
              <tr>
                <td class="strong">{{ c.year }}</td>
                <td><span class="chip" [class.good]="c.is_open" [class.closed]="!c.is_open">{{ c.is_open ? 'Open' : 'Closed' }}</span></td>
                <td>
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
            <p class="muted small">Pick a job scope to edit its required levels and survey questions.</p>
          </div>
        </div>
        <div class="toolbar">
          <label class="field">Job scope
            <select [ngModel]="scopeId()" (ngModelChange)="scopeId.set($event)">
              @for (s of d.job_scopes; track s.id) { <option [ngValue]="s.id">{{ s.name }}</option> }
            </select>
          </label>
          <span class="spacer"></span>
          <label class="field">New job scope
            <input placeholder="e.g. Data Analyst" [(ngModel)]="newScope" />
          </label>
          <button class="btn" type="button" (click)="addScope()" [disabled]="!newScope().trim()">Add job scope</button>
        </div>

        @if (scope(); as s) {
          <div class="card-section">
            <h3>Required levels for {{ s.name }}</h3>
            <p class="muted small">1 = basic, 5 = expert. HR should review these every year.</p>
            <div class="table-wrap">
              <table>
                <thead><tr><th>Competency</th><th>Required level</th><th class="actions-col"><span class="sr-only">Actions</span></th></tr></thead>
                <tbody>
                  @for (c of s.competencies; track c.competency_id) {
                    <tr>
                      <td class="strong">{{ c.name }}</td>
                      <td>
                        <select class="sm" [attr.aria-label]="'Required level for ' + c.name" [ngModel]="c.required_level"
                                (ngModelChange)="run(api.setLevel(s.id, c.competency_id, $event))">
                          @for (n of levels; track n) { <option [ngValue]="n">{{ n }}</option> }
                        </select>
                      </td>
                      <td>
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
              <label class="field">Add existing competency
                <select [ngModel]="addComp()" (ngModelChange)="addComp.set($event)">
                  <option [ngValue]="null">Select competency…</option>
                  @for (c of availableComps(); track c.id) { <option [ngValue]="c.id">{{ c.name }}</option> }
                </select>
              </label>
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
            <div class="table-wrap">
              <table>
                <thead><tr><th>Competency</th><th>Question</th><th>Wording</th><th class="actions-col"><span class="sr-only">Actions</span></th></tr></thead>
                <tbody>
                  @for (q of s.questions; track q.id) {
                    <tr>
                      <td class="strong nowrap">{{ q.competency }}</td>
                      <td>
                        @if (editingId() === q.id) {
                          <input class="wide" [attr.aria-label]="'Edit question ' + q.id" [(ngModel)]="editText" />
                        } @else { {{ q.text }} }
                      </td>
                      <td class="nowrap">
                        <span class="chip" [class.closed]="q.is_negative">{{ q.is_negative ? 'Negative' : 'Positive' }}</span>
                        @if (q.answer_count) { <div class="muted small">{{ q.answer_count }} answers</div> }
                      </td>
                      <td>
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
  `,
})
export class SetupPage implements OnInit {
  api = inject(Api);
  levels = [1, 2, 3, 4, 5];
  data = signal<SetupOverview | null>(null);
  cycles = signal<Cycle[]>([]);
  scopeId = signal<number | null>(null);
  scope = computed(() => this.data()?.job_scopes.find((s) => s.id === this.scopeId()) ?? null);
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

  refresh() {
    this.api.overview().subscribe({
      next: (d) => {
        this.data.set(d);
        if (!d.job_scopes.some((s) => s.id === this.scopeId())) this.scopeId.set(d.job_scopes[0]?.id ?? null);
      },
      error: (e) => this.error.set(errMsg(e)),
    });
    this.api.listCycles().subscribe({ next: (c) => this.cycles.set(c), error: (e) => this.error.set(errMsg(e)) });
  }

  /** Run any change, then reload the screen; show the server's message if it is refused. */
  run(call: Observable<unknown>, after?: () => void) {
    this.error.set('');
    call.subscribe({
      next: () => { after?.(); this.refresh(); },
      error: (e) => { this.error.set(errMsg(e)); window.scrollTo({ top: 0, behavior: 'smooth' }); this.refresh(); },
    });
  }

  toggleCycle(c: Cycle) { this.run(c.is_open ? this.api.closeCycle(c.id) : this.api.openCycle(c.id)); }
  addCycle() { this.run(this.api.createCycle(Number(this.newYear()))); }
  addScope() { this.run(this.api.createScope(this.newScope().trim()), () => this.newScope.set('')); }
  addNewComp() { this.run(this.api.createCompetency(this.newComp().trim()), () => this.newComp.set('')); }

  attachComp(scopeId: number) {
    const id = this.addComp();
    if (id !== null) this.run(this.api.setLevel(scopeId, id, this.addLevel()), () => this.addComp.set(null));
  }

  removeComp(scopeId: number, compId: number, name: string) {
    if (confirm(`Remove ${name} from this job scope?`)) this.run(this.api.removeLevel(scopeId, compId));
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
      ? `${answerCount} answer(s) from staff or supervisors exist for this question.\n\nDeleting it will also permanently delete those answers and change past reports. Delete anyway?`
      : 'Delete this question?';
    if (confirm(msg)) this.run(this.api.deleteQuestion(id, answerCount > 0));
  }
}
