# ============================================================
# GRAFICAS.PY — Procesamiento NetCDF y gráficas
# ============================================================
import os, sys, re

if sys.platform.startswith("win"):
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.interpolate import RBFInterpolator

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ============================================================
# Listado de paletas de matplotlib
# ============================================================
def listar_cmaps():
    """Devuelve todos los colormaps disponibles en matplotlib (ordenados)."""
    try:
        cmaps = list(plt.colormaps())
    except (AttributeError, TypeError):
        try:
            import matplotlib.cm as cm
            cmaps = list(cm.cmap_d.keys())
        except Exception:
            cmaps = ["gist_rainbow_r", "RdBu_r", "viridis", "plasma",
                     "jet", "rainbow", "Spectral", "coolwarm", "hsv"]
    return sorted(set(cmaps))


def _mpl_to_plotly_cmap(cmap_name, n=20):
    """Convierte un cmap de matplotlib a colorscale de plotly."""
    try:
        cmap = plt.get_cmap(cmap_name)
    except Exception:
        try:
            cmap = plt.get_cmap("gist_rainbow_r")
        except Exception:
            cmap = plt.get_cmap("viridis")
    colors = []
    for i in range(n):
        x = i / (n - 1) if n > 1 else 0
        r, g, b, a = cmap(x)
        colors.append([x, f"rgb({int(r*255)},{int(g*255)},{int(b*255)})"])
    return colors


# ============================================================
# Figura de aviso
# ============================================================
def figura_aviso(titulo="Datos insuficientes",
                 subtitulo="No hay datos disponibles para los años seleccionados"):
    fig = go.Figure()
    fig.add_annotation(x=0.5, y=0.6, text=f"<b>{titulo}</b>", showarrow=False,
                       font=dict(size=20, color="#64748B"),
                       xref="paper", yref="paper")
    fig.add_annotation(x=0.5, y=0.42, text=subtitulo, showarrow=False,
                       font=dict(size=13, color="#94A3B8"),
                       xref="paper", yref="paper")
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(paper_bgcolor="white", plot_bgcolor="white",
                      margin=dict(l=30, r=30, t=30, b=30))
    return fig


def _leer_var(ncfile, var_name):
    try:
        datos = ncfile.variables[var_name][:]
    except Exception:
        return None
    if isinstance(datos, np.ma.MaskedArray):
        datos = datos.filled(np.nan)
    return np.asarray(datos, dtype=float)


def _leer_tiempo(ncfile):
    try:
        time_val = ncfile.variables["time"][:]
    except Exception:
        return None
    if isinstance(time_val, np.ma.MaskedArray):
        time_val = time_val.filled(np.nan)
    return np.asarray(time_val, dtype=float)


def _parse_time_units(tunits):
    parts = str(tunits).split()
    ref = parts[2] if len(parts) >= 3 else "1991-01-01"
    return pd.Timestamp(ref)


def procesar_nc(ncfile, var_name, inicio="1991-01-01", fin="2020-12-31"):
    datos = _leer_var(ncfile, var_name)
    if datos is None:
        return None
    time_val = _leer_tiempo(ncfile)
    if time_val is None:
        return None
    try:
        tunits = getattr(ncfile.variables["time"], "units",
                         "days since 1991-01-01")
        ref = _parse_time_units(tunits)
        fechas = pd.to_datetime([ref + pd.Timedelta(days=float(t))
                                 for t in time_val])
        ntime = len(fechas)
    except Exception:
        return None
    if datos.ndim > 1:
        dims = datos.shape
        idx_t = [i for i, d in enumerate(dims) if d == ntime]
        if idx_t:
            idx = [0] * datos.ndim
            idx[idx_t[0]] = slice(None)
            datos = datos[tuple(idx)]
        else:
            datos = datos.ravel()
    datos = np.asarray(datos, dtype=float).ravel()
    datos[np.abs(datos) > 1e10] = np.nan
    if len(datos) > ntime:
        datos = datos[:ntime]
    elif len(datos) < ntime:
        datos = np.concatenate([datos, np.full(ntime - len(datos), np.nan)])

    df = pd.DataFrame({"fechas": fechas, "datos": datos})
    df["doy"] = df["fechas"].dt.dayofyear
    df["anio"] = df["fechas"].dt.year

    anio_ini_sol = pd.Timestamp(inicio).year
    anio_fin_sol = pd.Timestamp(fin).year
    anios_data = sorted(df["anio"].unique())
    anios_validos = [a for a in anios_data
                     if anio_ini_sol <= a <= anio_fin_sol]

    if anios_validos:
        anio_ini_efec = min(anios_validos)
        anio_fin_efec = max(anios_validos)
    else:
        anio_ini_efec = anio_ini_sol
        anio_fin_efec = anio_fin_sol

    df_sub = df[(df["anio"] >= anio_ini_efec) & (df["anio"] <= anio_fin_efec)]
    if len(df_sub) == 0:
        df["clim_dia"] = np.nan
    else:
        df_clim = (df_sub.dropna(subset=["datos"])
                   .groupby("doy")["datos"].mean().reset_index())
        df_clim.columns = ["doy", "clim_dia"]
        df = df.merge(df_clim, on="doy", how="left")

    df["anomalia"] = (df["datos"] - df["clim_dia"]).round(2)
    df = df.sort_values("fechas").reset_index(drop=True)
    try:
        df.attrs["clim_range"] = (anio_ini_efec, anio_fin_efec, len(anios_validos))
    except Exception:
        pass
    return df


