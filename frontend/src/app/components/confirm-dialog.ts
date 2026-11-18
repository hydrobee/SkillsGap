import { AfterViewInit, Component, ElementRef, input, output, viewChild } from '@angular/core';

/** A modal confirmation. The message goes inside the element. With `blocked` set, only a Close button is shown. */
@Component({
  selector: 'app-confirm-dialog',
  host: { '(document:keydown.escape)': 'cancel.emit()' },
  template: `
    <div class="backdrop" (click)="cancel.emit()">
      <div class="dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title"
           (click)="$event.stopPropagation()">
        <h2 id="confirm-title">{{ title() }}</h2>
        <div class="body"><ng-content /></div>
        <div class="actions">
          <button #first type="button" class="btn" (click)="cancel.emit()">{{ blocked() ? 'Close' : 'Cancel' }}</button>
          @if (!blocked()) {
            <button type="button" class="btn confirm" (click)="confirm.emit()">{{ confirmLabel() }}</button>
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    .backdrop { position: fixed; inset: 0; z-index: 100; display: grid; place-items: center; padding: 1rem;
                background: rgba(15, 23, 42, .5); }
    .dialog { width: min(28rem, 100%); background: var(--card); color: var(--ink); border: 1px solid var(--line);
              border-radius: var(--radius-lg); box-shadow: var(--shadow-lg); padding: 1.5rem; }
    h2 { margin: 0 0 .75rem; font-size: 1.15rem; }
    .body { color: var(--ink-2); font-size: .95rem; line-height: 1.5; }
    .actions { display: flex; justify-content: flex-end; gap: .5rem; margin-top: 1.5rem; }
    .btn.confirm { background: var(--danger); border-color: var(--danger); color: #fff; }
    .btn.confirm:hover:not(:disabled) { background: var(--danger); filter: brightness(.92); }
  `],
})
export class ConfirmDialog implements AfterViewInit {
  title = input('Are you sure?');
  confirmLabel = input('Delete');
  blocked = input(false);
  confirm = output<void>();
  cancel = output<void>();
  private first = viewChild<ElementRef<HTMLButtonElement>>('first');

  ngAfterViewInit() { this.first()?.nativeElement.focus(); }   // safe default: Cancel
}
