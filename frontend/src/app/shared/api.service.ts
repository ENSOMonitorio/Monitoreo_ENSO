import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface MapTabConfig {
  prefix: string;
  title: string;
  has_daily_anim: boolean;
}

export interface ConfigResponse {
  map_tabs: MapTabConfig[];
  auth_enabled: boolean;
}

export interface FiguresResponse {
  prefix: string;
  dates: string[];
  selected_date: string | null;
  image_url: string | null;
  anim_url: string | null;
  composite_anim_url: string | null;
}

export interface IndexRegion {
  key: string;
  label: string;
  color: string;
}

export interface IndicesResponse {
  regions: IndexRegion[];
}

export interface PlotlyFigure {
  data: unknown[];
  layout: Record<string, unknown>;
}

export type IndexFigureResponse = PlotlyFigure | { available: false };

export interface EnsoEvent {
  yr: string;
  title: string;
  stat: string;
  desc: string;
  src: string;
}

export interface Goes19Response {
  anim_url: string | null;
}

export interface StatusResponse {
  text: string;
  is_running: boolean;
}

export interface PipelineStatusResponse {
  running: boolean;
  ok: boolean | null;
  error: string | null;
  last_attempt_ts: string | null;
  last_success: Record<string, string>;
}

export interface PipelineRunResponse {
  started: boolean;
  reason?: string;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) {}

  getConfig(): Observable<ConfigResponse> {
    return this.http.get<ConfigResponse>('/api/config');
  }

  getFigures(prefix: string, date?: string): Observable<FiguresResponse> {
    const params = date ? { date } : undefined;
    return this.http.get<FiguresResponse>(`/api/figures/${prefix}`, { params });
  }

  getIndicesCatalog(): Observable<IndicesResponse> {
    return this.http.get<IndicesResponse>('/api/indices');
  }

  getIndexFigure(region: string): Observable<IndexFigureResponse> {
    return this.http.get<IndexFigureResponse>(`/api/indices/${region}`);
  }

  getHistoricoOni(): Observable<PlotlyFigure> {
    return this.http.get<PlotlyFigure>('/api/historico/oni');
  }

  getHistoricoEventos(): Observable<EnsoEvent[]> {
    return this.http.get<EnsoEvent[]>('/api/historico/eventos');
  }

  getGoes19(): Observable<Goes19Response> {
    return this.http.get<Goes19Response>('/api/goes19');
  }

  getStatus(): Observable<StatusResponse> {
    return this.http.get<StatusResponse>('/api/status');
  }

  getPipelineStatus(): Observable<PipelineStatusResponse> {
    return this.http.get<PipelineStatusResponse>('/api/pipeline/status');
  }

  runPipeline(): Observable<PipelineRunResponse> {
    return this.http.post<PipelineRunResponse>('/api/pipeline/run', {});
  }
}