def procesar_nc_perfil(ncfile, var_name):
    datos = _leer_var(ncfile, var_name)
    if datos is None:
        return None
    time_val = _leer_tiempo(ncfile)
    if time_val is None:
        return None
    try:
        tunits = getattr(ncfile.variables["time"], "units",
                         "days since 1991-01-01")
        ref = _parse_time_units(tunits)
        fechas = pd.to_datetime([ref + pd.Timedelta(days=float(t))
                                 for t in time_val])
        ntime = len(fechas)
    except Exception:
        return None

    depth = None
    for name in ["depth", "DEPTH", "Depth", "prof", "pressure"]:
        if name in ncfile.variables:
            try:
                d = ncfile.variables[name][:]
                if isinstance(d, np.ma.MaskedArray):
                    d = d.filled(np.nan)
                depth = np.asarray(d, dtype=float).ravel()
                depth = depth[~np.isnan(depth)]
                if len(depth) > 0:
                    break
            except Exception:
                pass

    if depth is None or len(depth) == 0:
        for name in ncfile.dimensions:
            if "depth" in name.lower():
                dim_size = len(ncfile.dimensions[name])
                depth = np.arange(dim_size, dtype=float)
                break

    if depth is None or len(depth) == 0:
        m = re.search(r"T_(\d+)", var_name)
        if m:
            depth = np.array([float(m.group(1))])

    if depth is None or len(depth) == 0:
        return None

    while datos.ndim > 2 and 1 in datos.shape:
        datos = np.squeeze(datos)
    if datos.ndim > 2:
        while datos.ndim > 2:
            datos = datos[..., 0]

    n_d = len(depth)

    if datos.ndim == 0:
        return None
    if datos.ndim == 1:
        if len(datos) == ntime:
            datos = datos.reshape(1, -1)
            if n_d > 1:
                depth = depth[:1]
                n_d = 1
        else:
            return None
    elif datos.ndim == 2:
        sh = datos.shape
        if sh == (n_d, ntime):
            pass
        elif sh == (ntime, n_d):
            datos = datos.T
        elif sh[0] == 1 and sh[1] == ntime:
            if n_d > 1:
                depth = depth[:1]
                n_d = 1
        elif sh[0] == ntime and sh[1] == 1:
            datos = datos.T
            if n_d > 1:
                depth = depth[:1]
                n_d = 1
        else:
            return None
    else:
        return None

    if datos.shape[0] != len(depth) or datos.shape[1] != ntime:
        return None

    datos[np.abs(datos) > 1e10] = np.nan
    mask = ~np.isnan(datos)
    n_validos = mask.sum()
    if n_validos == 0:
        return None

    prof_idx, time_idx = np.where(mask)

    df = pd.DataFrame({
        "Profundidad": depth[prof_idx],
        "Fecha": [fechas[i] for i in time_idx],
        "TEMP": datos[prof_idx, time_idx],
    })
    df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.normalize()
    df["AÑO"] = df["Fecha"].dt.year
    df["DOY"] = df["Fecha"].dt.dayofyear
    df["Profundidad"] = df["Profundidad"].astype(float)
    df["TEMP"] = df["TEMP"].astype(float)
    return df


def crear_eje_x():
    meses = ["Ene","Feb","Mar","Abr","May","Jun",
             "Jul","Ago","Sep","Oct","Nov","Dic"]
    dias_mes = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    starts = [1]
    for d in dias_mes[:-1]:
        starts.append(starts[-1] + d)
    starts2 = [s + 365 for s in starts]
    return starts + starts2, meses + meses


def preparar_24m(df_merge, anios_p1, anios_p2):
    df1 = df_merge[df_merge["anio"].isin(anios_p1)].copy()
    if len(df1) > 0:
        base = pd.Timestamp(f"{int(anios_p1[0])}-01-01")
        df1["dia_rel"] = (df1["fechas"] - base).dt.days + 1
        df1["Serie"] = f"Años: {anios_p1[0]}-{anios_p1[1]}"
    df2 = df_merge[df_merge["anio"].isin(anios_p2)].copy()
    if len(df2) > 0:
        base = pd.Timestamp(f"{int(anios_p2[0])}-01-01")
        df2["dia_rel"] = (df2["fechas"] - base).dt.days + 1
        df2["Serie"] = f"Años: {anios_p2[0]}-{anios_p2[1]}"
    return pd.concat([df1, df2], ignore_index=True)


