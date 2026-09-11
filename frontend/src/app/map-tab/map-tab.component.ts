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

  // Solo para prefix === 'subsurf': 3 vistas de nivel superior.
  topView = signal<'superficie' | 'mar' | 'atmosfera'>('mar');

  // Dentro de "Ver superficie": datos reales de TSM/Anomalía TSM (misma
  // fuente que las pestañas TSM y Anomalía de TSM), en vez de un mapa vacío
  // de referencia.
  surfaceView = signal<'tsm' | 'anom'>('tsm');
  tsmData = signal<FiguresResponse | null>(null);
  anomData = signal<FiguresResponse | null>(null);

  // Dentro de "Ver mapa de variables del mar": además del composite (mapa +
  // T observada/anomalía) se puede ver Hovmöller 3.4 y 1+2 — mismos datos
  // que esas pestañas.
  seaVariablesView = signal<'composite' | 'hov34' | 'hov12'>('composite');
  hov34Data = signal<FiguresResponse | null>(null);
  hov12Data = signal<FiguresResponse | null>(null);

  // Dentro de "Atmósfera": viento 850 hPa y presión a nivel del mar (SLP) —
  // mismos datos que esas pestañas.
  atmosferaView = signal<'viento' | 'slp'>('viento');
  vientoData = signal<FiguresResponse | null>(null);
  slpData = signal<FiguresResponse | null>(null);

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
        this.api.getFigures('hovmoller_nino34').subscribe((res) => this.hov34Data.set(res));
        this.api.getFigures('hovmoller_nino12').subscribe((res) => this.hov12Data.set(res));
        this.api.getFigures('viento').subscribe((res) => this.vientoData.set(res));
        this.api.getFigures('slp').subscribe((res) => this.slpData.set(res));
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

  setSeaVariablesView(view: 'composite' | 'hov34' | 'hov12'): void {
    this.seaVariablesView.set(view);
  }

  setAtmosferaView(view: 'viento' | 'slp'): void {
    this.atmosferaView.set(view);
  }

  onDateChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.load(value);
  }

  setTopView(view: 'superficie' | 'mar' | 'atmosfera'): void {
    this.topView.set(view);
  }
}
