import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ApiService, MapTabConfig } from './shared/api.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App implements OnInit, OnDestroy {
  mapTabs = signal<MapTabConfig[]>([]);
  clock = signal('');
  statusText = signal('');
  isRunning = signal(false);
  authEnabled = signal(false);

  private clockTimer?: ReturnType<typeof setInterval>;
  private pollTimer?: ReturnType<typeof setInterval>;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getConfig().subscribe((cfg) => {
      this.mapTabs.set(cfg.map_tabs);
      this.authEnabled.set(cfg.auth_enabled);
    });
    this.refreshStatus();
    this.tickClock();
    this.clockTimer = setInterval(() => this.tickClock(), 1000);
  }

  ngOnDestroy(): void {
    clearInterval(this.clockTimer);
    clearInterval(this.pollTimer);
  }

  onRefreshClick(): void {
    this.api.runPipeline().subscribe(() => this.refreshStatus());
  }

  private tickClock(): void {
    this.clock.set(
      new Date().toLocaleString('es-PE', {
        timeZone: 'America/Lima',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      }),
    );
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
