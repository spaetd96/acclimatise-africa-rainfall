#!/usr/bin/env python3
"""
Generic DestinE Climate DT Data Download Script

Downloads climate model data from DestinE using Polytope / earthkit-data.
Supports ICON, IFS-FESOM, and IFS-NEMO models with configurable temporal,
spatial, and variable selection.

Usage Examples:
    # Download ICON control simulation surface pressure for one day
    python download_destine.py --model ICON --experiment cont \
        --date 19900102 --param 134

    # Download IFS-FESOM projections for multiple days
    python download_destine.py --model IFS-FESOM --experiment SSP3-7.0 \
        --date 20200601 --end-date 20200605 \
        --param 134/165/166 --time 0000/0600/1200/1800 \
        --output ./data/fesom_proj

    # Download monthly data (clmn stream)
    python download_destine.py --model IFS-FESOM --experiment hist \
        --date 20100601 --param avg_2t --data-stream clmn

    # Use parameter short names
    python download_destine.py --model IFS-NEMO --experiment SSP3-7.0 \
        --date 20200102 --param tp/2t

    # Crop to bounding box (south, west, north, east) — use = syntax
    python download_destine.py --model ICON --experiment hist \
        --date 20000615 --param tp --bbox="5,44,10,49"

    # Download hourly data aggregated to daily means
    python download_destine.py --model ICON --experiment hist \
        --date 20000601 --end-date 20000630 --param tp --daily

    # Combine bounding box + daily aggregation
    python download_destine.py --model ICON --experiment hist \
        --date 20000601 --end-date 20000630 --param tp \
        --bbox="-10,-20,25,55" --daily --output ./data/sahel_daily

Requirements:
    conda activate destine
    pip install -r requirements.txt
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import numpy as np


# ---- Configuration ----

# Server addresses per model family
# ICON and IFS-FESOM -> LUMI  |  IFS-NEMO -> MN5
LUMI_ADDRESS = "polytope.lumi.apps.dte.destination-earth.eu"
MN5_ADDRESS  = "polytope.mn5.apps.dte.destination-earth.eu"
COLLECTION = "destination-earth"

# Default request template - most keys are standard across all Climate DT data
DEFAULT_REQUEST = {
    "class": "d1",
    "dataset": "climate-dt",
    "expver": "0001",
    "generation": "2",
    "resolution": "standard",
    "stream": "clte",
    "type": "fc",
}

# Map model -> correct Polytope server address
MODEL_ADDRESS = {
    "ICON":       LUMI_ADDRESS,
    "IFS-FESOM":  LUMI_ADDRESS,
    "IFS-NEMO":   MN5_ADDRESS,
}

# Map experiment -> correct activity keyword
EXPERIMENT_ACTIVITY = {
    "hist":      "baseline",
    "cont":      "baseline",
    "SSP3-7.0":  "projections",
}

# Parameter code reference — numeric codes for clte stream,
# shortNames for clmn stream (see destine_portfolio.py for full catalogue)
PARAM_CODES = {
    # clte hourly instantaneous / mean
    "sp": "134",         # Surface pressure (clte instantaneous)
    "10u": "165",        # 10m U wind (clte instantaneous)
    "10v": "166",        # 10m V wind (clte instantaneous)
    "2t": "167",         # 2m temperature (clte instantaneous)
    "2d": "168",         # 2m dewpoint (clte instantaneous)
    "tp": "avg_tprate",  # Total precipitation rate (alias for avg_tprate)
    "avg_tprate": "avg_tprate",  # Total precipitation rate
    "msl": "151",        # Mean sea level pressure (clte instantaneous)
    "skt": "235",        # Skin temperature (clte instantaneous)
    # clmn monthly means (use with --data-stream clmn)
    "avg_2t": "avg_2t",          # 2m temperature (monthly mean)
    "avg_sp": "avg_sp",          # surface pressure (monthly mean)
    "avg_msl": "avg_msl",        # MSL pressure (monthly mean)
    "avg_tcc": "avg_tcc",        # total cloud cover (monthly mean)
    "avg_10u": "avg_10u",        # 10m U wind (monthly mean)
    "avg_10v": "avg_10v",        # 10m V wind (monthly mean)
    "avg_skt": "avg_skt",        # skin temperature (monthly mean)
}

# Default 24-hour time string used when --daily is requested
ALL_HOURS = "/".join(f"{h:02d}00" for h in range(24))


def get_address(model: str) -> str:
    """Return the correct Polytope server address for a given model."""
    return MODEL_ADDRESS.get(model, LUMI_ADDRESS)


def get_activity(experiment: str) -> str:
    """Return the correct activity keyword for a given experiment."""
    return EXPERIMENT_ACTIVITY.get(experiment, "projections")


def safe_len(data) -> int:
    """Count fields in an earthkit-data result, even for GribData (no __len__/__iter__)."""
    try:
        return data.to_numpy().size
    except Exception:
        return 1


def parse_bbox(bbox_str: str) -> Dict[str, Any]:
    """Parse a 'south,west,north,east' string into a Polytope feature dict.

    Parameters
    ----------
    bbox_str : str
        Comma-separated coordinates: south,west,north,east (degrees).

    Returns
    -------
    dict
        Polytope ``feature`` sub-dict for a bounding-box request.

    Example
    -------
    >>> parse_bbox("5,44,10,49")
    {'type': 'boundingbox', 'points': [[10, 44], [5, 49]]}
    """
    parts = [float(x.strip()) for x in bbox_str.split(",")]
    if len(parts) != 4:
        raise ValueError(
            f"Bounding box must have 4 values (south,west,north,east), "
            f"got {len(parts)}: {bbox_str}"
        )
    south, west, north, east = parts
    return {
        "type": "boundingbox",
        "points": [[north, west], [south, east]],
    }


def build_request(
    model: str,
    experiment: str,
    date: str,
    param: str,
    time: str = "0000",
    levtype: str = "sfc",
    realization: str = "1",
    extra_keys: Optional[Dict[str, str]] = None,
    bbox: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a Polytope request dictionary.

    Parameters
    ----------
    model : str
        Climate model: 'ICON', 'IFS-FESOM', 'IFS-NEMO'
    experiment : str
        Experiment name: 'cont' (control), 'hist' (historical), 'SSP3-7.0' (projections)
    date : str
        Date in YYYYMMDD format.
        'cont'/'hist' experiments typically use 1990-2014 dates,
        'SSP3-7.0' uses 2020-2050 dates.
    param : str
        Parameter code(s), slash-separated, e.g. '134' or '228228/167'.
        Can also use short names: 'tp' -> 'avg_tprate', 'avg_2t' -> 'avg_2t'.
    time : str
        Time(s) in HHMM format, e.g. '0000' or '0000/0300/.../2100'.
    levtype : str
        'sfc' (surface), 'pl' (pressure levels), 'hl' (height levels),
        'sol' (soil/snow), 'o2d' (2D ocean), 'o3d' (3D ocean).
    realization : str
        Ensemble realization number.
    extra_keys : dict, optional
        Additional key-value pairs to add/override in the request.
    bbox : str, optional
        Bounding box as 'south,west,north,east' in degrees.
        Injects a ``feature`` key for server-side spatial subsetting.

    Returns
    -------
    dict
        Polytope request dictionary.
    """
    # Resolve parameter short names
    resolved_params = []
    for p in param.split("/"):
        resolved_params.append(PARAM_CODES.get(p.lower(), p))
    param_str = "/".join(resolved_params)

    request = {
        **DEFAULT_REQUEST,
        "activity": get_activity(experiment),
        "model": model,
        "experiment": experiment,
        "date": date,
        "param": param_str,
        "time": time,
        "levtype": levtype,
        "realization": realization,
    }

    if extra_keys:
        request.update(extra_keys)

    if bbox:
        request["feature"] = parse_bbox(bbox)

    return request


