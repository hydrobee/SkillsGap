import { Component, ElementRef, computed, inject, input, output, signal } from '@angular/core';

export interface SelectItem { id: number; label: string; }

/** A dropdown whose items each have a small delete button on the right.
 *  Clicking the trash icon asks the parent to delete (`remove`); it never selects the item. */
@Component({
  selector: 'app-item-select',
  host: { '(document:click)': 'onDocumentClick($event)' },
  template: `
    <div class="wrap">
      <button type="button" class="trigger" aria-haspopup="listbox" [attr.aria-expanded]="open()"
              [attr.aria-label]="label()" (click)="toggle()" (keydown)="onKey($event)">
        <span class="text" [class.placeholder]="!selected()">{{ selected()?.label ?? placeholder() }}</span>
      </button>
      @if (open()) {
        <ul class="menu" role="listbox" [attr.aria-label]="label()">
          @for (it of items(); track it.id; let i = $index) {
            <li role="option" [attr.aria-selected]="it.id === value()" [class.selected]="it.id === value()"
                [class.active]="i === active()" (mouseenter)="active.set(i)" (click)="choose(it)">
              <span class="name">{{ it.label }}</span>
              @if (deletable()) {
                <button type="button" class="trash" [attr.aria-label]="'Delete ' + it.label" title="Delete"
                        (click)="askDelete($event, it)">
                  <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.44c-.8.1-1.6.22-2.38.36a.75.75 0 10.27 1.48l.2-.04.84 10.5A2.75 2.75 0 007.67 19h4.66a2.75 2.75 0 002.74-2.55l.84-10.5.2.04a.75.75 0 10.27-1.48A41 41 0 0014 4.19v-.44A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.67.03 2.5.08v-.33c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.33C8.33 4.03 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z" clip-rule="evenodd"/></svg>
                </button>
              }
            </li>
          } @empty {
            <li class="empty">Nothing to choose</li>
          }
        </ul>
      }
    </div>
  `,
  styles: [`
    :host { display: block; min-width: 10rem; }
    .wrap { position: relative; }
    .trigger {
      width: 100%; height: var(--control-h); padding: 0 2.25rem 0 .8rem; text-align: left;
      font: inherit; font-size: .925rem; font-weight: 400; letter-spacing: normal; text-transform: none;
      border: 1px solid var(--line-strong); border-radius: var(--radius-sm);
      background-color: var(--card); color: var(--ink); cursor: pointer; box-shadow: var(--shadow-sm);
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='%238b95a9'%3E%3Cpath fill-rule='evenodd' d='M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z'/%3E%3C/svg%3E");
      background-repeat: no-repeat; background-position: right .6rem center; background-size: 1.1rem;
      transition: border-color .15s, box-shadow .15s;
    }
    .trigger:hover { border-color: var(--muted); }
    .trigger:focus-visible { outline: none; border-color: var(--accent); box-shadow: var(--ring); }
    .text { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .placeholder { color: var(--muted); }
    .menu {
      position: absolute; z-index: 30; left: 0; top: calc(100% + .25rem); min-width: 100%; width: max-content; max-width: 22rem;
      max-height: 16rem; overflow-y: auto; margin: 0; padding: .3rem; list-style: none;
      background: var(--card); border: 1px solid var(--line-strong); border-radius: var(--radius-sm); box-shadow: var(--shadow-lg);
      font-size: .925rem; font-weight: 400; letter-spacing: normal; text-transform: none; color: var(--ink);
    }
    li { display: flex; align-items: center; justify-content: space-between; gap: .5rem; min-height: 2.1rem;
         padding: 0 .3rem 0 .6rem; border-radius: 6px; cursor: pointer; }
    li.active { background: var(--bg-subtle); }
    li.selected .name { font-weight: 600; color: var(--accent-soft-ink); }
    li.empty { color: var(--muted); cursor: default; }
    .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .trash {
      display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
      width: 1.75rem; height: 1.75rem; padding: 0; border: 0; border-radius: 6px; background: transparent;
      color: var(--muted); cursor: pointer; opacity: 0; transition: opacity .12s, background .12s, color .12s;
    }
    .trash svg { width: 1rem; height: 1rem; }
    li:hover .trash, li.active .trash, .trash:focus-visible { opacity: 1; }
    .trash:hover, .trash:focus-visible { color: var(--danger); background: var(--danger-soft); outline: none; }
    @media (hover: none) { .trash { opacity: .75; } }
  `],
})
export class ItemSelect {
  private el = inject<ElementRef<HTMLElement>>(ElementRef);

  items = input<SelectItem[]>([]);
  value = input<number | null>(null);
  placeholder = input('Select…');
  label = input('');
  deletable = input(true);
  valueChange = output<number | null>();
  remove = output<number>();

  open = signal(false);
  active = signal(-1);
  selected = computed(() => this.items().find((i) => i.id === this.value()) ?? null);

  toggle() {
    this.open.update((o) => !o);
    if (this.open()) this.active.set(this.items().findIndex((i) => i.id === this.value()));
  }
  choose(it: SelectItem) { this.valueChange.emit(it.id); this.open.set(false); }

  /** Delete icon: ask the parent to confirm and delete. Must not select the row or keep the menu open. */
  askDelete(e: Event, it: SelectItem) {
    e.stopPropagation();
    e.preventDefault();
    this.open.set(false);
    this.remove.emit(it.id);
  }

  onKey(e: KeyboardEvent) {
    const n = this.items().length;
    if (e.key === 'Escape') { this.open.set(false); return; }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (!this.open()) { this.toggle(); return; }
      this.active.update((a) => (n ? (a + (e.key === 'ArrowDown' ? 1 : -1) + n) % n : -1));
    } else if ((e.key === 'Enter' || e.key === ' ') && this.open() && this.active() >= 0) {
      e.preventDefault();
      this.choose(this.items()[this.active()]);
    }
  }

  onDocumentClick(e: Event) {
    if (this.open() && !this.el.nativeElement.contains(e.target as Node)) this.open.set(false);
  }
}
