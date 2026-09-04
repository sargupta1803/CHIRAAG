# CHIRAAG

**Safer walking routes after dark, backed by evidence you can inspect.**

CHIRAAG finds walking routes that avoid unlit stretches of road, and shows you
why it made every choice. Click any street on the map and it tells you how much
of that street is covered by detected street lights, how long the longest dark
gap is, and where that evidence came from.

Crucially, it distinguishes **"we measured this street and it is dark"** from
**"we have no imagery here."** A street with no evidence is never scored as
dark, never counted toward a safety claim, and is drawn with hatching on the
map so you can see where the data runs out.

Built for Smart India Hackathon. Pilot area: central New Delhi.

---

## What it does

Give it an origin and a destination and it returns two routes:

- **Shortest** — plain distance, the route you would walk anyway
- **CHIRAAG / safer** — minimises unlit exposure, within a detour budget you set

Plus an evidence summary: how many metres of unlit road the safer route avoids,
how much extra walking that costs, and what percentage of the route we actually
have lighting data for.

A real result from the pilot area, India Gate to Connaught Place:

| | distance | unlit road | observed |
|---|---|---|---|
| Shortest | 3,287 m | 238 m | 73% |
| CHIRAAG | 3,302 m | 133 m | 77% |

**105 m less unlit road for 15 m of extra walking.**

---

## How it works

```
OpenStreetMap  ──┐
                 ├──► snap lights to roads ──► merge lit intervals ──► score
Mapillary     ──┘         (25 m radius)          (±25 m per light)      │
street-light                                                            ▼
detections                                                      PostGIS: road_segments
                                                                        │
                                                                        ▼
                                                    NetworkX graph ──► λ-sweep Dijkstra
                                                                        │
                                                                        ▼
                                                                   two routes + evidence
```

**Scoring.** Each street light is treated as lighting a ±25 m stretch of the
road it snaps to. Overlapping stretches merge, and what is left over becomes
`dark_fraction` and `longest_gap_m`.

**Routing.** Edge cost is `length + λ · (dark_fraction · length)`. The router
runs Dijkstra at λ=0 for the baseline, then sweeps λ ∈ {0.5, 1, 2, 5, 10, 20},
discards any candidate longer than `alpha × baseline`, and keeps the one with
the lowest unlit exposure.

**Unknown handling.** Segments with no imagery are never assigned a
`dark_fraction`. Under the `neutral` policy they cost plain distance; under
`avoid` they take an additive penalty. They are never treated as dark.

**Time of day.** The hour applies a bounded multiplier to the safety search —
1.00× during daylight, 1.15× from 19:00, 1.30× from 22:00. It makes routing
more conservative at night; it does not alter the stored evidence.

---

## Repository layout

```
chiraag_frontend/     React 19 + Vite + MapLibre GL
igdtw_backend/
  app/                FastAPI service (read-only over PostGIS)
    models/           SQLAlchemy models
    routers/          /api/v1/route, /api/v1/evidence
    schemas/          Pydantic request/response models
    services/         graph_builder, routing
  pipeline/           Offline ingestion and scoring (not used at request time)
  tests/              pytest
```

The API never fetches or scores anything. The pipeline is a batch job that
populates the database; the API only reads it.

---

## Running locally

### Prerequisites

