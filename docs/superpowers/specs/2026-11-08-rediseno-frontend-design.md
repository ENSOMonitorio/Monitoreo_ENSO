# Rediseño del frontend del Monitor ENSO

Fecha: 2026-11-08 · Estado: propuesta para aprobar
Mockup navegable: https://claude.ai/artifact/Dpe6dyJZwTmWNf73tH7M4e (login, portada y 9 vistas de Explorar)

## 1. Intención

El monitor (https://monitoreoenso.igdanielporrasn.cloud) funciona, pero se ve armado a parches: verde
oscuro sobre gris claro, todo escondido detrás de 4 botones y una columna larga por sección. Se quiere
un frontend con una estética claramente superior, que use como vara de calidad el prototipo DashFEN de
Escuela R, pero que **no se le parezca**: es otro proyecto, de otra organización.

Lo usan dos públicos:

- **Especialistas** (oceanografía, meteorología): vienen a ver cómo amaneció el Pacífico y a recorrer una
  variable en el tiempo.
- **Tomadores de decisiones**: necesitan entender en segundos en qué estamos y qué implica. Por eso la
  portada abre con una explicación en lenguaje claro, antes del detalle técnico.

## 2. Objetivos, no objetivos y antiobjetivos

**Objetivos**
- Portada «Situación» que responda primero, en lenguaje claro, qué está pasando, y luego dé el detalle técnico.
- Una vista por variable en «Explorar», con línea de tiempo y comparación de fechas donde aplique.
- Un recuadro «Cómo leerlo» en cada vista, para quien no es especialista.
- Login rediseñado, con entrada por Google (lista de correos aprobados) además de usuario y contraseña.
- Un solo sistema visual en Angular, en los gráficos Plotly y en la app Dash de boyas.

**No objetivos (v1)**
- Mapas interactivos (MapLibre con datos en vez de PNG): queda como fase 2, es trabajo del pipeline.
- Modo oscuro: las figuras de matplotlib tienen fondo blanco.
- Cambiar cómo se calculan los datos o las figuras (salvo lo anotado en §9).

**Antiobjetivos** (aunque funcione, sería un fracaso)
- Que se parezca a DashFEN: crema, verde y lima, títulos en serif, bordes en forma de hoja, flujo de pasos.
- Que parezca un comunicado oficial: todo índice propio dice «referencial, no reemplaza al ENFEN».
- Que el login muestre datos antes de autenticarse.
- Perder la animación del globo del login.
- Romper el pipeline diario, el CI o el despliegue automático.

## 3. Restricciones

- Se queda la arquitectura: Angular 22 (`frontend/`), Flask (`backend/app/app.py`), una imagen Docker
  multi-stage y deploy automático al mergear a `main` (`.github/workflows/ci-deploy.yml`).
- Todo va por rama + PR, nunca push directo a `main`. Cada PR pasa «Tests (build imagen + pytest)».
- Los mapas son PNG/GIF ya renderizados por el pipeline (`data/figures/`). El frontend los presenta, no
  los dibuja.
- El login lo renderiza Flask (`LOGIN_HTML` en `app.py`) antes de la SPA. Se mantiene así, para que nada
  de la SPA se sirva sin sesión.
- Credenciales y llaves solo en `secrets.env` (ojo: los `$` se escapan como `$$`).
- Equipo: Cami revisa antes de cada despliegue, Dodo mira servicios y logs después, Spiderman revisa el
  cambio de acceso (Google) y Rocki anota cada cambio en `HISTORIAL.md`.

## 4. Enfoques considerados

| Enfoque | Qué implica | Por qué sí o no |
|---|---|---|
| **A · Rediseño dentro del Angular actual** (elegido) | Nuevo sistema visual, portada y Explorar sobre la API que ya existe. Un endpoint nuevo (`/api/resumen`). Se alinean Plotly y Dash. | El problema es de diseño, no de tecnología. Reusa Docker, CI y rutas. Se entrega por partes. |
| B · Frontend nuevo en paralelo (`/v2`, otro framework) | Más libertad, dos frontends un tiempo, cambios en el Dockerfile. | Duplica trabajo sin ganar nada que A no dé. |
| C · A + mapas interactivos | MapLibre con datos (tiles o COG) en vez de PNG. | Lo más vistoso, pero es sobre todo trabajo del pipeline y lleva semanas. Queda como fase 2. |

El usuario delegó la decisión y se eligió A.

## 5. Sistema visual

Claro y frío, de «atlas científico». Distinto a propósito de DashFEN.

| Token | Valor | Uso |
|---|---|---|
| `--bg` | `#F3F5F6` | Fondo de la app |
| `--surface` | `#FFFFFF` | Tarjetas, cabecera |
| `--line` | `#DCE2E6` | Bordes |
| `--ink` | `#0E2233` | Texto principal, botones primarios (azul océano) |
| `--ink-2` | `#45576A` | Texto secundario |
| `--muted` | `#5C6E80` | Etiquetas (≥4.5:1 sobre blanco) |
| `--accent` | `#0F5E86` | Enlaces, íconos |
| `--accent-soft` | `#E3EEF4` | Ítem activo del menú |
| `--warm` / `--warm-soft` | `#8E1F12` / `#FBE8E1` | Solo para «cálido» (chip de magnitud, avisos) |
| Regiones Niño | 1+2 `#c62828` · 3 `#2e7d32` · 3.4 `#1565c0` · 4 `#7b1fa2` | Iguales a `NINO_COLORS` de `backend/app/plotting/common.py`, así el gráfico y las cajas del mapa coinciden |

- Tipografía: Space Grotesk (títulos y números grandes), Inter (texto), IBM Plex Mono (fechas, coordenadas
  y deltas).
- Radios de 8, 12 y 16 px, iguales en todas las esquinas. Sin degradados ni sombras grandes.
- Rojo y azul solo significan cálido y frío. La identidad de las series la dan los colores de región.
- Los valores se escriben en tinta, nunca del color de la serie. Los estados llevan ícono y texto, nunca
  solo color.
- Diseñado para laptop (1440 px). A ancho de celular, las columnas se apilan y los gráficos anchos se
  desplazan dentro de su caja.

## 6. Pantallas

### 6.1 Login (Flask, `/login`)
- Izquierda, en blanco: marca, «El Niño–Oscilación del Sur», una frase, tres líneas sobre lo que hay adentro
  y el **globo animado actual** (`/login-assets/past-el-nino-gif-1.webp`). Al pie, las fuentes.
- Derecha: tarjeta con **«Continuar con Google»**, separador «o con usuario y contraseña», Usuario,
  Contraseña (con «Mostrar») y «Iniciar sesión». Debajo: «La sesión queda abierta 7 días en este equipo».
- Errores: «Usuario o contraseña incorrectos.» y «La cuenta X no tiene acceso al monitor. Pide al
  administrador que la agregue.»
- No muestra ningún dato del ENSO.

### 6.2 Situación (portada, `/situacion`, ruta por defecto)
1. **Resumen en lenguaje claro:** fecha; titular; párrafo; recuadro «Qué suele traer un El Niño costero
   de esta magnitud» (3 impactos típicos, marcados como «no es un pronóstico»); aviso de que no reemplaza
   al ENFEN.
2. **Tarjeta de magnitud:** anomalía Niño 1+2 en grande, escala de 8 niveles (fría fuerte → cálida
   extraordinaria) con la marca «hoy», chip de categoría, Niño 3.4 con su categoría y tendencia de 7 días.
3. **Índices Niño:** 4 tarjetas (1+2, 3, 3.4, 4) con valor, curva de 30 días y deltas de 7 y 30 días y
   máximo.
4. **Mapa del día:** selector Anomalía / Temperatura y enlace «Recorrer el año» → Explorar.
5. **«Cómo llegamos aquí»:** serie diaria del año de Niño 1+2 y 3.4, con umbral +0.5, máximo anotado,
   etiquetas al final de cada línea y tooltip al pasar el cursor.
6. **Océano y atmósfera:** tarjetas de Onda Kelvin, Viento, Hovmöller 3.4 y Presión, cada una enlazada a
   su vista.

### 6.3 Explorar (`/explorar/:variable`)
Menú lateral por grupos (Superficie, Océano, Atmósfera) con enlaces. Cada vista tiene: título,
descripción, figura, «Cómo leerlo» y ficha (fuente, frecuencia, dominio).

| Variable | Ruta | Extras |
|---|---|---|
| Anomalía de TSM | `anom` | Línea de tiempo (reproducir, ‹ ›, deslizador) + «Comparar fechas» (A arriba, B abajo) |
| Temperatura (TSM) | `tsm` | Igual que anomalía |
| Onda Kelvin | `subsurf` | «Corte completo» (composite) / «Anomalía mes a mes» (fichas de mes) |
| Hovmöller Niño 3.4 / 1+2 | `hov34` / `hov12` | Figura alta a la izquierda; a la derecha, esquema de cómo leer los ejes; selector entre regiones |
| Boyas TAO | `boyas` | La app Dash existente en iframe, con el estilo nuevo (§7.4) |
| Viento 850 hPa | `viento` | Línea de tiempo + leyenda en palabras |
| Presión (SLP) | `slp` | Valor del centro del anticiclón (si el pipeline lo entrega, §9) + aviso «en desarrollo» de gatilladores |
| GOES-19 | `goes19` | Animación sobre fondo oscuro + hora de la última imagen (si `/api/goes19` no la entrega, se omite) |

### 6.4 Histórico (`/historico`)
El contenido actual (ONI histórico en Plotly + tarjetas de eventos) con el estilo nuevo. No se mockeó.

### Cabecera (en todas)
Marca · Situación / Explorar / Histórico · «Datos al día · fecha» (de `/api/status`) · «Actualizar datos»
(el `/api/pipeline/run` actual) · Salir.

## 7. Cambios técnicos

### 7.1 Frontend (Angular)
- `styles.scss`: reemplazar la paleta verde por los tokens de §5. Fuentes por Google Fonts, como hoy.
- Rutas: `''` → `situacion`; `explorar/:variable`; `historico`. Las rutas viejas (`tsm`, `anom`, `viento`,
  `slp`, `hovmoller_*`, `subsurf`, `goes19`, `indices`) redirigen a su equivalente.
- Componentes nuevos: `shell` (cabecera), `situacion`, `explorar` (menú + vista por variable),
  `timeline` (evolución de `date-player`), `como-leerlo`, `ficha`.
- Curvas de 30 días: SVG propio en Angular. Serie del año: Plotly (ya es dependencia) con el tema nuevo.
- Comparar fechas: dos llamadas a `/api/figures/<prefix>?date=...`.

### 7.2 Backend: `/api/resumen` (nuevo, con TDD en pytest)
Lee `data/processed/indices_diarios.csv` y devuelve JSON con:
- `fecha`.
- Por región (`nino12`, `nino3`, `nino34`, `nino4`): `valor`, `delta_7d`, `delta_30d`, `max_anual` y su
  fecha, y `serie_30d`.
- `serie_anual` de `nino12` y `nino34`.
- `categoria` de Niño 1+2 (umbrales ICEN: fría fuerte < −1.4; fría moderada −1.4 a −1.2; fría débil
  −1.2 a −1.0; neutra −1.0 a +0.4; cálida débil 0.4–1.0, moderada 1.0–1.7, fuerte 1.7–3.0, extraordinaria
  >3.0). Verificarlos contra la nota técnica del ENFEN antes de implementar.
- `categoria` de Niño 3.4 (umbrales ONI: débil 0.5–1.0, moderada 1.0–1.5, fuerte 1.5–2.0, muy fuerte ≥2.0).
- `tendencia` (sube / baja / estable, con un margen de ±0.1 °C en 7 días).
- `resumen`: titular y párrafo armados con plantillas a partir de lo anterior.
- Sin datos: `{"available": false}`, igual que `/api/indices/<region>`.

### 7.3 Plotly (`backend/app/theme.py`)
Pasar de `dark_layout` a un layout claro con los tokens de §5. Revisar quién lo usa (`indices.py`,
`layout_historico.py`).

### 7.4 Dash de boyas (`backend/app/subsuperficie/`)
Ajustar `assets/estilo.css` y `estilo.py` a los tokens y fuentes de §5. Quitar la barra de marca propia
(«🌊 Monitoreo ENSO»), porque ya está dentro del monitor, y los emojis. La funcionalidad no cambia.

### 7.5 Login con Google (Flask)
- Authlib (OIDC de Google). Rutas `/login/google` y `/auth/google/callback`.
- Variables en `secrets.env`: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` y `ENSO_ALLOWED_EMAILS` (correos
  separados por coma).
- Solo entra quien tenga `email_verified` y un correo en la lista. Si no, se muestra el error de §6.1.
- Se mantiene usuario y contraseña (`ENSO_AUTH_USER` / `ENSO_AUTH_PASS_HASH`).
- Se guarda el correo en la sesión. Si no hay credenciales de Google configuradas, el botón no aparece
  (igual que hoy el login se apaga sin `ENSO_AUTH_PASS_HASH`).
- En Google Cloud: cliente OAuth web con la dirección de retorno
  `https://monitoreoenso.igdanielporrasn.cloud/auth/google/callback`. Eso lo crea el usuario; se le pasan
  los pasos.
- Spiderman revisa antes de publicar.

## 8. Entregas (un PR cada una)

1. Sistema visual + cabecera + rutas nuevas con redirecciones + login rediseñado (sin Google todavía).
2. `/api/resumen` (tests primero) + portada Situación.
3. Explorar: las 9 vistas, la línea de tiempo y la comparación.
4. Tema de Plotly + estilo de la app Dash + Histórico.
5. Login con Google y lista de correos (con revisión de Spiderman).

En cada una: Cami revisa antes del merge, Dodo revisa después del deploy y Rocki anota en `HISTORIAL.md`.

## 9. Pendientes aparte (no bloquean)

- **Escala del Hovmöller Niño 1+2:** llega a +2.7 °C y el índice está en +5.4 °C, así que desde julio todo
  queda en el mismo rojo. Habría que ampliar la escala en el pipeline. Cambia las figuras, así que necesita
  el OK del usuario.
- **Centro del anticiclón:** el valor ~1032 hPa del mockup se leyó de la figura. Para mostrarlo en vivo, el
  pipeline debería guardar el máximo de presión y su posición. Si no, se omite.
- **Notas «Lo que muestra…»** de cada vista: necesitan que alguien las escriba. Quedan para una fase 2
  (nota del analista editable).

## 10. Decisiones tomadas por Dany (revisar)

- Los textos del resumen de la portada se arman **automáticamente con plantillas y umbrales** (§7.2). Los
  impactos típicos y los «Cómo leerlo» son textos fijos que valida el usuario.
- Para la magnitud se usan los umbrales del ICEN (Niño 1+2) y del ONI (Niño 3.4), aplicados al índice
  diario y marcados como referenciales.
- Las notas «Lo que muestra…» salen de la v1 (§9).
- En la v1 el login con Google usa una lista de correos (no dominio) y mantiene usuario y contraseña.

## 11. Lo que queda a criterio de quien construya

- Estructura interna de componentes y servicios en Angular.
- Detalles de espaciado y estados hover y foco, dentro de los tokens.
- Redacción exacta de las plantillas del resumen, siempre que respete §7.2 y diga «referencial».
