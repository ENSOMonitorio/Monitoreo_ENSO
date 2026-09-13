import { Routes } from '@angular/router';
import { Goes19Component } from './goes19/goes19.component';
import { HistoricoComponent } from './historico/historico.component';
import { IndicesComponent } from './indices/indices.component';
import { MapTabComponent } from './map-tab/map-tab.component';

// Espeja MAP_TABS de backend/app/app.py — las tabs prácticamente nunca
// cambian, así que se acepta esta pequeña duplicación en vez de resolver
// rutas dinámicamente contra /api/config.
export const MAP_TABS: { prefix: string; title: string }[] = [
  { prefix: 'tsm', title: 'Temperatura superficial del mar (TSM)' },
  { prefix: 'anom', title: 'Anomalía de TSM' },
  { prefix: 'viento', title: 'Viento zonal y vectores a 850 hPa' },
  { prefix: 'slp', title: 'Presión a nivel del mar (SLP)' },
  { prefix: 'hovmoller_nino34', title: 'Hovmöller — Niño 3.4' },
  { prefix: 'hovmoller_nino12', title: 'Hovmöller — Niño 1+2' },
  { prefix: 'subsurf', title: 'Subsuperficie — Onda Kelvin' },
];

export const routes: Routes = [
  // Subsuperficie es ahora la única vista de la app — su columna de
  // botones verticales (Ver superficie / Ver mapa de variables del mar /
  // Atmósfera / Otros) cubre todo lo que antes eran pestañas separadas
  // (TSM, Anomalía, Viento, SLP, Hovmöller, GOES-19, Índices, Histórico).
  // Esas rutas se mantienen abajo por si alguien entra por URL directa,
  // pero ya no hay nav que apunte a ellas.
  { path: '', redirectTo: 'subsurf', pathMatch: 'full' },
  ...MAP_TABS.map((tab) => ({
    path: tab.prefix,
    component: MapTabComponent,
    data: { prefix: tab.prefix, title: tab.title },
  })),
  { path: 'goes19', component: Goes19Component },
  { path: 'indices', component: IndicesComponent },
  { path: 'historico', component: HistoricoComponent },
];
