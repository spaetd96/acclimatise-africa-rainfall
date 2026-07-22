# `download_destine.py` — DestinE Climate DT Data Download Script

Command-line tool to download climate model data from the DestinE Climate DT
using Polytope / earthkit-data.  Supports ICON, IFS-FESOM, and IFS-NEMO models
with configurable temporal, spatial, and variable selection.

**Requirements:** `conda activate destine` and `pip install -r requirements.txt`

## Quick-start examples

```bash
# Single date, single parameter
python get-data/download_destine.py --model ICON --experiment cont \
    --date 19900102 --param 134

# Date range with multiple parameters
python get-data/download_destine.py --model IFS-FESOM --experiment SSP3-7.0 \
    --date 20200601 --end-date 20200630 \
    --param tp/2t --time 0000/0600/1200/1800

# Monthly data (clmn stream)
python get-data/download_destine.py --model IFS-FESOM --experiment hist \
    --date 20100601 --param avg_2t --data-stream clmn

# Dry-run: print the request dict without downloading
python get-data/download_destine.py --model ICON --experiment hist \
    --date 20000615 --param tp --dry-run
```

## Bounding-box cropping (`--bbox`)

Crop downloaded data to a geographic region using server-side spatial
subsetting.  The argument is four comma-separated values:

```
--bbox south,west,north,east
```

All coordinates are in **decimal degrees**.  This injects a `feature` key
into the Polytope request, so Polytope only returns cells inside the box.

### Examples

```bash
# Horn of Africa (lat 5–10°N, lon 44–49°E)
python get-data/download_destine.py --model ICON --experiment hist \
    --date 20000615 --param tp --bbox 5,44,10,49

# Sahel (lat 10°S–25°N, lon 20°W–55°E) — use = for negative values
python get-data/download_destine.py --model IFS-FESOM --experiment SSP3-7.0 \
    --date 20400601 --param tp --bbox="-10,-20,25,55"
```

### Grid type

Bounding-box requests return data on the **native HEALPix/unstructured grid**
(dimension `points` with `latitude`/`longitude` coordinates).  Use
`earthkit.plots.Map.point_cloud()` for plotting, or work with the xarray
data directly via `to_xarray()`.

## Daily aggregation (`--daily`)

Fetch hourly (`clte`) data and aggregate to **daily means** on the fly.
Each day's download is converted to xarray, resampled with
`.resample(time="1D").mean()`, and saved as a compressed netCDF file.

```bash
# Single day → one daily-mean file
python get-data/download_destine.py --model ICON --experiment hist \
    --date 20000601 --param tp --daily

# Multi-day range → one daily-mean file per day
python get-data/download_destine.py --model ICON --experiment hist \
    --date 20000601 --end-date 20000630 --param tp --daily --output ./data/daily
```

### Behaviour

| Aspect | Detail |
|--------|--------|
| Data stream | Forces `--data-stream clte` (hourly data is required) |
| Default hours | All 24 hours (`0000/0100/.../2300`) unless `--time` is explicitly set |
| Output format | Compressed netCDF (`{param}_{date}_daily.nc`) |
| Incompatible with | `--use-client`, `--data-stream clmn` |

### Output file names

```
tp_20000601_daily.nc
tp_20000602_daily.nc
...
tp_20000630_daily.nc
```

## Full option reference

### Required arguments

| Option | Type | Description |
|--------|------|-------------|
| `--model` | one of `ICON`, `IFS-FESOM`, `IFS-NEMO` | Climate model to query |
| `--experiment` | `cont`, `hist`, `SSP3-7.0` | Experiment / scenario |
| `--date` | `YYYYMMDD` | Date (or start date with `--end-date`) |
| `--param` | string | Parameter code(s), slash-separated (see below) |

### Optional arguments

| Option | Default | Description |
|--------|---------|-------------|
| `--end-date` | — | End date `YYYYMMDD` for date range (inclusive) |
| `--time` | `0000` | Time(s) in `HHMM`, e.g. `0000/0600/1200/1800` |
| `--levtype` | `sfc` | Level type: `sfc`, `pl`, `hl`, `sol`, `o2d`, `o3d` |
| `--data-stream` | `clte` | `clte` (hourly) or `clmn` (monthly) |
| `--realization` | `1` | Ensemble realization number |
| `--output`, `-o` | `./data` | Output directory |
| `--stream` | off | Stream data directly (no local cache) |
| `--use-client` | off | Use low-level `polytope-client` instead of `earthkit-data` |
| `--request-key` | — | Extra key=value for the Polytope request (repeatable) |
| `--email` | — | DestinE Platform email (for `--use-client`) |
| `--api-key` | — | DestinE Platform API key (for `--use-client`) |
| `--dry-run` | off | Print the request dict without downloading |
| `--bbox` | — | Bounding box: `south,west,north,east` (degrees) |
| `--daily` | off | Aggregate hourly data to daily means, output as netCDF |

