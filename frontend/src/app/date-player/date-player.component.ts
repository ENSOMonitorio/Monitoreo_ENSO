import { CommonModule } from '@angular/common';
import { Component, Input, OnChanges, OnDestroy, SimpleChanges, signal } from '@angular/core';
import { ApiService } from '../shared/api.service';

/** Reproductor de la serie diaria de un prefix (tsm, anom, viento, slp):
 * play/pausa + slider para recorrer todas las fechas disponibles, no solo
 * los últimos 15 días del GIF fijo. Reusa /api/figures/<prefix>?date=... —
 * el mismo endpoint que ya usa el selector de fecha de las pestañas
 * normales — así que no hace falta nada nuevo del lado del backend. */
@Component({
  selector: 'app-date-player',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './date-player.component.html',
})
export class DatePlayerComponent implements OnChanges, OnDestroy {
  @Input() prefix!: string;
  @Input() alt = '';

  dates = signal<string[]>([]);
  index = signal(0);
  imageUrl = signal<string | null>(null);
  playing = signal(false);
  loading = signal(true);

  private timer?: ReturnType<typeof setInterval>;
  private readonly frameMs = 450;

  constructor(private api: ApiService) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['prefix']) {
      this.pause();
      this.loading.set(true);
      this.api.getFigures(this.prefix).subscribe((res) => {
        // /api/figures/<prefix> devuelve las fechas más nuevas primero (para
        // el <select> de las pestañas normales) — acá se invierte para que
        // el slider lea de izquierda (inicio de año) a derecha (hoy), como
        // una línea de tiempo normal.
        const chronological = [...res.dates].reverse();
        this.dates.set(chronological);
        this.index.set(chronological.length - 1);
        this.imageUrl.set(res.image_url);
        this.loading.set(false);
      });
    }
  }

  ngOnDestroy(): void {
    this.pause();
  }

  get currentDate(): string {
    return this.dates()[this.index()] ?? '';
  }

  toggle(): void {
    if (this.playing()) {
      this.pause();
    } else {
      this.play();
    }
  }

  play(): void {
    if (this.dates().length < 2) return;
    // Si ya está en el último frame, un nuevo play arranca de nuevo desde
    // el principio en vez de no hacer nada.
    if (this.index() >= this.dates().length - 1) {
      this.index.set(0);
      this.loadCurrent();
    }
    this.playing.set(true);
    this.timer = setInterval(() => {
      if (this.index() >= this.dates().length - 1) {
        this.pause();
        return;
      }
      this.index.set(this.index() + 1);
      this.loadCurrent();
    }, this.frameMs);
  }

  pause(): void {
    this.playing.set(false);
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = undefined;
    }
  }

  onSlider(event: Event): void {
    this.pause();
    this.index.set(Number((event.target as HTMLInputElement).value));
    this.loadCurrent();
  }

  step(delta: number): void {
    this.pause();
    const next = Math.min(Math.max(this.index() + delta, 0), this.dates().length - 1);
    this.index.set(next);
    this.loadCurrent();
  }

  goToStart(): void {
    this.pause();
    this.index.set(0);
    this.loadCurrent();
  }

  goToLatest(): void {
    this.pause();
    this.index.set(this.dates().length - 1);
    this.loadCurrent();
  }

  private loadCurrent(): void {
    const date = this.currentDate;
    if (!date) return;
    this.api.getFigures(this.prefix, date).subscribe((res) => this.imageUrl.set(res.image_url));
  }
}
