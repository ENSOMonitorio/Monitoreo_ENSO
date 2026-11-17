import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, computed, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ApiService } from './shared/api.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App implements OnInit, OnDestroy {
  statusText = signal('');
  isRunning = signal(false);
  authEnabled = signal(false);

  // El backend antepone "⚠" cuando la última corrida del pipeline falló
  // (ver _status_text en backend/app/app.py).
  statusOk = computed(() => !this.statusText().startsWith('⚠'));
  // El ícono ya marca la advertencia; el texto visible no repite el "⚠".
  statusLabel = computed(() => this.statusText().replace(/^⚠\s*/, ''));

  private pollTimer?: ReturnType<typeof setInterval>;
  // El proceso del pipeline tarda unos segundos (imports pesados) en escribir
  // su lock: hasta verlo corriendo, o pasado este margen, no se da por
  // terminado. Sin esto el botón se rehabilitaba al instante y un segundo
  // clic lanzaba otra corrida en paralelo (dos descargas sobre el mismo .nc).
  private static readonly STARTUP_GRACE_MS = 20000;
  private sawRunning = false;
  private pollStartedAt = 0;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getConfig().subscribe((cfg) => {
      this.authEnabled.set(cfg.auth_enabled);
    });
    this.refreshStatus();
  }

  ngOnDestroy(): void {
    clearInterval(this.pollTimer);
  }

  onRefreshClick(): void {
    if (this.isRunning()) return;
    this.isRunning.set(true);
    // 202 = arrancó; 409 = ya había una corrida. En ambos casos se espera a
    // que termine.
    this.api.runPipeline().subscribe({
      next: () => this.startPolling(false),
      error: () => this.startPolling(false),
    });
  }

  private refreshStatus(): void {
    this.api.getStatus().subscribe((res) => {
      this.statusText.set(res.text);
      this.isRunning.set(res.is_running);
      if (res.is_running) this.startPolling(true);
    });
  }

  private startPolling(alreadyRunning: boolean): void {
    if (this.pollTimer) return;
    this.sawRunning = alreadyRunning;
    this.pollStartedAt = Date.now();
    this.pollTimer = setInterval(() => this.pollPipeline(), 4000);
  }

  private pollPipeline(): void {
    this.api.getPipelineStatus().subscribe((res) => {
      if (res.running) {
        this.sawRunning = true;
        return;
      }
      const starting = !this.sawRunning && Date.now() - this.pollStartedAt < App.STARTUP_GRACE_MS;
      if (starting) return;
      clearInterval(this.pollTimer);
      this.pollTimer = undefined;
      this.refreshStatus();
    });
  }
}
