import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ApiService, FiguresResponse, Goes19Response } from '../shared/api.service';
import { HistoricoComponent } from '../historico/historico.component';
import { IndicesComponent } from '../indices/indices.component';
import { DatePlayerComponent } from '../date-player/date-player.component';

@Component({
  selector: 'app-map-tab',
  standalone: true,
  imports: [CommonModule, HistoricoComponent, IndicesComponent, DatePlayerComponent],
  templateUrl: './map-tab.component.html',
})
export class MapTabComponent implements OnInit {
  prefix = '';
  title = '';
  data = signal<FiguresResponse | null>(null);
  loading = signal(true);

  // Solo para prefix === 'subsurf': 4 vistas de nivel superior.
  topView = signal<'superficie' | 'mar' | 'atmosfera' | 'otros'>('mar');

  // Dentro de "Ver superficie": <app-date-player> trae sus propios datos
  // (toda la serie diaria, no solo la fecha más reciente).
  surfaceView = signal<'tsm' | 'anom'>('tsm');

  // Dentro de "Ver mapa de variables del mar": además del composite (mapa +
  // T observada/anomalía) se puede ver Hovmöller 3.4 y 1+2 — mismos datos
  // que esas pestañas.
  seaVariablesView = signal<'composite' | 'hov34' | 'hov12'>('composite');
  hov34Data = signal<FiguresResponse | null>(null);
  hov12Data = signal<FiguresResponse | null>(null);

  // Dentro de "Atmósfera": viento 850 hPa y GOES-19, siempre juntos (sin
  // toggle) — mismos datos que esas pestañas.
  vientoData = signal<FiguresResponse | null>(null);
  goesData = signal<Goes19Response | null>(null);

  // Dentro de "Otros": todo junto en una sola vista (sin sub-botones) —
  // gatillador/inhibidor del fenómeno (APSO, ZCIT, etc. — proyección de la
  // línea de investigación, por ahora con SLP como proxy disponible), el
  // contexto histórico ENOS (reusa <app-historico>) y los índices Niño
  // 1+2/3.4 (reusa <app-indices>) — mismos componentes que sus pestañas
  // propias.
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
        this.api.getFigures('hovmoller_nino34').subscribe((res) => this.hov34Data.set(res));
        this.api.getFigures('hovmoller_nino12').subscribe((res) => this.hov12Data.set(res));
        this.api.getFigures('viento').subscribe((res) => this.vientoData.set(res));
        this.api.getGoes19().subscribe((res) => this.goesData.set(res));
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

  onDateChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.load(value);
  }

  setTopView(view: 'superficie' | 'mar' | 'atmosfera' | 'otros'): void {
    this.topView.set(view);
  }
}
