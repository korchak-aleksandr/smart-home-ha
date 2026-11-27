# Outdoor conditions: air quality, UV, Saharan dust, sea temperature

Goal: one colored air-quality index on the Home Assistant home page (like the official app), with all pollutant
values one tap away, plus UV and sea temperature. Built-in HA integrations only: no custom code, no API keys.

Config: [`stack/ha-packages/outdoor.yaml`](../../stack/ha-packages/outdoor.yaml), details page:
[`stack/ha-dashboards/outdoor.yaml`](../../stack/ha-dashboards/outdoor.yaml), index pictures:
[`stack/ha-www/air-quality/`](../../stack/ha-www/air-quality/).

## Sources

| Data | Source | Kind | HA integration |
|------|--------|------|----------------|
| Station index 1–4, PM10, PM2.5, O₃, NO₂, NO, NOx, SO₂, CO, benzene | [Cyprus air-quality network](https://www.airquality.dli.mlsi.gov.cy/) (Department of Labour Inspection), the same data as its iPhone app | **measured**, hourly | [Scrape](https://www.home-assistant.io/integrations/scrape/) (reads values from the station's web page) |
| UV index (now, max today), Saharan dust | [Open-Meteo Air Quality](https://open-meteo.com/en/docs/air-quality-api) (CAMS model) | model | [RESTful](https://www.home-assistant.io/integrations/rest/) (JSON) |
| Sea surface temperature | [Open-Meteo Marine](https://open-meteo.com/en/docs/marine-weather-api) | model, grid of a few km | RESTful |

Why not [WAQI](https://www.home-assistant.io/integrations/waqi/): it relays the same stations, but converts values
to the US AQI scale, so they don't match the official app and its limits.

Open-Meteo is free for non-commercial use without a key (limit 10 000 calls a day; this setup makes ~100).

Outside Cyprus: keep the Open-Meteo part as is. For the station part, use your national network if its station page
shows plain numbers (adjust the CSS selectors), or the WAQI integration.

## Setup

1. **Pick the station.** Open the [station map](https://www.airquality.dli.mlsi.gov.cy/), click the nearest station,
   open its page and copy the URL (`https://www.airquality.dli.mlsi.gov.cy/node/<number>`). Traffic stations show
   street-level pollution, background ones the general area. Add the URL to `homeassistant/config/secrets.yaml`, so
   your town stays out of git:
   ```yaml
   air_quality_station_url: https://www.airquality.dli.mlsi.gov.cy/node/1066   # example: Nicosia - Traffic Station
   ```
2. **Home location.** Open-Meteo uses *Settings → System → General → location*, rounded to ~1 km. Approximate is
   fine. If home is inland, the marine API returns the nearest sea point.
3. **Install** (packages must be enabled once, see [08, HA metrics](../08-monitoring.md#3-home-assistant-metrics)):
   ```bash
   scp stack/ha-packages/outdoor.yaml homeserver:/tmp/pkg-outdoor.yaml
   scp stack/ha-dashboards/outdoor.yaml homeserver:/tmp/dash-outdoor.yaml
   scp stack/ha-www/air-quality/*.svg homeserver:/tmp/
   ssh homeserver 'C=/opt/smart-home/homeassistant/config
     sudo install -D -m 644 /tmp/pkg-outdoor.yaml $C/packages/outdoor.yaml
     sudo install -D -m 644 /tmp/dash-outdoor.yaml $C/dashboards/outdoor.yaml
     for n in 1 2 3 4; do sudo install -D -m 644 /tmp/$n.svg $C/www/air-quality/$n.svg; done
     cd /opt/smart-home && docker compose restart homeassistant'
   ```
   Restart HA again if `www/` didn't exist before: HA only serves `/local/` when the folder exists at start.
4. **Check:** *Settings → Entities*, search `outdoor`: 14 sensors with values. Compare them with the official app.

Polling: the station every hour (it publishes hourly values), Open-Meteo every 30 minutes. After editing
`outdoor.yaml`, restart HA: Scrape has no reload action (RESTful has `rest.reload`). Changes to the details page
show after a browser refresh.

## Home page

The default **Home** dashboard is generated automatically and stays that way. On top of it:

1. **Favorites for the summary:** home page → *Edit* → *Favorites* → add *Outdoor air quality index*, *UV index* and
   *Sea temperature*, and drag them to the top for a first row of outdoor values. The index tile shows its picture:
   a colored circle with the number, as in the official app (1 green, 2 yellow, 3 orange, 4 red).
2. **Details page** `/outdoor-conditions/details`: a small YAML dashboard registered by the package, hidden from the
   sidebar, with a back arrow to the home page. Air quality (index, every pollutant, dust, 48 h graph) and sun and sea.
   Tap a tile for its history.
3. **Shortcut to it:** home page → *Edit* → *Summaries* → add a **shortcut** (label e.g. "Outdoor", icon `mdi:tree`,
   path `/outdoor-conditions/details`) and drag it under *Weather*.

Why not an area "Outdoor" for the details: every area also appears under *Areas* on the home page, and the Home
dashboard can't hide one, so the same thing would be shown twice. Why not value tiles in *Summaries*: that column only
takes built-in summaries (lights, climate, weather, ...) and shortcuts (a label, an icon and a link, **without a
value**). Placing value tiles anywhere means taking control of the dashboard, which stops HA from adding new devices
and areas to it automatically.

Rename entities to your language in the entity settings: the entity ID stays `sensor.outdoor_*`, so the metrics
allow-list, the details page and Grafana keep working.

## Monitoring

`sensor.outdoor_*` is in the metrics allow-list (`stack/ha-packages/monitoring.yaml`). Grafana → **Home Assistant**
→ row **Outdoor**: index, UV, dust, sea, history of particles and gases, and **station data age**. If the site
changes its layout, the station sensors turn *unavailable* and show up in *Unavailable entities*. Fix it by updating
the selectors in `outdoor.yaml`.

## How the station sensors read the page

Each station page carries every value as a field with a plain number in the `content` attribute:

```html
<div class="field field--name-field-pollutant-5 ...">
  <div class="field--label">PM₁₀</div>
  <div content="38.84" class="field--item">38.84μg/m³</div>
```

Selector `.field--name-field-pollutant-<code> .field--item` + `attribute: content`. The codes are the European
(EEA) pollutant codes:

| Code | Pollutant | Code | Pollutant |
|------|-----------|------|-----------|
| 1 | SO₂ | 10 | CO |
| 5 | PM10 | 20 | benzene (C₆H₆) |
| 7 | O₃ | 38 | NO |
| 8 | NO₂ | 6001 | PM2.5 |
| 9 | NOx | | |

The station index is `.field--name-field-station-status .field--item` (1–4). Not every station measures every
pollutant. A missing one stays *unavailable*: remove it from `outdoor.yaml` for your station.

Official limits (μg/m³) for the index levels 1 low / 2 moderate / 3 high / 4 very high:

| Pollutant | 1 | 2 | 3 | 4 |
|-----------|---|---|---|---|
| PM10 | 0–50 | 50–100 | 100–200 | > 200 |
| PM2.5 | 0–25 | 25–50 | 50–100 | > 100 |
| O₃ | 0–100 | 100–140 | 140–180 | > 180 |
| NO₂ | 0–100 | 100–150 | 150–200 | > 200 |
| SO₂ | 0–150 | 150–250 | 250–350 | > 350 |