def clim_continua(df_merge):
    df_clim = (df_merge.drop_duplicates(subset="doy")[["doy", "clim_dia"]]
               .sort_values("doy"))
    vals = df_clim["clim_dia"].values
    if len(vals) == 0:
        return np.full(731, np.nan)
    if len(vals) >= 365:
        vals = vals[:365]
    else:
        vals = np.resize(vals, 365)
    return np.resize(vals, 731)


_TEMA_MAP = {
    "minimal": "plotly_white",
    "bw":      "simple_white",
    "classic": "simple_white",
    "light":   "plotly_white",
    "gray":    "plotly",
}


def _layout_base(titulo, ylab, tema):
    return dict(
        template=_TEMA_MAP.get(tema, "plotly_white"),
        title=dict(text=titulo, x=0.5, xanchor="center",
                   font=dict(size=13, color="#17324D")),
        margin=dict(l=60, r=20, t=60, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=False),
        yaxis=dict(title=ylab, showgrid=True, gridcolor="#E2E8F0"),
    )


def fmt_titulo_clim(titulo, df_merge):
    if not titulo:
        return ""
    try:
        range_clim = df_merge.attrs.get("clim_range")
        if range_clim:
            ini, fin, n_v = range_clim
            if "[" in titulo and "]" in titulo:
                return re.sub(r"\[\d{4}-\d{4}\]", f"[{ini}-{fin}]", titulo)
    except Exception:
        pass
    return titulo


def _series_hist_seg(df_merge, anios_p1, anios_p2, titulo, ylab, colores,
                     tema, c_p1, c_p2, c_hist, c_sep, unidad, ystep=5):
    eje_dias, eje_meses = crear_eje_x()
    df_plot = preparar_24m(df_merge, anios_p1, anios_p2)
    clim_ext = clim_continua(df_merge)
    df_clim = pd.DataFrame({"dia_rel": np.arange(1, 732),
                            "clim_dia": clim_ext})
    datos_vals = df_plot["datos"].values[~np.isnan(df_plot["datos"].values)]
    clim_vals = df_clim["clim_dia"].values[~np.isnan(df_clim["clim_dia"].values)]
    if len(datos_vals) == 0 and len(clim_vals) == 0:
        return figura_aviso("Sin datos válidos", titulo)
    minv = min(np.nanmin(datos_vals) if len(datos_vals) else np.inf,
               np.nanmin(clim_vals) if len(clim_vals) else np.inf)
    maxv = max(np.nanmax(datos_vals) if len(datos_vals) else -np.inf,
               np.nanmax(clim_vals) if len(clim_vals) else -np.inf)
    if not np.isfinite(minv) or not np.isfinite(maxv) or minv == maxv:
        minv, maxv = -5, 5
    ymin = np.floor(minv / ystep) * ystep
    ymax = np.ceil(maxv / ystep) * ystep

    titulo_final = fmt_titulo_clim(titulo, df_merge)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_clim["dia_rel"], y=df_clim["clim_dia"] - ymin,
        base=ymin, marker=dict(color=c_hist, line=dict(width=0)),
        width=1, name="Prom. Histórico", opacity=0.8,
        hovertemplate="Día %{x}<br>Prom. Histórico: %{y:.2f}<extra></extra>",
    ))
    fig.add_vline(x=366, line=dict(color=c_sep, width=1, dash="dot"))
    for serie, color in [(f"Años: {anios_p1[0]}-{anios_p1[1]}", c_p1),
                         (f"Años: {anios_p2[0]}-{anios_p2[1]}", c_p2)]:
        sub = df_plot[df_plot["Serie"] == serie]
        if len(sub) == 0: continue
        fig.add_trace(go.Scatter(
            x=sub["dia_rel"], y=sub["datos"], mode="lines", name=serie,
            line=dict(color=color, width=1),
            customdata=np.stack(
                [sub["fechas"].dt.strftime("%d/%m/%Y")], axis=-1),
            hovertemplate=("Fecha: %{customdata[0]}<br>Datos: %{y:.2f} "
                           + unidad + "<extra></extra>"),
        ))
    layout = _layout_base(titulo_final, ylab, tema)
    layout["xaxis"] = dict(tickmode="array", tickvals=eje_dias,
                           ticktext=eje_meses, range=[1, 731],
                           showgrid=False)
    layout["yaxis"] = dict(title=ylab, range=[ymin, ymax], showgrid=True,
                           gridcolor="#E2E8F0")
    fig.update_layout(**layout)
    return fig


