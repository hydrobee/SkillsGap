import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { Api } from '../core/api';
import { SurveyView } from '../core/models';
import { errMsg } from '../core/util';

@Component({
  selector: 'app-survey',
  template: `
    <div class="page-head">
      <div>
        <span class="eyebrow">Self assessment</span>
        <h1>My survey</h1>
        @if (view(); as v) {
          <p class="subtitle">Assessment cycle {{ v.cycle.year }}
            <span class="chip" [class.closed]="!v.cycle.is_open">{{ v.cycle.is_open ? 'Open' : 'Closed' }}</span></p>
        }
      </div>
      @if (view(); as v) {
        <div class="progress-wrap">
          <div class="progress-label"><span>Progress</span><span>{{ answeredCount() }} / {{ v.total }} answered</span></div>
          <div class="progress"><span [style.width.%]="v.total ? (answeredCount() / v.total) * 100 : 0"></span></div>
        </div>
      }
    </div>

    @if (error()) { <p class="alert error" role="alert">{{ error() }}</p> }

    @if (view(); as v) {
      @if (!v.cycle.is_open) {
        <p class="alert info">This assessment cycle is closed. You can still see your answers, but not change them.</p>
      } @else {
        <p class="muted">Rate each statement from <b>1 (strongly disagree)</b> to <b>5 (strongly agree)</b>.
          You can change your answers until the cycle closes.</p>
      }

      @for (q of v.questions; track q.id; let i = $index) {
        <fieldset class="card question" [disabled]="!v.cycle.is_open">
          <legend class="tag">{{ q.competency }}</legend>
          <p class="q-text"><span class="q-num">{{ i + 1 }}.</span> {{ q.text }}</p>
          <div class="scale" role="radiogroup">
            @for (n of scale; track n) {
              <label class="pill" [class.on]="answers()[q.id] === n">
                <input type="radio" [name]="'q' + q.id" [value]="n" [checked]="answers()[q.id] === n"
                       (change)="pick(q.id, n)" />
                {{ n }}
              </label>
            }
          </div>
          <div class="scale-labels"><span>Strongly disagree</span><span>Strongly agree</span></div>
        </fieldset>
      }

      <div class="sticky-actions no-print">
        <div class="sticky-status">
          <span>{{ answeredCount() }} of {{ v.total }} answered</span>
          @if (message()) { <span class="ok">{{ message() }}</span> }
        </div>
        <button class="btn primary" type="button" (click)="save()"
                [disabled]="!v.cycle.is_open || saving() || answeredCount() === 0">
          {{ saving() ? 'Saving…' : 'Save answers' }}
        </button>
      </div>
    }
  `,
})
export class SurveyPage implements OnInit {
  private api = inject(Api);
  scale = [1, 2, 3, 4, 5];
  view = signal<SurveyView | null>(null);
  answers = signal<Record<number, number | null>>({});
  answeredCount = computed(() => Object.values(this.answers()).filter((v) => v != null).length);
  saving = signal(false);
  message = signal('');
  error = signal('');

  ngOnInit() {
    this.api.survey().subscribe({
      next: (v) => {
        this.view.set(v);
        this.answers.set(Object.fromEntries(v.questions.map((q) => [q.id, q.answer])));
      },
      error: (e) => this.error.set(errMsg(e)),
    });
  }

  pick(id: number, n: number) {
    this.answers.update((a) => ({ ...a, [id]: n }));
    this.message.set('');
  }

  save() {
    const v = this.view();
    if (!v) return;
    const payload = Object.entries(this.answers())
      .filter(([, a]) => a != null)
      .map(([id, a]) => ({ question_id: Number(id), answer: a as number }));
    this.saving.set(true);
    this.error.set('');
    this.api.saveSurvey(v.cycle.id, payload).subscribe({
      next: () => { this.message.set('Saved.'); this.saving.set(false); },
      error: (e) => { this.error.set(errMsg(e)); this.saving.set(false); },
    });
  }
}