## Parameter codes

### Hourly `clte` stream parameters

| Short name | Numeric code | Description |
|------------|-------------|-------------|
| `sp` | `134` | Surface pressure |
| `10u` | `165` | 10 m U wind component |
| `10v` | `166` | 10 m V wind component |
| `2t` | `167` | 2 m temperature |
| `2d` | `168` | 2 m dewpoint temperature |
| `tp` | `228228` | Total precipitation |
| `msl` | `151` | Mean sea level pressure |
| `skt` | `235` | Skin temperature |

### Monthly `clmn` stream parameters (use `--data-stream clmn`)

| Short name | Description |
|------------|-------------|
| `avg_2t` | 2 m temperature (monthly mean) |
| `avg_tprate` | Total precipitation rate (monthly mean) |
| `avg_sp` | Surface pressure (monthly mean) |
| `avg_msl` | Mean sea level pressure (monthly mean) |
| `avg_tcc` | Total cloud cover (monthly mean) |
| `avg_10u` | 10 m U wind (monthly mean) |
| `avg_10v` | 10 m V wind (monthly mean) |
| `avg_skt` | Skin temperature (monthly mean) |

## Experiment → server mapping

| Experiment | Activity | Date range | Server |
|-----------|----------|------------|--------|
| `cont` | `baseline` | ~1990–2014 | LUMI (ICON/IFS-FESOM) or MN5 (IFS-NEMO) |
| `hist` | `baseline` | ~1990–2014 | LUMI (ICON/IFS-FESOM) or MN5 (IFS-NEMO) |
| `SSP3-7.0` | `projections` | ~2020–2050 | LUMI (ICON/IFS-FESOM) or MN5 (IFS-NEMO) |

| Model | Server address |
|-------|---------------|
| `ICON`, `IFS-FESOM` | `polytope.lumi.apps.dte.destination-earth.eu` |
| `IFS-NEMO` | `polytope.mn5.apps.dte.destination-earth.eu` |

## Troubleshooting

### Authentication errors

Ensure you have a valid `~/.polytopeapirc` file with your DestinE Platform
credentials.  See [`docs/polytope_setup.md`](polytope_setup.md) for setup
instructions.

### "No data returned" or size mismatch

- Check that the parameter exists for your model/stream/levtype combination.
  Use `get-data/03_lazy_browse_portfolio.ipynb` to browse available variables.
- Verify the date is within the experiment's valid range (see table above).
- Ensure the correct server address is used (LUMI vs MN5 — the script
  auto-selects based on `--model`).

### Daily aggregation fails with `--use-client`

`--daily` is incompatible with `--use-client` because daily aggregation
requires the earthkit-data GRIB object for `to_xarray()` conversion.
Use the default earthkit-data path (omit `--use-client`).

### Large bounding boxes

Bounding-box requests return data on the native HEALPix grid.  Very large
regions (e.g. global) may return millions of points and exceed memory
limits.  For global analysis, consider using the Zarr-backed
`PolytopeZarrStore` approach (see `analysis/sahel_rainfall_trends.ipynb`).

## See also

- [`docs/polytope_setup.md`](polytope_setup.md) — Polytope authentication setup
- [`docs/polytope_usage.md`](polytope_usage.md) — Detailed Polytope API reference
- [`get-data/destine_portfolio.py`](../get-data/destine_portfolio.py) — Full variable catalogue
- [`get-data/03_lazy_browse_portfolio.ipynb`](../get-data/03_lazy_browse_portfolio.ipynb) — Interactive data browser
- [`analysis/sahel_rainfall_trends.ipynb`](../analysis/sahel_rainfall_trends.ipynb) — Example bounding-box + monthly analysis
- [`analysis/seasonality_hornofafrica.ipynb`](../analysis/seasonality_hornofafrica.ipynb) — Example bounding-box + hourly analysis