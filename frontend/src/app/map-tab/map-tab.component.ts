import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ApiService, FiguresResponse, Goes19Response, WalkerResponse } from '../shared/api.service';
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
  // T observada/anomalía) se puede ver la App Interactiva de Boyas TAO (Dash).
  seaVariablesView = signal<'composite' | 'dash_boyas'>('composite');

  // Dentro de "Atmósfera": viento 850 hPa (<app-date-player>, trae sus
  // propios datos) y GOES-19, siempre juntos (sin toggle).
  goesData = signal<Goes19Response | null>(null);
  walkerData = signal<WalkerResponse | null>(null);
  readonly walkerBands = [
    { key: '5S-5N', label: '5°S–5°N' },
    { key: '2S-2N', label: '2°S–2°N' },
    { key: '0', label: '0°' },
  ];
  walkerBand = signal<string>('5S-5N');

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
        this.api.getGoes19().subscribe((res) => this.goesData.set(res));
        this.api.getWalker(this.walkerBand()).subscribe((res) => this.walkerData.set(res));
        this.api.getFigures('slp').subscribe((res) => this.slpData.set(res));
      }
    });
  }

  onWalkerBandChange(band: string): void {
    this.walkerBand.set(band);
    this.api.getWalker(band).subscribe((res) => this.walkerData.set(res));
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

  setSeaVariablesView(view: 'composite' | 'dash_boyas'): void {
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