def _series_hist_line(df_merge, anios_p1, anios_p2, titulo, ylab, colores,
                      tema, c_hist, c_p1, c_p2, c_sep, unidad, ystep=2):
    eje_dias, eje_meses = crear_eje_x()
    df_plot = preparar_24m(df_merge, anios_p1, anios_p2)
    clim_ext = clim_continua(df_merge)
    df_clim = pd.DataFrame({"dia_rel": np.arange(1, 732),
                            "clim_dia": clim_ext})
    datos_vals = df_plot["datos"].values[~np.isnan(df_plot["datos"].values)]
    clim_vals = df_clim["clim_dia"].values[~np.isnan(df_clim["clim_dia"].values)]
    if len(datos_vals) == 0 and len(clim_vals) == 0:
        return figura_aviso("Sin datos válidos", titulo)
    minv = min(np.nanmin(datos_vals) if len(datos_vals) else np.inf,
               np.nanmin(clim_vals) if len(clim_vals) else np.inf)
    maxv = max(np.nanmax(datos_vals) if len(datos_vals) else -np.inf,
               np.nanmax(clim_vals) if len(clim_vals) else -np.inf)
    if not np.isfinite(minv) or not np.isfinite(maxv) or minv == maxv:
        minv, maxv = 20, 30
    ymin = np.floor(minv / ystep) * ystep
    ymax = np.ceil(maxv / ystep) * ystep

    titulo_final = fmt_titulo_clim(titulo, df_merge)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_clim["dia_rel"], y=df_clim["clim_dia"], mode="lines",
        name="Prom. Histórico", line=dict(color=c_hist, width=1.5),
        hovertemplate=("Día %{x}<br>Prom. Histórico: %{y:.2f} "
                       + unidad + "<extra></extra>"),
    ))
    fig.add_vline(x=366, line=dict(color=c_sep, width=1, dash="dot"))
    for serie, color in [(f"Años: {anios_p1[0]}-{anios_p1[1]}", c_p1),
                         (f"Años: {anios_p2[0]}-{anios_p2[1]}", c_p2)]:
        sub = df_plot[df_plot["Serie"] == serie]
        if len(sub) == 0: continue
        fig.add_trace(go.Scatter(
            x=sub["dia_rel"], y=sub["datos"], mode="lines", name=serie,
            line=dict(color=color, width=1),
            customdata=np.stack(
                [sub["fechas"].dt.strftime("%d/%m/%Y")], axis=-1),
            hovertemplate=("Fecha: %{customdata[0]}<br>Datos: %{y:.2f} "
                           + unidad + "<extra></extra>"),
        ))
    layout = _layout_base(titulo_final, ylab, tema)
    layout["xaxis"] = dict(tickmode="array", tickvals=eje_dias,
                           ticktext=eje_meses, range=[1, 731],
                           showgrid=False)
    layout["yaxis"] = dict(title=ylab, range=[ymin, ymax], showgrid=True,
                           gridcolor="#E2E8F0")
    fig.update_layout(**layout)
    return fig


def _series_anom(df_merge, anios_p1, anios_p2, titulo, ylab, colores,
                 tema, c_cero, c_sep, unidad, ystep=5):
    eje_dias, eje_meses = crear_eje_x()
    df_plot = preparar_24m(df_merge, anios_p1, anios_p2)
    vals = df_plot["anomalia"].values[~np.isnan(df_plot["anomalia"].values)]
    if len(vals) == 0:
        return figura_aviso("Sin datos válidos", titulo)
    minv, maxv = np.nanmin(vals), np.nanmax(vals)
    if not np.isfinite(minv) or not np.isfinite(maxv) or minv == maxv:
        minv, maxv = -5, 5
    ymin = np.floor(minv / ystep) * ystep
    ymax = np.ceil(maxv / ystep) * ystep

    titulo_final = fmt_titulo_clim(titulo, df_merge)
    fig = go.Figure()
    for serie, color in [(f"Años: {anios_p1[0]}-{anios_p1[1]}", colores[0]),
                         (f"Años: {anios_p2[0]}-{anios_p2[1]}", colores[1])]:
        sub = df_plot[df_plot["Serie"] == serie]
        if len(sub) == 0: continue
        fig.add_trace(go.Scatter(
            x=sub["dia_rel"], y=sub["anomalia"], mode="lines", name=serie,
            line=dict(color=color, width=1),
            customdata=np.stack(
                [sub["fechas"].dt.strftime("%d/%m/%Y")], axis=-1),
            hovertemplate=("Fecha: %{customdata[0]}<br>Anomalía: %{y:.2f} "
                           + unidad + "<extra></extra>"),
        ))
    fig.add_hline(y=0, line=dict(color=c_cero, width=1, dash="dash"))
    fig.add_vline(x=366, line=dict(color=c_sep, width=1, dash="dot"))
    layout = _layout_base(titulo_final, ylab, tema)
    layout["xaxis"] = dict(tickmode="array", tickvals=eje_dias,
                           ticktext=eje_meses, range=[1, 731],
                           showgrid=False)
    layout["yaxis"] = dict(title=ylab, range=[ymin, ymax], showgrid=True,
                           gridcolor="#E2E8F0")
    fig.update_layout(**layout)
    return fig


