import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnChanges, OnDestroy, Output, SimpleChanges, signal } from '@angular/core';
import { ApiService } from '../shared/api.service';

export interface PlayerBandOption {
  key: string;
  label: string;
}

/** Reproductor de la serie diaria de un prefix (tsm, anom, viento, slp, walker):
 * play/pausa + slider para recorrer todas las fechas disponibles, no solo
 * los últimos 15 días del GIF fijo. Reusa /api/figures/<prefix>?date=...&band=... —
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
  /** Alto fijo (chart-figure--fixed-height) — para paneles donde esta
   * imagen se compara al lado de otra con distinta relación ancho/alto
   * (p.ej. Viento vs. GOES-19 en Atmósfera). */
  @Input() fixedHeight = false;
  @Input() bands: PlayerBandOption[] = [];
  @Input() initialBand = '5S-5N';
  @Input() hasTimeseriesToggle = false;
  @Output() bandChange = new EventEmitter<string>();
  @Output() timeseriesToggle = new EventEmitter<boolean>();

  dates = signal<string[]>([]);
  index = signal(0);
  imageUrl = signal<string | null>(null);
  playing = signal(false);
  loading = signal(true);
  speed = signal(1);
  currentBand = signal<string>('5S-5N');
  timeseriesActive = signal<boolean>(false);
  readonly speedOptions = [0.5, 1, 2, 4, 8];

  private timer?: ReturnType<typeof setInterval>;
  private readonly baseFrameMs = 450;

  constructor(private api: ApiService) {}

  toggleTimeseries(): void {
    const next = !this.timeseriesActive();
    this.timeseriesActive.set(next);
    this.timeseriesToggle.emit(next);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['initialBand'] && this.initialBand) {
      if (this.currentBand() !== this.initialBand) {
        this.currentBand.set(this.initialBand);
        this.loadCurrent();
      }
    }
    if (changes['prefix'] || changes['bands']) {
      this.fetchInitial();
    }
  }

  private fetchInitial(): void {
    this.pause();
    this.loading.set(true);
    const band = this.bands.length ? this.currentBand() : undefined;
    this.api.getFigures(this.prefix, undefined, band).subscribe((res) => {
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
    this.startTimer();
  }

  pause(): void {
    this.playing.set(false);
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = undefined;
    }
  }

  onBandChange(event: Event): void {
    const band = (event.target as HTMLSelectElement).value;
    this.currentBand.set(band);
    this.bandChange.emit(band);
    this.loadCurrent();
  }

  onSpeedChange(event: Event): void {
    this.speed.set(Number((event.target as HTMLSelectElement).value));
    // Si ya estaba reproduciendo, reinicia el intervalo con la nueva
    // velocidad sin tocar el frame en el que está parado.
    if (this.playing()) {
      if (this.timer) clearInterval(this.timer);
      this.startTimer();
    }
  }

  private startTimer(): void {
    this.timer = setInterval(() => {
      if (this.index() >= this.dates().length - 1) {
        this.pause();
        return;
      }
      this.index.set(this.index() + 1);
      this.loadCurrent();
    }, this.baseFrameMs / this.speed());
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
    const band = this.bands.length ? this.currentBand() : undefined;
    this.api.getFigures(this.prefix, date, band).subscribe((res) => this.imageUrl.set(res.image_url));
  }
}
