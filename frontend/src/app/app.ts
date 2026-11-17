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
    this.api.runPipeline().subscribe(() => this.refreshStatus());
  }

  private refreshStatus(): void {
    this.api.getStatus().subscribe((res) => {
      this.statusText.set(res.text);
      this.isRunning.set(res.is_running);
      if (res.is_running && !this.pollTimer) {
        this.pollTimer = setInterval(() => this.pollPipeline(), 4000);
      }
    });
  }

  private pollPipeline(): void {
    this.api.getPipelineStatus().subscribe((res) => {
      if (!res.running) {
        clearInterval(this.pollTimer);
        this.pollTimer = undefined;
        this.refreshStatus();
      }
    });
  }
}
