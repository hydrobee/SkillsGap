import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { Api } from '../core/api';
import { RatingView, TeamView } from '../core/models';
import { errMsg, initials } from '../core/util';

@Component({
  selector: 'app-rating',
  template: `
    <div class="page-head">
      <div>
        <span class="eyebrow">Supervisor review</span>
        <h1>Rate my team</h1>
        @if (team(); as t) {
          <p class="subtitle">Assessment cycle {{ t.cycle.year }}
            <span class="chip" [class.closed]="!t.cycle.is_open">{{ t.cycle.is_open ? 'Open' : 'Closed' }}</span></p>
        }
      </div>
    </div>
    @if (error()) { <p class="alert error" role="alert">{{ error() }}</p> }

    <div class="split">
      <section class="card">
        <div class="card-head">
          <h2>Direct reports</h2>
          @if (team()?.team?.length) { <span class="chip plain neutral">{{ team()?.team?.length }}</span> }
        </div>
        @if (team()?.team?.length === 0) { <p class="muted">You have no direct reports.</p> }
        <ul class="nav-list">
          @for (m of team()?.team ?? []; track m.staff_id) {
            <li>
              <button type="button" class="list-btn" [class.on]="selected()?.staff?.id === m.staff_id"
                      (click)="open(m.staff_id)">
                <span class="avatar" aria-hidden="true">{{ initials(m.name) }}</span>
                <span class="list-text">
                  <span class="list-title">{{ m.name }}</span>
                  <span class="list-sub">{{ m.rated }} of {{ m.total }} rated</span>
                </span>
                <span class="chip" [class.good]="m.status === 'Complete'">{{ m.status }}</span>
              </button>
            </li>
          }
        </ul>
      </section>

      <section class="card">
        @if (selected(); as s) {
          <div class="card-head">
            <div>
              <h2>{{ s.staff.name }}</h2>
              <p class="muted small">{{ ratedCount() }} of {{ s.questions.length }} statements rated</p>
            </div>
          </div>
          <p class="muted">Answer the same statements {{ s.staff.name }} answered, from your point of view.
            For each one, rate how strongly you agree it describes {{ s.staff.name }}:
            <b>1 (strongly disagree)</b> to <b>5 (strongly agree)</b>. Your answers carry 70% of the final score.</p>
          @if (!s.cycle.is_open) { <p class="alert info">This cycle is closed, so ratings cannot be changed.</p> }
          @for (q of s.questions; track q.question_id; let i = $index) {
            <fieldset class="rate-row" [disabled]="!s.cycle.is_open">
              <legend class="tag">{{ q.competency }}@if (q.required) { · required level {{ q.required }} }</legend>
              <p class="q-text"><span class="q-num">{{ i + 1 }}.</span> “{{ q.text }}”</p>
              <div class="scale" role="radiogroup">
                @for (n of scale; track n) {
                  <label class="pill" [class.on]="ratings()[q.question_id] === n">
                    <input type="radio" [name]="'q' + q.question_id" [value]="n"
                           [checked]="ratings()[q.question_id] === n" (change)="pick(q.question_id, n)" />
                    {{ n }}
                  </label>
                }
              </div>
              <div class="scale-labels"><span>Strongly disagree</span><span>Strongly agree</span></div>
            </fieldset>
          }
          <div class="actions">
            @if (message()) { <span class="ok">{{ message() }}</span> }
            <button class="btn primary" type="button" (click)="save()"
                    [disabled]="!s.cycle.is_open || saving() || ratedCount() === 0">
              {{ saving() ? 'Saving…' : 'Save ratings' }}
            </button>
          </div>
        } @else {
          <div class="empty">
            <div class="empty-icon" aria-hidden="true">👈</div>
            <p>Choose a team member to start rating.</p>
          </div>
        }
      </section>
    </div>
  `,
})
export class RatingPage implements OnInit {
  private api = inject(Api);
  scale = [1, 2, 3, 4, 5];
  team = signal<TeamView | null>(null);
  selected = signal<RatingView | null>(null);
  ratings = signal<Record<number, number | null>>({});
  ratedCount = computed(() => Object.values(this.ratings()).filter((v) => v != null).length);
  saving = signal(false);
  message = signal('');
  error = signal('');

  ngOnInit() { this.loadTeam(); }
  initials = initials;

  private loadTeam() {
    this.api.team().subscribe({ next: (t) => this.team.set(t), error: (e) => this.error.set(errMsg(e)) });
  }

  open(staffId: number) {
    this.message.set('');
    this.error.set('');
    this.api.ratings(staffId).subscribe({
      next: (r) => {
        this.selected.set(r);
        this.ratings.set(Object.fromEntries(r.questions.map((q) => [q.question_id, q.rating])));
      },
      error: (e) => this.error.set(errMsg(e)),
    });
  }

  pick(questionId: number, n: number) {
    this.ratings.update((r) => ({ ...r, [questionId]: n }));
    this.message.set('');
  }

  save() {
    const s = this.selected();
    if (!s) return;
    const payload = Object.entries(this.ratings())
      .filter(([, r]) => r != null)
      .map(([id, r]) => ({ question_id: Number(id), rating: r as number }));
    this.saving.set(true);
    this.error.set('');
    this.api.saveRatings(s.staff.id, s.cycle.id, payload).subscribe({
      next: () => { this.message.set('Saved.'); this.saving.set(false); this.loadTeam(); },
      error: (e) => { this.error.set(errMsg(e)); this.saving.set(false); },
    });
  }
}