def graficar_dyn(df_merge, anios_p1, anios_p2, titulo_hist, titulo_anom,
                 ylab_hist="Altura Dinámica [cm]",
                 ylab_anom="Anomalías [cm]",
                 colores=None, tema="minimal"):
    if not colores or len(colores) < 5:
        colores = ["#D32F2F", "#000000", "#6495ED", "#FF0000", "#FF0000"]
    hist = _series_hist_seg(df_merge, anios_p1, anios_p2, titulo_hist,
                            ylab_hist, colores, tema, colores[0], colores[1],
                            colores[2], colores[4], "cm", 5)
    anom = _series_anom(df_merge, anios_p1, anios_p2, titulo_anom, ylab_anom,
                        colores, tema, colores[3], colores[4], "cm", 5)
    return {"hist": hist, "anom": anom}


def graficar_iso(df_merge, anios_p1, anios_p2, titulo_hist, titulo_anom,
                 ylab_hist="Profundidad [m]", ylab_anom="Profundidad [m]",
                 colores=None, tema="minimal"):
    if not colores or len(colores) < 5:
        colores = ["#D32F2F", "#000000", "#B0B0B0", "#FF0000", "#FF0000"]
    hist = _series_hist_seg(df_merge, anios_p1, anios_p2, titulo_hist,
                            ylab_hist, colores, tema, colores[0], colores[1],
                            colores[2], colores[4], "m", 10)
    hist.update_yaxes(autorange="reversed")
    anom = _series_anom(df_merge, anios_p1, anios_p2, titulo_anom, ylab_anom,
                        colores, tema, colores[3], colores[4], "m", 10)
    anom.update_yaxes(autorange="reversed")
    return {"hist": hist, "anom": anom}


def graficar_sst(df_merge, anios_p1, anios_p2, titulo_hist, titulo_anom,
                 ylab_hist="[°C]", ylab_anom="Anomalías [°C]",
                 colores=None, tema="minimal"):
    if not colores or len(colores) < 5:
        colores = ["#0000CD", "#D32F2F", "#000000", "#FF0000", "#FF0000"]
    hist = _series_hist_line(df_merge, anios_p1, anios_p2, titulo_hist,
                             ylab_hist, colores, tema, colores[0], colores[1],
                             colores[2], colores[4], "°C", 2)
    anom = _series_anom(df_merge, anios_p1, anios_p2, titulo_anom, ylab_anom,
                        colores, tema, colores[3], colores[4], "°C", 2)
    return {"hist": hist, "anom": anom}


