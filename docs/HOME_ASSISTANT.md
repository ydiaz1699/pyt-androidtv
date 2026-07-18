# Integración con Home Assistant

Guía completa para instalar, configurar y personalizar la integración **pyt-androidtv** en Home Assistant con tarjetas **Mushroom**.

---

## Tabla de Contenidos

- [Requisitos](#requisitos)
- [Instalación](#instalación)
  - [Instalación via HACS (recomendada)](#instalación-via-hacs-recomendada)
  - [Instalación manual](#instalación-manual)
- [Configuración](#configuración)
  - [Desde la UI](#desde-la-ui)
  - [Desde YAML](#desde-yaml)
- [Entidades creadas](#entidades-creadas)
- [Servicios personalizados](#servicios-personalizados)
- [Tarjetas Mushroom](#tarjetas-mushroom)
  - [Requisitos Mushroom](#requisitos-mushroom)
  - [Media Player Card (básica)](#media-player-card-básica)
  - [Media Player con volumen slider](#media-player-con-volumen-slider)
  - [Chips de Apps Favoritas](#chips-de-apps-favoritas)
  - [Control Remoto D-pad](#control-remoto-d-pad)
  - [Panel completo (todo junto)](#panel-completo-todo-junto)
  - [Botón de toque en pantalla](#botón-de-toque-en-pantalla)
  - [Teclado virtual](#teclado-virtual)
- [Automatizaciones](#automatizaciones)
- [Solución de problemas](#solución-de-problemas)

---

## Requisitos

| Requisito | Versión mínima |
|-----------|---------------|
| Home Assistant | 2024.1+ |
| Python | 3.10+ |
| Dispositivo | Android TV o Fire TV con ADB habilitado |
| Red | Dispositivo y HA en la misma red WiFi |

### Habilitar ADB en el dispositivo

1. Ir a **Ajustes > Acerca del dispositivo**
2. Pulsar 7 veces en **Número de compilación** (activa Opciones de desarrollador)
3. Volver a **Ajustes > Opciones de desarrollador**
4. Activar **Depuración USB** y/o **Depuración inalámbrica**

---

## Instalación

### Instalación via HACS (recomendada)

1. Asegúrate de tener [HACS](https://hacs.xyz/) instalado
2. En HACS, ve a **Integraciones**
3. Clic en el menú de 3 puntos (arriba derecha) > **Repositorios personalizados**
4. Agregar URL: `https://github.com/ydiaz1699/pyt-androidtv`
5. Categoría: **Integración**
6. Clic en **Agregar**
7. Buscar "pyt-androidtv" y hacer clic en **Descargar**
8. Reiniciar Home Assistant

### Instalación manual

1. Descargar la carpeta `custom_components/pyt_androidtv/` del repositorio
2. Copiarla en `config/custom_components/pyt_androidtv/` de tu HA
3. Reiniciar Home Assistant

Estructura esperada:
```
config/
└── custom_components/
    └── pyt_androidtv/
        ├── __init__.py
        ├── config_flow.py
        ├── const.py
        ├── manifest.json
        ├── media_player.py
        ├── services.yaml
        └── strings.json
```

---

## Configuración

### Desde la UI

1. Ir a **Ajustes > Dispositivos y servicios**
2. Clic en **Agregar integración**
3. Buscar "Android TV / Fire TV (pyt-androidtv)"
4. Rellenar el formulario:

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| **Dirección IP** | IP del dispositivo en tu red | `192.168.1.100` |
| **Puerto ADB** | Puerto de depuración (por defecto 5555) | `5555` |
| **Nombre** | Nombre para mostrar en HA | `Android TV Salón` |
| **Tipo de dispositivo** | androidtv o firetv | `androidtv` |
| **Ruta adbkey** | (Opcional) Ruta al archivo de clave ADB | `/config/.android/adbkey` |
| **IP servidor ADB** | (Opcional) Si usas un servidor ADB | `192.168.1.50` |

5. Clic en **Enviar**
6. Si la conexión es exitosa, verás tu dispositivo en la lista

### Desde YAML

También puedes configurar manualmente en `configuration.yaml`:

```yaml
# configuration.yaml
pyt_androidtv:
  - host: 192.168.1.100
    port: 5555
    name: "Android TV Salón"
    device_class: androidtv
    # adbkey: "/config/.android/adbkey"  # Opcional
    # adb_server_ip: "192.168.1.50"      # Opcional
```

---

## Entidades creadas

Al configurar un dispositivo, se crean las siguientes entidades:

| Entidad | Tipo | Descripción |
|---------|------|-------------|
| `media_player.android_tv_salon` | media_player | Control principal del dispositivo |

### Atributos expuestos

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `app_id` | string | Package ID de la app actual |
| `hdmi_input` | string | Entrada HDMI activa (HW1, HW2...) |
| `running_apps` | lista | Apps en ejecución |
| `volume_level` | float | Nivel de volumen (0.0 - 1.0) |
| `is_volume_muted` | bool | Si está en silencio |
| `source` | string | App actual (misma que app_id) |
| `source_list` | lista | Lista de apps en ejecución |

### Features soportadas

La entidad media_player soporta todas estas operaciones (compatibles con Mushroom):

- Encender / Apagar
- Play / Pause / Stop
- Siguiente / Anterior
- Volumen: Subir, Bajar, Silenciar, Establecer nivel
- Seleccionar fuente (lanzar app)

---

## Servicios personalizados

Además del control estándar de media_player, esta integración expone servicios adicionales:

### `pyt_androidtv.adb_command`

Ejecutar cualquier comando ADB en el dispositivo.

```yaml
service: pyt_androidtv.adb_command
data:
  entity_id: media_player.android_tv_salon
  command: "dumpsys battery"
```

### `pyt_androidtv.tap`

Simular un toque en coordenadas de la pantalla.

```yaml
service: pyt_androidtv.tap
data:
  entity_id: media_player.android_tv_salon
  x: 960
  y: 540
```

### `pyt_androidtv.swipe`

Simular un deslizamiento en la pantalla.

```yaml
service: pyt_androidtv.swipe
data:
  entity_id: media_player.android_tv_salon
  x1: 500
  y1: 1500
  x2: 500
  y2: 500
  duration_ms: 300
```

### `pyt_androidtv.input_text`

Escribir texto en el campo de entrada activo.

```yaml
service: pyt_androidtv.input_text
data:
  entity_id: media_player.android_tv_salon
  text: "Mi película favorita"
```

---

## Tarjetas Mushroom

### Requisitos Mushroom

1. Instalar [Mushroom](https://github.com/piitaya/lovelace-mushroom) via HACS:
   - En HACS > **Frontend** > Buscar "Mushroom" > Descargar
2. Reiniciar el navegador (F5)

> **Nota importante**: Mushroom NO se incorpora a la librería Python.
> Es un frontend (JavaScript) que lee las entidades de HA y las muestra
> con una interfaz bonita. Tu integración pyt-androidtv crea las
> entidades correctas, y Mushroom las renderiza automáticamente.

---

### Media Player Card (básica)

La tarjeta más simple — muestra estado y controles de reproducción:

```yaml
type: custom:mushroom-media-player-card
entity: media_player.android_tv_salon
name: "Android TV Salón"
icon: mdi:television
media_controls:
  - on_off
  - play_pause_stop
volume_controls:
  - volume_mute
  - volume_set
```

**Opciones de `media_controls`:**
| Control | Descripción |
|---------|-------------|
| `on_off` | Botón encender/apagar |
| `play_pause_stop` | Botón play/pause/stop según estado |
| `previous` | Pista anterior |
| `next` | Siguiente pista |
| `shuffle` | Aleatorio |
| `repeat` | Repetir |

**Opciones de `volume_controls`:**
| Control | Descripción |
|---------|-------------|
| `volume_set` | Slider de volumen (barra deslizante) |
| `volume_buttons` | Botones +/- |
| `volume_mute` | Botón silenciar |

---

### Media Player con volumen slider

Tarjeta horizontal con info del medio y slider de volumen:

```yaml
type: custom:mushroom-media-player-card
entity: media_player.android_tv_salon
name: "Android TV"
icon: mdi:television
use_media_info: true
show_volume_level: true
layout: horizontal
fill_container: true
media_controls:
  - on_off
  - previous
  - play_pause_stop
  - next
volume_controls:
  - volume_mute
  - volume_set
```

**`use_media_info: true`** — Cuando hay algo reproduciéndose, muestra el nombre de la app (ej: "Netflix", "YouTube") en lugar del nombre de la entidad.

**`show_volume_level: true`** — Muestra el porcentaje de volumen junto al estado.

**`collapsible_controls: true`** — Los controles se ocultan cuando el TV está apagado (ahorra espacio).

---

### Chips de Apps Favoritas

Fila de íconos pequeños para lanzar apps con un solo toque:

```yaml
type: custom:mushroom-chips-card
chips:
  # Netflix
  - type: action
    icon: mdi:netflix
    tap_action:
      action: call-service
      service: media_player.select_source
      data:
        entity_id: media_player.android_tv_salon
        source: com.netflix.ninja

  # YouTube
  - type: action
    icon: mdi:youtube
    tap_action:
      action: call-service
      service: media_player.select_source
      data:
        entity_id: media_player.android_tv_salon
        source: com.google.android.youtube.tv

  # Plex
  - type: action
    icon: mdi:plex
    tap_action:
      action: call-service
      service: media_player.select_source
      data:
        entity_id: media_player.android_tv_salon
        source: com.plexapp.android

  # Disney+
  - type: action
    icon: mdi:movie-open
    tap_action:
      action: call-service
      service: media_player.select_source
      data:
        entity_id: media_player.android_tv_salon
        source: com.disney.disneyplus

  # Spotify
  - type: action
    icon: mdi:spotify
    tap_action:
      action: call-service
      service: media_player.select_source
      data:
        entity_id: media_player.android_tv_salon
        source: com.spotify.tv.android

  # Kodi
  - type: action
    icon: mdi:kodi
    tap_action:
      action: call-service
      service: media_player.select_source
      data:
        entity_id: media_player.android_tv_salon
        source: org.xbmc.kodi

  # HBO Max
  - type: action
    icon: mdi:alpha-h-box
    tap_action:
      action: call-service
      service: media_player.select_source
      data:
        entity_id: media_player.android_tv_salon
        source: com.hbo.hbonow
```

**Package IDs comunes:**

| App | Package ID |
|-----|-----------|
| Netflix | `com.netflix.ninja` |
| YouTube | `com.google.android.youtube.tv` |
| Disney+ | `com.disney.disneyplus` |
| Plex | `com.plexapp.android` |
| Spotify | `com.spotify.tv.android` |
| HBO Max | `com.hbo.hbonow` |
| Prime Video | `com.amazon.amazonvideo.livingroom` |
| Kodi | `org.xbmc.kodi` |
| Jellyfin | `org.jellyfin.androidtv` |
| Apple TV+ | `com.apple.atve.android.appletv` |
| Twitch | `tv.twitch.android.app` |
| VLC | `org.videolan.vlc` |

> **Tip**: Para encontrar el package ID de cualquier app, usa el servicio:
> ```yaml
> service: pyt_androidtv.adb_command
> data:
>   entity_id: media_player.android_tv_salon
>   command: "pm list packages | grep netflix"
> ```

---

### Control Remoto D-pad

Recrear un control remoto con flechas usando Template Cards de Mushroom:

```yaml
type: vertical-stack
cards:
  # --- Fila superior: Arriba + Home ---
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: ""
        icon: mdi:arrow-up-bold
        icon_color: blue
        layout: vertical
        tap_action:
          action: call-service
          service: media_player.play_media
          data:
            entity_id: media_player.android_tv_salon
            media_content_type: send_key
            media_content_id: UP
      - type: custom:mushroom-template-card
        primary: ""
        icon: mdi:home
        icon_color: amber
        layout: vertical
        tap_action:
          action: call-service
          service: media_player.play_media
          data:
            entity_id: media_player.android_tv_salon
            media_content_type: send_key
            media_content_id: HOME

  # --- Fila central: Izquierda + OK + Derecha ---
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: ""
        icon: mdi:arrow-left-bold
        icon_color: blue
        layout: vertical
        tap_action:
          action: call-service
          service: media_player.play_media
          data:
            entity_id: media_player.android_tv_salon
            media_content_type: send_key
            media_content_id: LEFT
      - type: custom:mushroom-template-card
        primary: "OK"
        icon: mdi:checkbox-blank-circle
        icon_color: green
        layout: vertical
        tap_action:
          action: call-service
          service: media_player.play_media
          data:
            entity_id: media_player.android_tv_salon
            media_content_type: send_key
            media_content_id: ENTER
      - type: custom:mushroom-template-card
        primary: ""
        icon: mdi:arrow-right-bold
        icon_color: blue
        layout: vertical
        tap_action:
          action: call-service
          service: media_player.play_media
          data:
            entity_id: media_player.android_tv_salon
            media_content_type: send_key
            media_content_id: RIGHT

  # --- Fila inferior: Abajo + Back ---
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: ""
        icon: mdi:arrow-down-bold
        icon_color: blue
        layout: vertical
        tap_action:
          action: call-service
          service: media_player.play_media
          data:
            entity_id: media_player.android_tv_salon
            media_content_type: send_key
            media_content_id: DOWN
      - type: custom:mushroom-template-card
        primary: ""
        icon: mdi:keyboard-backspace
        icon_color: red
        layout: vertical
        tap_action:
          action: call-service
          service: media_player.play_media
          data:
            entity_id: media_player.android_tv_salon
            media_content_type: send_key
            media_content_id: BACK
```

**Personalizar colores de íconos:**

Usa `icon_color` con estos valores:
- `red`, `pink`, `purple`, `deep-purple`, `indigo`, `blue`, `light-blue`
- `cyan`, `teal`, `green`, `light-green`, `lime`, `yellow`, `amber`, `orange`
- `deep-orange`, `brown`, `grey`, `blue-grey`

---

### Panel completo (todo junto)

Combina todas las tarjetas en un panel tipo control remoto:

```yaml
type: vertical-stack
cards:
  # Título
  - type: custom:mushroom-title-card
    title: "Android TV"
    subtitle: "{{ states('media_player.android_tv_salon') }}"

  # Media Player principal
  - type: custom:mushroom-media-player-card
    entity: media_player.android_tv_salon
    use_media_info: true
    show_volume_level: true
    collapsible_controls: true
    media_controls:
      - on_off
      - previous
      - play_pause_stop
      - next
    volume_controls:
      - volume_mute
      - volume_set
    fill_container: true

  # Apps favoritas
  - type: custom:mushroom-chips-card
    alignment: center
    chips:
      - type: action
        icon: mdi:netflix
        tap_action:
          action: call-service
          service: media_player.select_source
          data:
            entity_id: media_player.android_tv_salon
            source: com.netflix.ninja
      - type: action
        icon: mdi:youtube
        tap_action:
          action: call-service
          service: media_player.select_source
          data:
            entity_id: media_player.android_tv_salon
            source: com.google.android.youtube.tv
      - type: action
        icon: mdi:plex
        tap_action:
          action: call-service
          service: media_player.select_source
          data:
            entity_id: media_player.android_tv_salon
            source: com.plexapp.android
      - type: action
        icon: mdi:spotify
        tap_action:
          action: call-service
          service: media_player.select_source
          data:
            entity_id: media_player.android_tv_salon
            source: com.spotify.tv.android

  # D-pad navegación
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: ""
        icon: mdi:arrow-up-bold
        icon_color: blue
        layout: vertical
        tap_action:
          action: call-service
          service: media_player.play_media
          data:
            entity_id: media_player.android_tv_salon
            media_content_type: send_key
            media_content_id: UP
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: ""
        icon: mdi:arrow-left-bold
        icon_color: blue
        layout: vertical
        tap_action:
          action: call-service
          service: media_player.play_media
          data:
            entity_id: media_player.android_tv_salon
            media_content_type: send_key
            media_content_id: LEFT
      - type: custom:mushroom-template-card
        primary: "OK"
        icon: mdi:circle
        icon_color: green
        layout: vertical
        tap_action:
          action: call-service
          service: media_player.play_media
          data:
            entity_id: media_player.android_tv_salon
            media_content_type: send_key
            media_content_id: ENTER
      - type: custom:mushroom-template-card
        primary: ""
        icon: mdi:arrow-right-bold
        icon_color: blue
        layout: vertical
        tap_action:
          action: call-service
          service: media_player.play_media
          data:
            entity_id: media_player.android_tv_salon
            media_content_type: send_key
            media_content_id: RIGHT
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: ""
        icon: mdi:arrow-down-bold
        icon_color: blue
        layout: vertical
        tap_action:
          action: call-service
          service: media_player.play_media
          data:
            entity_id: media_player.android_tv_salon
            media_content_type: send_key
            media_content_id: DOWN
      - type: custom:mushroom-template-card
        primary: ""
        icon: mdi:keyboard-backspace
        icon_color: red
        layout: vertical
        tap_action:
          action: call-service
          service: media_player.play_media
          data:
            entity_id: media_player.android_tv_salon
            media_content_type: send_key
            media_content_id: BACK
```

---

### Botón de toque en pantalla

Usar el servicio `pyt_androidtv.tap` desde un botón Mushroom:

```yaml
type: custom:mushroom-template-card
primary: "Tap centro"
secondary: "Toca el centro de la pantalla"
icon: mdi:gesture-tap
icon_color: purple
tap_action:
  action: call-service
  service: pyt_androidtv.tap
  data:
    entity_id: media_player.android_tv_salon
    x: 960
    y: 540
```

---

### Teclado virtual

Botón que abre un prompt para escribir texto en el dispositivo:

```yaml
type: custom:mushroom-template-card
primary: "Escribir texto"
secondary: "Abrir teclado"
icon: mdi:keyboard
icon_color: teal
tap_action:
  action: call-service
  service: pyt_androidtv.input_text
  data:
    entity_id: media_player.android_tv_salon
    text: "texto de búsqueda"
```

> **Tip avanzado**: Para un teclado interactivo real, puedes crear un
> `input_text` helper en HA y una automatización que envíe el texto
> al dispositivo cuando cambie:
>
> ```yaml
> # En automations.yaml
> automation:
>   - alias: "Enviar texto a Android TV"
>     trigger:
>       - platform: state
>         entity_id: input_text.android_tv_keyboard
>     action:
>       - service: pyt_androidtv.input_text
>         data:
>           entity_id: media_player.android_tv_salon
>           text: "{{ states('input_text.android_tv_keyboard') }}"
>       - service: input_text.set_value
>         data:
>           entity_id: input_text.android_tv_keyboard
>           value: ""
> ```

---

## Automatizaciones

### Apagar TV al salir de casa

```yaml
automation:
  - alias: "Apagar TV al salir"
    trigger:
      - platform: state
        entity_id: person.tu_nombre
        from: "home"
    action:
      - service: media_player.turn_off
        target:
          entity_id: media_player.android_tv_salon
```

### Abrir Netflix a las 20:00

```yaml
automation:
  - alias: "Netflix hora de cena"
    trigger:
      - platform: time
        at: "20:00:00"
    condition:
      - condition: state
        entity_id: person.tu_nombre
        state: "home"
    action:
      - service: media_player.turn_on
        target:
          entity_id: media_player.android_tv_salon
      - delay: "00:00:05"
      - service: media_player.select_source
        data:
          entity_id: media_player.android_tv_salon
          source: com.netflix.ninja
```

### Bajar volumen por la noche

```yaml
automation:
  - alias: "Volumen nocturno"
    trigger:
      - platform: time
        at: "22:00:00"
    condition:
      - condition: state
        entity_id: media_player.android_tv_salon
        state: "playing"
    action:
      - service: media_player.volume_set
        data:
          entity_id: media_player.android_tv_salon
          volume_level: 0.3
```

---

## Solución de problemas

| Problema | Solución |
|----------|----------|
| "No se pudo conectar" | Verificar que ADB está habilitado y la IP es correcta |
| Entidad no disponible | Reiniciar HA, verificar que el TV está encendido |
| Volumen no funciona | Algunas apps bloquean el control de volumen externo |
| Apps no aparecen en source_list | Esperar al siguiente ciclo de actualización (10 seg) |
| Mushroom no muestra controles | Verificar que `media_controls` y `volume_controls` están configurados |
| "Servicio no encontrado" | Reiniciar HA después de instalar la integración |

### Logs de depuración

Agregar a `configuration.yaml` para ver logs detallados:

```yaml
logger:
  default: info
  logs:
    custom_components.pyt_androidtv: debug
    pyt_androidtv: debug
```

### Verificar conexión manualmente

Desde **Herramientas de desarrollador > Servicios**:

```yaml
service: pyt_androidtv.adb_command
data:
  entity_id: media_player.android_tv_salon
  command: "getprop ro.product.model"
```

Si funciona, verás el modelo del dispositivo en los logs.

---

## Créditos

- Librería: [pyt-androidtv](https://github.com/ydiaz1699/pyt-androidtv)
- Tarjetas UI: [Mushroom](https://github.com/piitaya/lovelace-mushroom) por piitaya
- Integración original: [python-androidtv](https://github.com/JeffLIrion/python-androidtv) por Jeff Irion


---

## Nuevas Funcionalidades (v1.1)

### Entidades adicionales

Al configurar un dispositivo ahora se crean **3 entidades** adicionales:

| Entidad | Tipo | Descripción |
|---------|------|-------------|
| `sensor.android_tv_salon_apps_instaladas` | sensor | Número de apps instaladas (lista en atributos) |
| `sensor.android_tv_salon_apps_en_ejecucion` | sensor | Número de apps ejecutándose |
| `camera.android_tv_salon_pantalla` | camera | Captura de pantalla en vivo |

---

### Captura de pantalla en vivo (Camera)

La entidad camera muestra la pantalla del dispositivo como imagen. Se actualiza al abrir la tarjeta (con caché de 5 segundos para no saturar ADB).

```yaml
# Tarjeta picture-entity para ver la pantalla del TV
type: picture-entity
entity: camera.android_tv_salon_pantalla
show_state: false
show_name: false
```

---

### Sensor de Apps Instaladas

Útil para crear automatizaciones basadas en las apps del dispositivo:

```yaml
# Mostrar el número de apps como chip
type: custom:mushroom-chips-card
chips:
  - type: entity
    entity: sensor.android_tv_salon_apps_instaladas
    icon: mdi:apps
```

La lista completa está en el atributo `apps` del sensor.

---

### Servicio: Buscar en App

Combina abrir una app + escribir una búsqueda automáticamente:

```yaml
# Buscar "Stranger Things" en Netflix
service: pyt_androidtv.search_in_app
data:
  entity_id: media_player.android_tv_salon
  app: com.netflix.ninja
  query: "Stranger Things"
  delay_s: 3
```

Tarjeta Mushroom para búsqueda rápida:

```yaml
type: custom:mushroom-template-card
primary: "Buscar en Netflix"
secondary: "Stranger Things"
icon: mdi:magnify
icon_color: red
tap_action:
  action: call-service
  service: pyt_androidtv.search_in_app
  data:
    entity_id: media_player.android_tv_salon
    app: com.netflix.ninja
    query: "Stranger Things"
    delay_s: 3
```

---

### Servicio: Grabar Pantalla

Graba la pantalla del dispositivo y descarga el MP4 a `/config/www/pyt_androidtv/`:

```yaml
service: pyt_androidtv.record_screen
data:
  entity_id: media_player.android_tv_salon
  duration_s: 30
  filename: "grabacion_tv.mp4"
```

Al completarse, recibirás una notificación persistente con la ubicación del archivo.
El video estará disponible en: `http://tu-ha:8123/local/pyt_androidtv/grabacion_tv.mp4`

---

### Apps Favoritas desde la UI (OptionsFlow)

Después de configurar el dispositivo, puedes agregar apps favoritas desde la interfaz:

1. Ir a **Ajustes > Integraciones > pyt-androidtv**
2. Clic en **Configurar** (icono de engranaje)
3. En el campo "Apps favoritas", escribir los package IDs separados por coma
4. También puedes ajustar el intervalo de actualización y reintentos de reconexión

Las apps favoritas configuradas se exponen como atributo `favorite_apps` en la entidad media_player.

---

### Reconexión Automática

Si el dispositivo se desconecta (reinicio, pérdida de WiFi, etc.), la integración intentará reconectar automáticamente:

- Hasta 3 intentos por ciclo de actualización (configurable en opciones)
- Logging informativo de cada intento
- Reconexión transparente sin reiniciar HA

---

### Resumen de todos los servicios disponibles

| Servicio | Descripción |
|----------|-------------|
| `pyt_androidtv.adb_command` | Comando ADB personalizado |
| `pyt_androidtv.tap` | Toque en coordenadas |
| `pyt_androidtv.swipe` | Deslizamiento en pantalla |
| `pyt_androidtv.input_text` | Escribir texto |
| `pyt_androidtv.search_in_app` | Abrir app y buscar texto |
| `pyt_androidtv.record_screen` | Grabar y descargar pantalla |

Todos los servicios requieren `entity_id` y lo usan correctamente para dirigirse al dispositivo correcto (soporta múltiples dispositivos).