def generate_date_range(start_date: str, end_date: str) -> List[str]:
    """
    Generate a list of dates between start_date and end_date (inclusive)
    in YYYYMMDD format.

    Example:
        generate_date_range('20200101', '20200103')
        -> ['20200101', '20200102', '20200103']
    """
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    if end < start:
        raise ValueError(f"end_date {end_date} is before start_date {start_date}")

    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    return dates


def download_data(
    request: Dict[str, Any],
    output_dir: str = "./data",
    stream: bool = False,
) -> Optional[Any]:
    """
    Download data from Polytope using earthkit-data.

    Parameters
    ----------
    request : dict
        Polytope request dictionary.
    output_dir : str
        Directory to store downloaded data.
    stream : bool
        If True, stream data directly; if False, cache to local file.

    Returns
    -------
    earthkit.data source object or None
        The downloaded data object on success, or None on failure.
    """
    try:
        import earthkit.data

        model = request.get("model", "ICON")
        address = get_address(model)

        print("Downloading from Polytope...")
        print(f"  Server:     {address}")
        print(f"  Model:      {model}")
        print(f"  Activity:   {request.get('activity', 'N/A')}")
        print(f"  Experiment: {request.get('experiment', 'N/A')}")
        print(f"  Date:       {request.get('date', 'N/A')}")
        print(f"  Time:       {request.get('time', 'N/A')}")
        print(f"  Param:      {request.get('param', 'N/A')}")
        print(f"  Output:     {output_dir}")

        os.makedirs(output_dir, exist_ok=True)

        data = earthkit.data.from_source(
            "polytope",
            COLLECTION,
            request,
            address=address,
            stream=stream,
        )

        n_vals = safe_len(data)
        print(f"Download successful - retrieved {n_vals} values.")
        return data

    except ImportError:
        print("ERROR: earthkit-data is not installed.", file=sys.stderr)
        print("Install with: pip install -r requirements.txt", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        print("Check your authentication (~/.polytopeapirc) and request parameters.",
              file=sys.stderr)
        return None


def download_low_level(
    request: Dict[str, Any],
    output_dir: str = "./data",
    email: Optional[str] = None,
    api_key: Optional[str] = None,
) -> bool:
    """
    Download data using the low-level polytope-client.

    Use this for advanced scenarios where earthkit-data is not suitable.

    Parameters
    ----------
    request : dict
        Polytope request dictionary.
    output_dir : str
        Directory for output files.
    email : str, optional
        DestinE Platform email. Reads from ~/.polytopeapirc if omitted.
    api_key : str, optional
        DestinE Platform API key. Reads from ~/.polytopeapirc if omitted.

    Returns
    -------
    bool
        True if successful, False otherwise.
    """
    try:
        from polytope.api import Client

        model = request.get("model", "ICON")
        address = get_address(model)

        kwargs = {"address": address}
        if email and api_key:
            kwargs["user_email"] = email
            kwargs["user_key"] = api_key

        client = Client(**kwargs)
        client.revoke("all")  # Cancel any pending requests

        os.makedirs(output_dir, exist_ok=True)

        print(f"Downloading via polytope-client to {output_dir}...")
        files = client.retrieve(COLLECTION, request, output_dir)
        print(f"Downloaded {len(files)} file(s):")
        for f in files:
            print(f"  {f}")
        return True

    except ImportError:
        print("ERROR: polytope-client is not installed.", file=sys.stderr)
        print("Install with: pip install polytope-client", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        return False


def aggregate_daily(
    data: Any,
    output_dir: str,
    param: str,
    date_str: str,
) -> str:
    """Aggregate hourly data to daily means and save as netCDF.

    Converts the earthkit-data GRIB object to xarray, averages across
    all time steps within each day, and writes a compressed netCDF file.

    Parameters
    ----------
    data : earthkit.data source
        Downloaded hourly GRIB data object.
    output_dir : str
        Directory to save the netCDF file.
    param : str
        Parameter short name (used in the output filename).
    date_str : str
        Date string YYYYMMDD (used in the output filename).

    Returns
    -------
    str
        Path to the saved netCDF file.

    Raises
    ------
    ImportError
        If xarray is not installed.
    """
    try:
        import xarray as xr
        import pandas as pd
    except ImportError:
        print("ERROR: xarray and pandas are required for daily aggregation.",
              file=sys.stderr)
        print("Install with: pip install -r requirements.txt", file=sys.stderr)
        raise

    print(f"  Aggregating hourly data to daily means for {date_str} ...")

    # Convert GRIB to xarray
    ds = data.to_xarray()

    # Squeeze singleton GRIB dimensions (number, step, etc.)
    _grib_singletons = ("number", "step", "steps")
    squeeze_dims = [d for d in _grib_singletons if d in ds.dims and ds.sizes[d] == 1]
    if squeeze_dims:
        ds = ds.squeeze(squeeze_dims).drop_vars(squeeze_dims, errors="ignore")

    # Rename common time-like dims to "time"
    _dim_renames = {"datetimes": "time", "forecast_reference_time": "time",
                    "valid_time": "time"}
    renames = {k: v for k, v in _dim_renames.items() if k in ds.dims}
    if renames:
        ds = ds.rename(renames)

    # Ensure time coordinate is proper datetime64
    if "time" in ds.coords and not np.issubdtype(ds["time"].dtype, np.datetime64):
        ds["time"] = pd.to_datetime(ds["time"].values, utc=True).tz_localize(None)

    # Resample to daily means
    if "time" in ds.dims and ds.sizes["time"] > 1:
        ds_daily = ds.resample(time="1D").mean()
    else:
        ds_daily = ds

    # Save as netCDF
    out_fname = f"{param}_{date_str}_daily.nc"
    out_path = os.path.join(output_dir, out_fname)
    encoding = {var: {"zlib": True, "complevel": 4} for var in ds_daily.data_vars}
    ds_daily.to_netcdf(out_path, encoding=encoding)
    print(f"  Saved daily netCDF: {out_path}")
    return out_path


def consolidate_daily_files(output_dir: str, param: str, start_date: str,
                            end_date: str = None) -> List[str]:
    """Merge daily netCDF files into monthly or yearly files, delete originals.

    Decision logic:
      - > 365 days span → yearly files  (one per year)
      - > 31  days span → monthly files (one per month)
      - ≤ 31  days      → leave daily files as-is

    Parameters
    ----------
    output_dir : str
        Directory containing the daily ``*_daily.nc`` files.
    param : str
        Parameter short name (used to match files).
    start_date : str
        Start date YYYYMMDD of the download period.
    end_date : str, optional
        End date YYYYMMDD of the download period.  If None, inferred from
        ``start_date`` as a single day.

    Returns
    -------
    list of str
        Paths to the consolidated netCDF files (empty if span ≤ 31 days).
    """
    import glob
    import xarray as xr
    import pandas as pd

    pattern = os.path.join(output_dir, f"{param}_*_daily.nc")
    daily_files = sorted(glob.glob(pattern))
    if not daily_files:
        return []

    n_days = len(daily_files)
    if end_date is None:
        end_date = start_date

    t0 = datetime.strptime(start_date, "%Y%m%d")
    t1 = datetime.strptime(end_date, "%Y%m%d")
    span_days = (t1 - t0).days + 1

    if span_days <= 31:
        print(f"\n  Span ({span_days} days) ≤ 31 — keeping daily files as-is.")
        return []

    if span_days > 365:
        freq_label = "Y"
        freq_file = "%Y"
        group_key = lambda f: os.path.basename(f)[len(f"{param}_"):][:4]  # YYYY
    else:
        freq_label = "M"
        freq_file = "%Y%m"
        group_key = lambda f: os.path.basename(f)[len(f"{param}_"):][:6]  # YYYYMM

    # Group files
    groups = {}
    for f in daily_files:
        key = group_key(f)
        groups.setdefault(key, []).append(f)

    print(f"\n  Consolidating {n_days} daily files into {len(groups)} "
          f"{freq_label} files ...")

    consolidated = []
    for grp_key in sorted(groups.keys()):
        fpaths = groups[grp_key]
        out_fname = f"{param}_{grp_key}_{freq_label}_mean.nc"
        out_path = os.path.join(output_dir, out_fname)

        if len(fpaths) == 1:
            os.rename(fpaths[0], out_path)
            print(f"    Renamed {os.path.basename(fpaths[0])} → {out_fname}")
        else:
            ds = xr.open_mfdataset(fpaths, combine="by_coords")
            encoding = {var: {"zlib": True, "complevel": 4}
                        for var in ds.data_vars}
            ds.to_netcdf(out_path, encoding=encoding)
            print(f"    Merged {len(fpaths)} files → {out_fname}")
            # Delete daily files
            for fp in fpaths:
                os.remove(fp)

        consolidated.append(out_path)

    print(f"  Consolidation complete — {len(consolidated)} {freq_label} file(s).")
    return consolidated


def parse_key_value_pairs(pairs: List[str]) -> Dict[str, str]:
    """Parse 'key=value' strings into a dictionary."""
    result = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(
                f"Invalid key=value pair: '{pair}'. Expected format: key=value"
            )
        key, value = pair.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Download DestinE Climate DT data via Polytope",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single date, single parameter
  %(prog)s --model ICON --experiment cont --date 19900102 --param 134

  # Date range with multiple parameters
  %(prog)s --model IFS-FESOM --experiment SSP3-7.0 \\
           --date 20200601 --end-date 20200630 \\
           --param tp/2t --time 0000/0600/1200/1800

  # Monthly data (clmn stream)
  %(prog)s --model IFS-FESOM --experiment hist \\
           --date 20100601 --param avg_2t --data-stream clmn

  # Crop to a bounding box (south,west,north,east)
  %(prog)s --model ICON --experiment hist \\
           --date 20000615 --param tp --bbox 5,44,10,49

  # Daily aggregation from hourly data
  %(prog)s --model ICON --experiment hist \\
           --date 20000601 --end-date 20000615 --param tp --daily

  # Bounding box + daily aggregation
  %(prog)s --model ICON --experiment hist \\
           --date 20000601 --end-date 20000615 --param tp \\
           --bbox -10,-20,25,55 --daily

  # Use short parameter names
  %(prog)s --model ICON --experiment hist --date 20000615 --param tp/10u/10v

  # Override request keys
  %(prog)s --model ICON --experiment SSP3-7.0 --date 20200615 \\
           --param tp --request-key generation=2 \\
           --request-key resolution=standard

  # Use low-level polytope-client
  %(prog)s --model IFS-FESOM --experiment SSP3-7.0 \\
           --date 20200101 --param 134 --use-client

  # Dry-run: print request without downloading
  %(prog)s --model IFS-NEMO --experiment hist --date 20000615 \\
           --param 134 --dry-run

Experiment names:
  cont      = control simulation (activity=baseline)
  hist      = historical simulation (activity=baseline)
  SSP3-7.0  = future projections (activity=projections)

Server mapping:
  ICON, IFS-FESOM  -> LUMI (polytope.lumi.apps.dte.destination-earth.eu)
  IFS-NEMO         -> MN5  (polytope.mn5.apps.dte.destination-earth.eu)

Parameter short names (hourly clte):
  sp=134 (surface pressure), 10u=165, 10v=166, 2t=167,
  2d=168, tp=avg_tprate (precipitation rate), msl=151, skt=235

Parameter short names (monthly clmn, use --data-stream clmn):
  avg_2t (2m temperature), avg_tprate (precipitation rate),
  avg_sp (surface pressure), avg_msl (MSLP), avg_tcc (cloud cover)
        """,
    )

    # Required arguments
    parser.add_argument(
        "--model", required=True,
        choices=["ICON", "IFS-FESOM", "IFS-NEMO"],
        help="Climate model to query"
    )
    parser.add_argument(
        "--experiment", required=True,
        help="Experiment name: cont (control), hist (historical), SSP3-7.0 (projections)"
    )
    parser.add_argument(
        "--date", required=True,
        help="Date in YYYYMMDD format (start date if used with --end-date)"
    )
    parser.add_argument(
        "--param", required=True,
        help="Parameter codes (slash-separated), e.g. '134/165/166' or 'tp/2t'"
    )

    # Optional arguments
    parser.add_argument(
        "--end-date",
        help="End date in YYYYMMDD format for date range (inclusive)"
    )
    parser.add_argument(
        "--time", default="0000",
        help="Time(s) in HHMM format (default: 0000). "
             "Use slash for multiple: '0000/0600/1200/1800'"
    )
    parser.add_argument(
        "--levtype", default="sfc",
        choices=["sfc", "pl", "hl", "sol", "o2d", "o3d"],
        help="Level type (default: sfc)"
    )
    parser.add_argument(
        "--data-stream", default="clte",
        choices=["clte", "clmn"],
        help="Data stream: clte (hourly instantaneous, default) or "
             "clmn (monthly means)"
    )
    parser.add_argument(
        "--realization", default="1",
        help="Ensemble realization number (default: 1)"
    )
    parser.add_argument(
        "--output", "-o", default="./data",
        help="Output directory (default: ./data)"
    )
    parser.add_argument(
        "--stream", action="store_true",
        help="Stream data directly instead of caching locally"
    )
    parser.add_argument(
        "--use-client", action="store_true",
        help="Use low-level polytope-client instead of earthkit-data"
    )
    parser.add_argument(
        "--request-key", action="append", default=[],
        metavar="KEY=VALUE",
        help="Additional request key-value pair (can be used multiple times). "
             "Example: --request-key generation=2 --request-key stream=clte"
    )
    parser.add_argument(
        "--email",
        help="DestinE Platform email (for polytope-client)"
    )
    parser.add_argument(
        "--api-key",
        help="DestinE Platform API key (for polytope-client)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print the request dictionary without downloading"
    )

    # ---- New spatial / temporal options ----
    parser.add_argument(
        "--bbox",
        help="Bounding box in degrees: south,west,north,east. "
             "Example: '5,44,10,49' for Horn of Africa. "
             "Injects a 'feature' key for server-side spatial subsetting."
    )
    parser.add_argument(
        "--daily", action="store_true",
        help="Aggregate hourly (clte) data to daily means. "
             "Forces --data-stream to clte and --time to all 24 hours if "
             "not explicitly overridden. Output saved as netCDF."
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-download and overwrite existing daily netCDF files. "
             "By default, dates whose output file already exists are skipped."
    )

    args = parser.parse_args()

    # ---- Validate --daily constraints ----
    if args.daily:
        if args.data_stream != "clte":
            print("NOTE: --daily forces --data-stream to clte (hourly data required "
                  "for daily aggregation).", file=sys.stderr)
            args.data_stream = "clte"
        if args.use_client:
            print("ERROR: --daily is not compatible with --use-client.",
                  file=sys.stderr)
            sys.exit(1)

    # Parse extra request keys
    try:
        extra_keys = parse_key_value_pairs(args.request_key)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Inject data stream if not already in extra_keys (overrides DEFAULT_REQUEST)
    if "stream" not in extra_keys and args.data_stream:
        extra_keys["stream"] = args.data_stream

    # ---- Handle --daily time default ----
    time_arg = args.time
    if args.daily and args.time == "0000":
        # User did not override --time; default to all 24 hours
        time_arg = ALL_HOURS
        print(f"Using all 24 hours for daily aggregation: {ALL_HOURS}")

    # Generate date list
    if args.end_date:
        try:
            dates = generate_date_range(args.date, args.end_date)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        dates = [args.date]

    print("=" * 60)
    print("DestinE Climate DT Data Download")
    print("=" * 60)
    print(f"Model:       {args.model}")
    print(f"Experiment:  {args.experiment}")
    print(f"Server:      {get_address(args.model)}")
    print(f"Data stream: {args.data_stream}")
    print(f"Dates to download: {len(dates)} day(s)")
    if args.bbox:
        print(f"Bounding box: {args.bbox}")
    if args.daily:
        print(f"Daily aggregation: enabled")
    print()

    success_count = 0
    fail_count = 0

    for idx, day in enumerate(dates, start=1):
        request = build_request(
            model=args.model,
            experiment=args.experiment,
            date=day,
            param=args.param,
            time=time_arg,
            levtype=args.levtype,
            realization=args.realization,
            extra_keys=extra_keys if extra_keys else None,
            bbox=args.bbox,
        )

        if args.dry_run:
            print(f"--- Request for {day} ---")
            for key, value in sorted(request.items()):
                print(f"  {key}: {value}")
            continue

        print(f"--- Processing {day} ({idx}/{len(dates)}) ---")

        # Skip if daily file already exists (unless --force)
        if args.daily and not args.force:
            out_fname = f"{args.param}_{day}_daily.nc"
            out_path = os.path.join(args.output, out_fname)
            if os.path.exists(out_path):
                print(f"  Skipping — {out_fname} already exists (use --force to re-download)")
                success_count += 1
                continue

        if args.use_client:
            ok = download_low_level(
                request,
                output_dir=args.output,
                email=args.email,
                api_key=args.api_key,
            )
            if ok:
                success_count += 1
            else:
                fail_count += 1
        else:
            data = download_data(
                request,
                output_dir=args.output,
                stream=args.stream,
            )

            if data is None:
                fail_count += 1
                continue

            success_count += 1

            # ---- Daily aggregation ----
            if args.daily:
                try:
                    aggregate_daily(data, args.output, args.param, day)
                except Exception as e:
                    print(f"Daily aggregation failed for {day}: {e}",
                          file=sys.stderr)
                    # Don't count as download failure — data was retrieved
                    print("  (download succeeded but aggregation failed)")

    # ---- Consolidate daily files (if --daily and span > 31 days) ----
    if args.daily and not args.dry_run and success_count > 0:
        end_d = args.end_date if args.end_date else args.date
        try:
            consolidate_daily_files(args.output, args.param, args.date, end_d)
        except Exception as e:
            print(f"Consolidation failed: {e}", file=sys.stderr)

    # Summary
    print()
    print("=" * 60)
    print(
        f"Summary: {success_count} succeeded, {fail_count} failed "
        f"(out of {len(dates)} day(s))"
    )
    print("=" * 60)

    if args.dry_run:
        print("\nThis was a dry run. Remove --dry-run to actually download data.")

    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()