def graficar_w(df_merge, anios_p1, anios_p2, titulo_hist, titulo_anom,
               ylab_hist="Velocidad [m/s]", ylab_anom="Anomalía [m/s]",
               colores=None, tema="bw"):
    if not colores or len(colores) < 5:
        colores = ["#D32F2F", "#0000FF", "#D32F2F", "#4B92DB", "#FF0000"]
    c_bar, c_line = colores[0], colores[1]
    c_pos, c_neg = colores[2], colores[3]
    c_sep = colores[4]
    eje_dias, eje_meses = crear_eje_x()
    template_plotly = _TEMA_MAP.get(tema, "plotly_white")

    def prep(anios):
        sub = df_merge[df_merge["anio"].isin(anios)].copy()
        if len(sub) == 0:
            return sub
        base = pd.Timestamp(f"{int(anios[0])}-01-01")
        sub["dia_rel"] = (sub["fechas"] - base).dt.days + 1
        return sub

    df1 = prep(anios_p1); df2 = prep(anios_p2)
    titulo_final_hist = fmt_titulo_clim(titulo_hist, df_merge)
    titulo_final_anom = fmt_titulo_clim(titulo_anom, df_merge)

    def hist_plot(df, label):
        if len(df) == 0:
            return figura_aviso("Datos insuficientes", label)
        titulo_txt = titulo_final_hist + "<br><sub>" + label + "</sub>"
        vals = np.abs(np.concatenate([df["datos"].values,
                                       df["clim_dia"].values]))
        vals = vals[~np.isnan(vals)]
        maxv = np.nanmax(vals) if len(vals) > 0 else 10
        if not np.isfinite(maxv) or maxv == 0: maxv = 10
        xmax = int(np.ceil(maxv))
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df["dia_rel"], x=df["datos"], orientation="h",
            marker=dict(color=c_bar, line=dict(width=0)), width=1,
            name=label,
            customdata=np.stack(
                [df["fechas"].dt.strftime("%d/%m/%Y")], axis=-1),
            hovertemplate=("Fecha: %{customdata[0]}<br>Datos: %{x:.2f} "
                           "m/s<extra></extra>"),
        ))
        fig.add_trace(go.Scatter(
            y=df["dia_rel"], x=df["clim_dia"], mode="lines",
            name="Prom. Histórico", line=dict(color=c_line, width=1.2),
            hovertemplate=("Día %{y}<br>Prom. Histórico: %{x:.2f} "
                           "m/s<extra></extra>"),
        ))
        fig.add_hline(y=366, line=dict(color=c_sep, width=1, dash="dash"))
        fig.add_vline(x=0, line=dict(color="black", width=1))
        fig.update_layout(
            template=template_plotly,
            title=dict(text=titulo_txt, x=0.5, xanchor="center",
                       font=dict(size=13)),
            margin=dict(l=60, r=20, t=60, b=50),
            xaxis=dict(title=ylab_hist, range=[-xmax, xmax]),
            yaxis=dict(tickmode="array", tickvals=eje_dias,
                       ticktext=eje_meses, autorange="reversed"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
        )
        return fig

    def anom_plot(df, label):
        if len(df) == 0:
            return figura_aviso("Datos insuficientes", label)
        vals = df["anomalia"].values
        vals = vals[~np.isnan(vals)]
        maxv = np.nanmax(np.abs(vals)) if len(vals) > 0 else 5
        if not np.isfinite(maxv) or maxv == 0: maxv = 5
        xmax = int(np.ceil(maxv))
        if xmax % 2 != 0: xmax += 1
        cols = np.where(df["anomalia"] >= 0, c_pos, c_neg)
        titulo_txt = titulo_final_anom + "<br><sub>" + label + "</sub>"
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df["dia_rel"], x=df["anomalia"], orientation="h",
            marker=dict(color=cols, line=dict(width=0)), width=1,
            name=label,
            customdata=np.stack(
                [df["fechas"].dt.strftime("%d/%m/%Y")], axis=-1),
            hovertemplate=("Fecha: %{customdata[0]}<br>Anomalía: %{x:.2f} "
                           "m/s<extra></extra>"),
        ))
        fig.add_hline(y=366, line=dict(color=c_sep, width=1, dash="dash"))
        fig.add_vline(x=0, line=dict(color="black", width=1))
        fig.update_layout(
            template=template_plotly,
            title=dict(text=titulo_txt, x=0.5, xanchor="center",
                       font=dict(size=13)),
            margin=dict(l=60, r=20, t=60, b=50),
            xaxis=dict(title=ylab_anom, range=[-xmax, xmax]),
            yaxis=dict(tickmode="array", tickvals=eje_dias,
                       ticktext=eje_meses, autorange="reversed"),
            showlegend=False,
        )
        return fig

    return {
        "hist_p1": hist_plot(df1, f"Años: {anios_p1[0]}-{anios_p1[1]}"),
        "hist_p2": hist_plot(df2, f"Años: {anios_p2[0]}-{anios_p2[1]}"),
        "anom_p1": anom_plot(df1, f"Años: {anios_p1[0]}-{anios_p1[1]}"),
        "anom_p2": anom_plot(df2, f"Años: {anios_p2[0]}-{anios_p2[1]}"),
    }


# ============================================================
# CONTORNO Temperatura Subsuperficial
# ============================================================
def _interpolar_rbf(x, y, z, nodos_x=100, nodos_y=100, smoothing=0.05):
    mask = ~np.isnan(z) & ~np.isnan(x) & ~np.isnan(y)
    x = np.asarray(x[mask], dtype=float)
    y = np.asarray(y[mask], dtype=float)
    z = np.asarray(z[mask], dtype=float)

    if len(x) < 10:
        return None

    if len(x) > 800:
        idx = np.random.RandomState(42).choice(len(x), 800, replace=False)
        x, y, z = x[idx], y[idx], z[idx]

    x_grid = np.linspace(x.min(), x.max(), nodos_x)
    y_grid = np.linspace(0, y.max(), nodos_y)
    XX, YY = np.meshgrid(x_grid, y_grid)

    try:
        interp = RBFInterpolator(
            np.column_stack([x, y]), z,
            kernel="thin_plate_spline",
            smoothing=smoothing,
        )
        pts = np.column_stack([XX.ravel(), YY.ravel()])
        Z = interp(pts).reshape(nodos_y, nodos_x)
    except Exception as e:
        print(f"[TAO-RBF] Error en interpolacion: {e}")
        return None
    return x_grid, y_grid, Z


