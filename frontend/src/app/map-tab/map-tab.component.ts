import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ApiService, FiguresResponse } from '../shared/api.service';

@Component({
  selector: 'app-map-tab',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './map-tab.component.html',
})
export class MapTabComponent implements OnInit {
  prefix = '';
  title = '';
  data = signal<FiguresResponse | null>(null);
  loading = signal(true);
  showFlatMap = signal(false);

  // Solo para prefix === 'subsurf': datos reales de TSM/Anomalía TSM (misma
  // fuente que las pestañas TSM y Anomalía de TSM) para mostrar dentro de
  // "Ver superficie", en vez de un mapa vacío de referencia.
  surfaceView = signal<'tsm' | 'anom'>('tsm');
  tsmData = signal<FiguresResponse | null>(null);
  anomData = signal<FiguresResponse | null>(null);

  constructor(
    private route: ActivatedRoute,
    private api: ApiService,
  ) {}

  ngOnInit(): void {
    this.route.data.subscribe((routeData) => {
      this.prefix = routeData['prefix'];
      this.title = routeData['title'];
      this.load();
      if (this.prefix === 'subsurf') {
        this.api.getFigures('tsm').subscribe((res) => this.tsmData.set(res));
        this.api.getFigures('anom').subscribe((res) => this.anomData.set(res));
      }
    });
  }

  load(date?: string): void {
    this.loading.set(true);
    this.api.getFigures(this.prefix, date).subscribe((res) => {
      this.data.set(res);
      this.loading.set(false);
    });
  }

  setSurfaceView(view: 'tsm' | 'anom'): void {
    this.surfaceView.set(view);
  }

  onDateChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.load(value);
  }

  showSurfaceView(): void {
    this.showFlatMap.set(true);
  }

  showSeaVariablesView(): void {
    this.showFlatMap.set(false);
  }
}
