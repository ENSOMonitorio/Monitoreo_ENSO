import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { App } from './app';
import { routes } from './app.routes';
import { ConfigResponse, StatusResponse } from './shared/api.service';

describe('App', () => {
  let fixture: ComponentFixture<App> | undefined;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter(routes), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
  });

  // Limpia el setInterval del sondeo cuando el pipeline figura corriendo.
  afterEach(() => fixture?.destroy());

  function render(config: ConfigResponse, status: StatusResponse): HTMLElement {
    fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/config').flush(config);
    http.expectOne('/api/status').flush(status);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  const noAuth: ConfigResponse = { map_tabs: [], auth_enabled: false };
  const idle = (text: string): StatusResponse => ({ text, is_running: false });

  it('should create the app', () => {
    fixture = TestBed.createComponent(App);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('muestra la marca', () => {
    const el = render(noAuth, idle('Actualizado 06 nov · 07:31'));
    expect(el.querySelector('.brand-name')?.textContent?.trim()).toBe('Monitor ENSO');
    expect(el.querySelector('.brand-sub')?.textContent?.trim()).toBe('Perú · Pacífico tropical');
    expect(el.querySelector('.live-badge')).toBeNull();
    expect(el.querySelector('.header-time')).toBeNull();
  });

  it('muestra el estado con el texto completo en title', () => {
    const el = render(noAuth, idle('Actualizado 06 nov · 07:31'));
    const st = el.querySelector('.header-status')!;
    expect(st.textContent).toContain('Actualizado 06 nov · 07:31');
    expect(st.getAttribute('title')).toBe('Actualizado 06 nov · 07:31');
    expect(st.classList.contains('header-status--warn')).toBe(false);
  });

  it('marca advertencia cuando falló la última actualización', () => {
    const txt = '⚠ Falló la última actualización (sst_mean.nc corrupto) — Actualizado 05 nov · 07:30';
    const el = render(noAuth, idle(txt));
    expect(el.querySelector('.header-status')!.classList.contains('header-status--warn')).toBe(true);
  });

  it('deshabilita el botón mientras corre el pipeline', () => {
    const el = render(noAuth, { text: 'x', is_running: true });
    const btn = el.querySelector('button.header-refresh') as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    expect(btn.textContent?.trim()).toBe('Actualizando…');
  });

  it('habilita Actualizar datos cuando el pipeline está quieto', () => {
    const el = render(noAuth, idle('x'));
    const btn = el.querySelector('button.header-refresh') as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
    expect(btn.textContent?.trim()).toBe('Actualizar datos');
  });

  describe('botón Actualizar datos', () => {
    const pipe = (running: boolean) => ({
      running, ok: true, error: null, last_attempt_ts: null, last_success: {},
    });

    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    function click(el: HTMLElement): HTMLButtonElement {
      const btn = el.querySelector('button.header-refresh') as HTMLButtonElement;
      btn.click();
      fixture!.detectChanges();
      return btn;
    }

    it('se deshabilita apenas se hace clic, antes de que responda el servidor', () => {
      const el = render(noAuth, idle('x'));
      const btn = click(el);
      expect(btn.disabled).toBe(true);
      expect(btn.textContent?.trim()).toBe('Actualizando…');
      TestBed.inject(HttpTestingController).expectOne('/api/pipeline/run');
    });

    it('sigue en Actualizando… mientras el pipeline todavía no escribió su lock', () => {
      const el = render(noAuth, idle('x'));
      const btn = click(el);
      const http = TestBed.inject(HttpTestingController);
      http.expectOne('/api/pipeline/run').flush({ started: true }, { status: 202, statusText: 'Accepted' });

      vi.advanceTimersByTime(4000);
      http.expectOne('/api/pipeline/status').flush(pipe(false)); // aún arrancando
      fixture!.detectChanges();
      expect(btn.disabled).toBe(true);

      vi.advanceTimersByTime(4000);
      http.expectOne('/api/pipeline/status').flush(pipe(true));
      vi.advanceTimersByTime(4000);
      http.expectOne('/api/pipeline/status').flush(pipe(false)); // terminó
      http.expectOne('/api/status').flush(idle('Actualizado 17 nov · 08:00'));
      fixture!.detectChanges();
      expect(btn.disabled).toBe(false);
      expect(btn.textContent?.trim()).toBe('Actualizar datos');
    });

    it('si ya había una corrida (409) también queda esperando', () => {
      const el = render(noAuth, idle('x'));
      const btn = click(el);
      const http = TestBed.inject(HttpTestingController);
      http.expectOne('/api/pipeline/run').flush(
        { started: false, reason: 'already_running' }, { status: 409, statusText: 'Conflict' });
      fixture!.detectChanges();
      expect(btn.disabled).toBe(true);

      vi.advanceTimersByTime(4000);
      http.expectOne('/api/pipeline/status').flush(pipe(true));
      fixture!.detectChanges();
      expect(btn.disabled).toBe(true);
    });
  });

  it('oculta Salir sin login', () => {
    const el = render(noAuth, idle('x'));
    expect(el.querySelector('a.header-logout')).toBeNull();
  });

  it('muestra Salir con login activo', () => {
    const el = render({ map_tabs: [], auth_enabled: true }, idle('x'));
    expect(el.querySelector('a.header-logout')?.getAttribute('href')).toBe('/logout');
  });

  it('muestra el pie con las fuentes y el aviso de referencia', () => {
    const el = render(noAuth, idle('x'));
    const footer = el.querySelector('footer.app-footer')!;
    expect(footer.textContent).toContain('NOAA OISST v2');
    expect(footer.textContent).toContain('referencial, no reemplaza al ENFEN');
  });
});