def calcular_datos_contorno_t(df_perfil, anios_p1, anios_p2,
                              inicio="1991-01-01", fin="2020-12-31",
                              prof_max=500):
    anio_ini_sol = pd.Timestamp(inicio).year
    anio_fin_sol = pd.Timestamp(fin).year
    anios_disp = sorted(df_perfil["AÑO"].unique())
    anios_validos = [a for a in anios_disp
                     if anio_ini_sol <= a <= anio_fin_sol]

    if len(anios_validos) < 25:
        return {"status": "insuficiente",
                "mensaje": (f"Se requieren al menos 25 años para la climatología.<br>"
                            f"Años disponibles en [{anio_ini_sol}-{anio_fin_sol}]: {len(anios_validos)}")}

    ini_ef = min(anios_validos); fin_ef = max(anios_validos)
    clim = (df_perfil[(df_perfil["AÑO"] >= ini_ef) &
                      (df_perfil["AÑO"] <= fin_ef)]
            .groupby(["DOY", "Profundidad"])["TEMP"]
            .mean().reset_index())
    clim.columns = ["DOY", "Profundidad", "TEMP_clim"]

    if len(clim) == 0:
        return {"status": "insuficiente",
                "mensaje": "No hay climatología disponible en el rango elegido"}

    df_full = df_perfil.merge(clim, on=["DOY", "Profundidad"], how="left")
    df_full["ANOM"] = df_full["TEMP"] - df_full["TEMP_clim"]

    def prep(anios):
        sub = df_full[(df_full["AÑO"].isin(anios)) &
                      (df_full["Profundidad"] <= prof_max)].copy()
        if len(sub) == 0:
            return None
        fecha_min = sub["Fecha"].min()
        sub["DIA_AÑO"] = (sub["Fecha"] - fecha_min).dt.days + 1

        t = _interpolar_rbf(sub["DIA_AÑO"].values,
                            sub["Profundidad"].values,
                            sub["TEMP"].values,
                            nodos_x=100, nodos_y=100, smoothing=0.05)
        a = _interpolar_rbf(sub["DIA_AÑO"].values,
                            sub["Profundidad"].values,
                            sub["ANOM"].values,
                            nodos_x=100, nodos_y=100, smoothing=0.05)
        if t is None or a is None:
            return None
        return {"temp": t, "anom": a,
                "label": f"Año: {anios[0]}-{anios[1]}"}

    p1 = prep([anios_p1[0], anios_p1[1]])
    p2 = prep([anios_p2[0], anios_p2[1]])
    if p1 is None and p2 is None:
        return {"status": "insuficiente",
                "mensaje": "No hay registros para los años seleccionados"}
    return {"status": "ok", "p1": p1, "p2": p2, "prof_max": prof_max,
            "anio_ini_efec": ini_ef, "anio_fin_efec": fin_ef}


def _tickvals_cada_2(lo, hi):
    lo_i = int(np.floor(lo))
    hi_i = int(np.ceil(hi))
    start = lo_i if lo_i % 2 == 0 else lo_i + 1
    if start < lo_i:
        start = lo_i
    vals = list(range(start, hi_i + 1, 2))
    if len(vals) < 3:
        vals = list(range(lo_i, hi_i + 1, 2))
    return vals


