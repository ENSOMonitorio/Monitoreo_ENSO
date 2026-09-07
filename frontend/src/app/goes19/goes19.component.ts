import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { ApiService } from '../shared/api.service';

@Component({
  selector: 'app-goes19',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './goes19.component.html',
})
export class Goes19Component implements OnInit {
  animUrl = signal<string | null>(null);
  loading = signal(true);

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getGoes19().subscribe((res) => {
      this.animUrl.set(res.anim_url);
      this.loading.set(false);
    });
  }
}
