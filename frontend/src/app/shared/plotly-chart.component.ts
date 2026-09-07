import {
  AfterViewInit,
  Component,
  ElementRef,
  Input,
  OnChanges,
  OnDestroy,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import * as Plotly from 'plotly.js-basic-dist-min';
import { PlotlyFigure } from './api.service';

@Component({
  selector: 'app-plotly-chart',
  standalone: true,
  template: `<div #chart class="plotly-chart"></div>`,
  styles: [
    `
      :host {
        display: block;
      }
      .plotly-chart {
        width: 100%;
      }
    `,
  ],
})
export class PlotlyChartComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input() figure: PlotlyFigure | null = null;
  @ViewChild('chart', { static: true }) chartRef!: ElementRef<HTMLDivElement>;

  private rendered = false;

  ngAfterViewInit(): void {
    this.render();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['figure'] && this.chartRef) {
      this.render();
    }
  }

  ngOnDestroy(): void {
    if (this.rendered) {
      Plotly.purge(this.chartRef.nativeElement);
    }
  }

  private render(): void {
    if (!this.figure) {
      return;
    }
    const config = { displayModeBar: false, responsive: true };
    if (this.rendered) {
      Plotly.react(this.chartRef.nativeElement, this.figure.data as never, this.figure.layout, config);
    } else {
      Plotly.newPlot(this.chartRef.nativeElement, this.figure.data as never, this.figure.layout, config);
      this.rendered = true;
    }
  }
}
