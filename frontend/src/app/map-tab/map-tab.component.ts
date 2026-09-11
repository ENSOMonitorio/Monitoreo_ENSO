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

  constructor(
    private route: ActivatedRoute,
    private api: ApiService,
  ) {}

  ngOnInit(): void {
    this.route.data.subscribe((routeData) => {
      this.prefix = routeData['prefix'];
      this.title = routeData['title'];
      this.load();
    });
  }

  load(date?: string): void {
    this.loading.set(true);
    this.api.getFigures(this.prefix, date).subscribe((res) => {
      this.data.set(res);
      this.loading.set(false);
    });
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