def construir_plots_contorno_t(datos, titulo_hist, titulo_anom,
                               ylab_hist="Profundidad [m]",
                               ylab_anom="Profundidad [m]",
                               cmap_temp="gist_rainbow_r",
                               cmap_anom="RdBu_r"):
    """Construye las 4 gráficas de TSSM usando dos cmaps de matplotlib."""
    colorscale_temp = _mpl_to_plotly_cmap(cmap_temp, n=20)
    colorscale_anom = _mpl_to_plotly_cmap(cmap_anom, n=20)

    if datos is None or datos.get("status") != "ok":
        msg = datos.get("mensaje", "Sin datos") if datos else "Sin datos"
        p = figura_aviso("Datos insuficientes", msg)
        return {"hist_p1": p, "hist_p2": p, "anom_p1": p, "anom_p2": p}

    def fmt_titulo(t, ini, fin):
        if not t: return None
        if re.search(r"\[\d{4}-\d{4}\]", t):
            return re.sub(r"\[\d{4}-\d{4}\]", f"[{ini}-{fin}]", t)
        return f"{t}<br>Climatología: {ini}-{fin}"

    tit_hist = fmt_titulo(titulo_hist, datos["anio_ini_efec"], datos["anio_fin_efec"])
    tit_anom = fmt_titulo(titulo_anom, datos["anio_ini_efec"], datos["anio_fin_efec"])

    eje_dias, eje_meses = crear_eje_x()

    def plot_temp(p, titulo, label):
        if p is None:
            return figura_aviso("Datos insuficientes", label)
        x_grid, y_grid, Z = p["temp"]
        tmin = int(np.floor(np.nanmin(Z)))
        tmax = int(np.ceil(np.nanmax(Z)))
        tickvals = _tickvals_cada_2(tmin, tmax)

        fig = go.Figure(go.Contour(
            x=x_grid, y=y_grid, z=Z,
            colorscale=colorscale_temp,
            contours=dict(
                start=tmin, end=tmax, size=1,
                showlabels=True,
                labelfont=dict(size=10),
            ),
            line=dict(width=0.5, color="black"),
            hovertemplate=("Día %{x:.0f}<br>Prof: %{y:.0f} m<br>"
                           "T: %{z:.2f}°C<extra></extra>"),
            colorbar=dict(
                ticks="outside",
                tickfont=dict(size=11),
                tickmode="array",
                tickvals=tickvals,
                thickness=15,
                outlinewidth=1,
                outlinecolor="black",
                len=0.95,
                lenmode="fraction",
                x=1.02,
            ),
        ))

        titulo_completo = f"{titulo}<br>{label}"

        fig.update_layout(
            template="plotly_white",
            title=dict(text=titulo_completo, x=0.5, xanchor="center", font=dict(size=12)),
            margin=dict(l=60, r=100, t=75, b=40),
            xaxis=dict(
                title=None,
                tickmode="array",
                tickvals=eje_dias,
                ticktext=eje_meses,
                range=[1, 731],
                showgrid=False
            ),
            yaxis=dict(autorange="reversed", title=ylab_hist),
        )
        return fig

    def plot_anom(p, titulo, label):
        if p is None:
            return figura_aviso("Datos insuficientes", label)
        x_grid, y_grid, Z = p["anom"]
        lim = max(abs(np.nanmin(Z)), abs(np.nanmax(Z)))
        lim = int(np.ceil(lim))
        if lim == 0: lim = 3
        tickvals = _tickvals_cada_2(-lim, lim)
        if 0 not in tickvals:
            tickvals = sorted(set(tickvals + [0]))

        fig = go.Figure(go.Contour(
            x=x_grid, y=y_grid, z=Z,
            colorscale=colorscale_anom,
            zmin=-lim, zmax=lim,
            contours=dict(
                start=-lim, end=lim, size=1,
                showlabels=True,
                labelfont=dict(size=10),
            ),
            line=dict(width=0.5, color="black"),
            hovertemplate=("Día %{x:.0f}<br>Prof: %{y:.0f} m<br>"
                           "Anom: %{z:.2f}°C<extra></extra>"),
            colorbar=dict(
                ticks="outside",
                tickfont=dict(size=11),
                tickmode="array",
                tickvals=tickvals,
                thickness=15,
                outlinewidth=1,
                outlinecolor="black",
                len=0.95,
                lenmode="fraction",
                x=1.02,
            ),
        ))

        titulo_completo = f"{titulo}<br>{label}"

        fig.update_layout(
            template="plotly_white",
            title=dict(text=titulo_completo, x=0.5, xanchor="center", font=dict(size=12)),
            margin=dict(l=60, r=100, t=75, b=40),
            xaxis=dict(
                title=None,
                tickmode="array",
                tickvals=eje_dias,
                ticktext=eje_meses,
                range=[1, 731],
                showgrid=False
            ),
            yaxis=dict(autorange="reversed", title=ylab_anom),
        )
        return fig

    l1 = datos["p1"]["label"] if datos["p1"] else ""
    l2 = datos["p2"]["label"] if datos["p2"] else ""
    return {
        "hist_p1": plot_temp(datos["p1"], tit_hist, l1),
        "hist_p2": plot_temp(datos["p2"], tit_hist, l2),
        "anom_p1": plot_anom(datos["p1"], tit_anom, l1),
        "anom_p2": plot_anom(datos["p2"], tit_anom, l2),
    }


defaults_var = {
    "sst": {"titulo_hist": "TSM: Promedio Histórico [1991-2020] Vs Años",
            "titulo_anom": "Anomalías: Temperatura Superficial del Mar [1991-2020]",
            "ylab_hist": "[°C]", "ylab_anom": "Anomalías [°C]"},
    "dyn": {"titulo_hist": "Promedio Histórico [1991-2020] Vs Años",
            "titulo_anom": "Anomalías: Altura Dinámica [1991-2020]",
            "ylab_hist": "Altura Dinámica [cm]",
            "ylab_anom": "Anomalías [cm]"},
    "iso": {"titulo_hist": "Isoterma de 20°C: Promedio Histórico [1991-2020] Vs Años",
            "titulo_anom": "Anomalías: Isoterma 20°C [1991-2020]",
            "ylab_hist": "Profundidad [m]", "ylab_anom": "Profundidad [m]"},
    "t":   {"titulo_hist": "Temperatura Sub Superficial del mar [°C]",
            "titulo_anom": "Anomalía diaria de Temperatura Sub Superficial del mar [°C]",
            "ylab_hist": "Profundidad [m]", "ylab_anom": "Profundidad [m]"},
    "w":   {"titulo_hist": "Vientos Zonales: Promedio Histórico [1991-2020] Vs Años",
            "titulo_anom": "Vientos Zonales: Anomalías [1991-2020]",
            "ylab_hist": "Velocidad [m/s]",
            "ylab_anom": "Anomalía [m/s]"},
}