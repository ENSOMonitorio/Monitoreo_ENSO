import { Component, Input } from '@angular/core';
import { EnsoEvent } from '../shared/api.service';

@Component({
  selector: 'app-event-card',
  standalone: true,
  templateUrl: './event-card.component.html',
})
export class EventCardComponent {
  @Input({ required: true }) event!: EnsoEvent;
}
