# DestinE Climate DT Data Catalogue

Overview of available Climate Digital Twin datasets accessible via Polytope, with focus on ICON and IFS-FESOM models relevant to the Acclimatise Africa Rainfall project.

## Available Climate Models

| Model | Type | Description |
|-------|------|-------------|
| **ICON** | Atmosphere-only | Icosahedral Nonhydrostatic model, ~5 km resolution |
| **IFS-FESOM** | Coupled | IFS atmosphere (~9 km) coupled with FESOM ocean/sea-ice |
| **IFS-NEMO** | Coupled | IFS atmosphere (~9 km) coupled with NEMO ocean (~1/12°) |

## ICON — Available Simulations

### Control Simulation
- **Experiment**: `control-1950`
- **Activity**: `control`
- **Period**: Multi-decadal (at least 5 years)
- **Description**: Present-day climate simulation with fixed 1950 greenhouse gas forcing
- **Realizations**: Multiple ensemble members available

### Historical and Projection Simulations
- **Activity**: `projections`
- **Experiments**:
  - `historical` — Historical forcing (typically 1950–2014)
  - `SSP3-7.0` — Future scenario with high emissions
  - Other SSP scenarios may be available

## IFS-FESOM — Available Simulations

### Control Simulation
- **Experiment**: `control-1950`
- **Activity**: `control`
- **Period**: Multi-decadal
- **Description**: Coupled atmosphere-ocean present-day simulation

### Historical and Projection Simulations
- **Activity**: `projections`
- **Experiments**:
  - `historical` — Historical forcing
  - `SSP3-7.0` — Future scenario

### Storyline Simulations
- **Activity**: `storylines` (if available)
- **Description**: Targeted simulations exploring specific climate pathways
- For details see the [Storyline Simulations documentation](https://platform.destine.eu/docs/climate-dt-user-guide/doc/simulations/storylines.html)

## Key Surface Variables

For rainfall and climate analysis over Africa, the following surface variables are most relevant:

| Code | Variable | Short Name | Unit |
|------|----------|------------|------|
| `228228` | Total precipitation | TP | m (accumulated) |
| `167` | 2m temperature | 2T | K |
| `168` | 2m dewpoint temperature | 2D | K |
| `134` | Surface pressure | SP | Pa |
| `165` | 10m U wind component | 10U | m/s |
| `166` | 10m V wind component | 10V | m/s |
| `151` | Mean sea level pressure | MSL | Pa |
| `235` | Surface temperature | SKT | K |
| `139` | Soil temperature level 1 | STL1 | K |
| `170` | Soil moisture level 1 | SWVL1 | m³/m³ |

## Pressure Level Variables

For atmospheric column analysis, use `levtype: 'pl'`:

| Code | Variable | Levels (hPa) |
|------|----------|--------------|
| `130` | Temperature | 1000, 850, 700, 500, 300, 200, 100 |
| `131` | U wind | Same as above |
| `132` | V wind | Same as above |
| `133` | Specific humidity | Same as above |
| `157` | Relative humidity | Same as above |

## Data Structure

### Grid
Climate DT data is provided on the HEALPix grid. The standard resolution is:
- **ICON**: ~5 km native grid
- **IFS-FESOM**: ~9 km atmosphere grid

### Temporal Coverage
- **Frequency**: Hourly (some variables daily/monthly)
- **Format**: `time` key uses `HHMM` format, e.g., `0000`, `0300`, ..., `2100`
- **Date format**: `YYYYMMDD`

### Available Levels
| Level Type | Key | Purpose |
|------------|-----|---------|
| `sfc` | Surface | Surface variables (precipitation, 2m temp, 10m wind) |
| `pl` | Pressure levels | Atmospheric vertical profiles |
| `hl` | Height levels | Alternative vertical coordinate |

## Request Template for African Rainfall Analysis

```python
# African domain rainfall from ICON projections
request = {
    'activity': 'projections',
    'class': 'd1',
    'dataset': 'climate-dt',
    'date': '20500601',          # Adjust as needed
    'experiment': 'SSP3-7.0',
    'expver': '0001',
    'generation': '2',
    'levtype': 'sfc',
    'model': 'ICON',             # or 'IFS-FESOM'
    'param': '228228',           # Total precipitation
    'realization': '1',
    'resolution': 'standard',
    'stream': 'clte',
    'time': '0000',
    'type': 'fc'
}
```

## Data Discovery

### Using the Climate DT Explorer
The [polytope-examples explorer notebooks](https://github.com/destination-earth-digital-twins/polytope-examples/tree/main/climate-dt/explorer) provide interactive tools to discover available data:

1. **Monthly catalogue** — Browse monthly data availability
2. **Hourly catalogue** — Browse hourly data availability
3. **Variable lookup** — Search for variables by name or code

### Using earthkit-data
You can programmatically inspect data availability using `earthkit-data`'s request inspection features:

```python
import earthkit.data

# Check what's available (lazy evaluation)
source = earthkit.data.from_source(
    "polytope",
    "destination-earth",
    request,
    address="polytope.mn5.apps.dte.destination-earth.eu",
    stream=False
)

# Inspect metadata
print(source)
```

## Related Resources

- [DestinE Platform Data Catalogue](https://platform.destine.eu/docs/climate-dt-user-guide/doc/data/data_catalogue.html)
- [Data Structure and Keys](https://platform.destine.eu/docs/climate-dt-user-guide/doc/data/data_structure.html)
- [Ocean Model Levels](https://platform.destine.eu/docs/climate-dt-user-guide/doc/data/ocean_model_levels.html) (relevant for IFS-FESOM ocean data)
- [ECMWF Parameter Database](https://codes.ecmwf.int/grib/param-db/)