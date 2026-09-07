import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { ApiService, IndexRegion, PlotlyFigure } from '../shared/api.service';
import { PlotlyChartComponent } from '../shared/plotly-chart.component';

interface RegionCard extends IndexRegion {
  figure: PlotlyFigure | null;
  available: boolean;
}

// Mismas 2 regiones que mostraba la pestaña "Índices" en Dash — el CSV/API
// ya trae las 4 (nino12/nino34/nino3/nino4) por si se quiere ampliar luego.
const SHOWN_REGIONS = ['nino12', 'nino34'];

@Component({
  selector: 'app-indices',
  standalone: true,
  imports: [CommonModule, PlotlyChartComponent],
  templateUrl: './indices.component.html',
})
export class IndicesComponent implements OnInit {
  cards: RegionCard[] = [];
  loading = true;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getIndicesCatalog().subscribe((res) => {
      this.cards = res.regions
        .filter((region) => SHOWN_REGIONS.includes(region.key))
        .map((region) => ({ ...region, figure: null, available: true }));
      this.loading = false;

      for (const card of this.cards) {
        this.api.getIndexFigure(card.key).subscribe((fig) => {
          if ('available' in fig && fig.available === false) {
            card.available = false;
          } else {
            card.figure = fig as PlotlyFigure;
          }
        });
      }
    });
  }
}