- Docker Desktop
- Node.js 18+
- A [MapTiler](https://www.maptiler.com/) API key (free tier is fine)
- A [Mapillary](https://www.mapillary.com/dashboard/developer) access token,
  only if you want to ingest fresh data

### 1. Backend

```bash
cd igdtw_backend
docker-compose up -d --build
```

This starts PostGIS on port 5434 and the API on port 8000. Tables are created
automatically on first boot.

Check it:

```bash
curl http://localhost:8000
```

You should get `{"status":"online", ...}`. Interactive API docs are at
`http://localhost:8000/docs`.

### 2. Load data

The pipeline runs inside the API container.

**Option A — restore the pilot dataset (fast).** `chiraag_data.sql` in
`igdtw_backend/` holds the ingested central Delhi network:

```bash
docker cp chiraag_data.sql igdtw_backend-db-1:/tmp/chiraag_data.sql
docker-compose exec db psql -U chiraag -d chiraag -f /tmp/chiraag_data.sql
```

**Option B — ingest fresh (slow, needs a Mapillary token).**

```bash
docker-compose exec api python -m pipeline.run_ingestion \
  --lat 28.6180 --lon 77.2200 --radius 2500 \
  --bbox "77.1944,28.5954,77.2456,28.6406" \
  --mapillary-token "YOUR_TOKEN"
```

**`--radius` and `--bbox` must cover the same area.** `--radius` controls the
OSM street pull (as a square of side `2 × radius`); `--bbox` controls the
Mapillary light query. If the bbox is smaller, streets outside it can never be
scored and coverage collapses. Derive the bbox from your ingested extent:

```bash
docker-compose exec db psql -U chiraag -d chiraag -t -c \
  "SELECT ST_XMin(e)||','||ST_YMin(e)||','||ST_XMax(e)||','||ST_YMax(e)
   FROM (SELECT ST_Extent(geom) AS e FROM road_segments) t;"
```

Verify whichever option you used:

```bash
docker-compose exec db psql -U chiraag -d chiraag -c \
  "SELECT observation_state, count(*) FROM road_segments GROUP BY 1;"
```

### 3. Frontend

```bash
cd chiraag_frontend
npm install
```

Create `chiraag_frontend/.env`:

```
VITE_API_URL=http://localhost:8000
VITE_MAPTILER_KEY=your_maptiler_key
```

```bash
npm run dev
```

Open `http://localhost:5173`. It loads with a route already drawn — click a
preset chip to try others, or type any place in central Delhi.

### 4. Tests

```bash
cd igdtw_backend
docker-compose exec api python -m pytest tests/ -q
```

15 tests. The routing tests need no database; only `test_api.py` does.

---

## Pipeline reference

`python -m pipeline.run_ingestion [options]`

| flag | purpose |
|---|---|
| `--lat` / `--lon` | Centre point for the OSM street pull. Preferred over `--place`. |
| `--radius` | Half-width in metres of the OSM square. Default 1000. |
| `--place` | Place name for OSMnx. Only works for names that resolve to a polygon boundary — landmarks like "Connaught Place" resolve to a point and will fail. |
| `--bbox` | Mapillary query box, `minLon,minLat,maxLon,maxLat`. Required unless `--skip-lights`. |
| `--mapillary-token` | Mapillary API token. Required unless `--skip-lights`. |
| `--skip-osm` | Reuse existing streets. |
| `--skip-lights` | Reuse existing lights. Use with `--skip-osm` to re-score only. |

Re-running is safe. Streets are deduplicated in PostGIS with `ST_Equals`
(direction-agnostic, so a street stored A→B matches an incoming B→A), and
lights are deduplicated by `mapillary_id`. Mapillary occasionally returns HTTP
500 for large boxes; the ingester retries by subdividing into quadrants.

---

## API reference

Base URL `http://localhost:8000`. Full interactive docs at `/docs`.

### `POST /api/v1/route`

```json
{
  "origin":      { "lat": 28.612945, "lon": 77.229466 },
  "destination": { "lat": 28.631540, "lon": 77.216742 },
  "alpha": 1.3,
  "unknown_policy": "neutral",
  "hour": 23
}
```

| field | default | notes |
|---|---|---|
| `alpha` | 1.20 | Detour cap, 1.0–2.0. 1.3 allows a 30% longer route. |
| `unknown_policy` | `neutral` | `avoid`, `neutral`, or `show_gaps`. |
| `hour` | 12 | 0–23. Applies the time-of-day weighting. |

Response contains `baseline_route` and `chiraag_route`, each with:

- `nodes` — flat `[lon, lat]` polyline following the real street geometry
- `segments` — per-street breakdown with `road_id`, `dark_fraction`,
  `observation_state` and its own coordinates (this is what makes streets
  clickable on the map)
- `metrics` — `total_length_m`, `unlit_length_m`, `unknown_length_m`,
  `dark_fraction`, `coverage_ratio`

Plus `evidence_summary` with `unlit_meters_avoided`, `extra_distance_m` and
`safety_gain_percent`.

**Always read `coverage_ratio` alongside `unlit_length_m`.** A route with no
observation returns `unlit_length_m: 0.0`, which means "we have not looked", not
"there is no dark road". The frontend surfaces this; any other client should too.

Returns **400** if an endpoint is more than 250 m from the nearest mapped
street, or if no walking route exists between the two points.

### `GET /api/v1/evidence/segment/{id}`

Returns `road_id`, `length_m`, `dark_fraction`, `longest_gap_m`,
`observation_state`. The last three are `null` for unobserved streets.

### `POST /api/v1/evidence/audit`

```json
{ "road_segment_id": 489, "rating": 2.0, "observed_light_count": 3 }
```

Records a ground-truth rating (0 = pitch dark, 5 = well lit) and recomputes
that segment's `dark_fraction` as `1 - mean(rating)/5`. Ratings are averaged
across all audits for the segment, so one outlier cannot flip a street.
Audited evidence overrides imagery inference, and the change takes effect on
the next route request.

---

## Known limitations

Worth stating plainly rather than being asked.

**Coverage is 10% of the network.** 1,212 of 11,982 segments have lighting
evidence. Per-route coverage is what matters and is often much higher — the
pilot corridors run at 60–90% — but plenty of routes will honestly report
"not enough data".

**Darkness is only measurable where lights exist.** Because `dark_fraction`
comes from detected lights, streets with no detections are unobserved rather
than dark. A genuinely pitch-black street and a street with no Mapillary
coverage are currently indistinguishable. Fixing this needs Mapillary *image
coverage* ingested separately from *light detections*, so absence of lights in
an imaged area can be scored as dark.

**Light-to-road attribution is ambiguous on divided roads.** `sjoin_nearest`
assigns each detection to one centreline, which over-attributes poles from
medians and service lanes on wide avenues. This is why the evidence drawer
reports lit coverage rather than a pole count. Network-wide the clustered
density comes to 34.7 poles/km, which matches real urban street lighting.

**The 25 m light radius is an assumption**, not a measurement. It is a
reasonable figure for urban street lighting but it is not derived from lamp
height, output, or road width.

**Geographic scope is a 5 km box in central Delhi.** Requests outside it are
rejected with an explanatory 400 rather than being silently snapped to the
edge of the data.

---

## Deployment

The pilot runs on Vercel (frontend), Render (backend, Docker), and Supabase
with PostGIS (database, Mumbai region).

Backend environment variables:

```
POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
POSTGRES_SSLMODE=require
ALLOWED_ORIGINS_RAW=https://your-frontend.vercel.app
```

`ALLOWED_ORIGINS_RAW` is compared as an exact string — no trailing slash, and
scheme included, or CORS preflight will fail with a 400.

`DATABASE_URL_OVERRIDE` accepts a full connection string if your host provides
one instead of separate values.

Frontend build variables are `VITE_API_URL` and `VITE_MAPTILER_KEY`. Note that
Vite inlines `VITE_`-prefixed values into the bundle, so the MapTiler key is
visible to anyone who opens devtools — restrict it to your domain in the
MapTiler dashboard.

---

## Tech stack

**Backend** FastAPI · SQLAlchemy · GeoAlchemy2 · PostGIS · NetworkX · Shapely
**Pipeline** OSMnx · GeoPandas · Mapillary API
**Frontend** React 19 · Vite · MapLibre GL · MapTiler

## Data sources

Street geometry from [OpenStreetMap](https://www.openstreetmap.org/) via OSMnx
(ODbL). Street-light detections from [Mapillary](https://www.mapillary.com/)
map features. Basemap tiles from [MapTiler](https://www.maptiler.com/).
