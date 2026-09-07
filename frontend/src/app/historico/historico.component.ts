import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { ApiService, EnsoEvent, PlotlyFigure } from '../shared/api.service';
import { EventCardComponent } from '../event-card/event-card.component';
import { PlotlyChartComponent } from '../shared/plotly-chart.component';

@Component({
  selector: 'app-historico',
  standalone: true,
  imports: [CommonModule, PlotlyChartComponent, EventCardComponent],
  templateUrl: './historico.component.html',
})
export class HistoricoComponent implements OnInit {
  oniFigure = signal<PlotlyFigure | null>(null);
  events = signal<EnsoEvent[]>([]);

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getHistoricoOni().subscribe((fig) => this.oniFigure.set(fig));
    this.api.getHistoricoEventos().subscribe((events) => this.events.set(events));
  }
}
