#!/usr/bin/env python3

import argparse
import re
from difflib import get_close_matches
from pathlib import Path

import pandas as pd


def slugify(text: str) -> str:
    """Lower‑case `text`, replace any run of non‑alphanumerics with “_”."""
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def find_first_sample_row(raw: pd.DataFrame, sample_name_col: int) -> int:
    """
    Return the index of the first *real* sample row (i.e. where the sample
    name cell is not NaN **and** the row is beyond the metadata section).
    """
    for idx in range(4, len(raw)):
        if pd.notna(raw.iat[idx, sample_name_col]):
            return idx
    raise ValueError("No sample rows found – check the input workbook.")


def build_column_lookup(raw: pd.DataFrame) -> tuple[dict[str, int], dict[str, int]]:
    """
    Returns two dicts mapping **slug** → **column‑index**:
       • display_name_lookup  – based on Row 1
       • machine_name_lookup  – based on Row 0
    """
    display = {slugify(v): i for i, v in enumerate(raw.iloc[1]) if pd.notna(v)}
    machine  = {slugify(v): i for i, v in enumerate(raw.iloc[0]) if pd.notna(v)}
    return display, machine


def main(input_path: Path, template_path: Path, output_path: Path) -> None:
    # Read workbooks
    emsl_raw   = pd.read_excel(input_path, header=None, engine="openpyxl")
    nmdc_tmpl  = pd.read_excel(template_path, header=None, engine="openpyxl")

    # Locate sample section
    try:
        sample_name_col = list(emsl_raw.iloc[0]).index("sample_name")
    except ValueError:
        raise ValueError("Column 'sample_name' not found in EMSL workbook.")
    first_sample_row = find_first_sample_row(emsl_raw, sample_name_col)

    # Split EMSL raw dataframe into metadata + samples
    sample_df = emsl_raw.iloc[first_sample_row:].reset_index(drop=True)

    # Build column look‑ups
    display_lu, machine_lu = build_column_lookup(emsl_raw)

    # Prepare NMDC header mapping
    nmdc_headers = nmdc_tmpl.iloc[0].tolist()
    header_idx   = {h: i for i, h in enumerate(nmdc_headers)}

    # Optionally add manual overrides
    # Keys = NMDC column name (exact), Value = EMSL column *code* or *display* name
    MANUAL_MAP: dict[str, str] = {
        # Example:
        # "watering regimen": "watering_regimen_schedule_treatment",
    }
    # Build slugged manual map for quick access
    manual_lu = {slugify(k): slugify(v) for k, v in MANUAL_MAP.items()}

    # Transform row‑by‑row
    out_records: list[list] = []
    num_cols = len(nmdc_headers)

    for _, emsl_row in sample_df.iterrows():
        record = [pd.NA] * num_cols

        for nmdc_col in nmdc_headers:
            slug = slugify(nmdc_col)

            # Manual overrides win
            if slug in manual_lu:
                source_slug = manual_lu[slug]
                if source_slug in display_lu:
                    val = emsl_row.iat[display_lu[source_slug]]
                elif source_slug in machine_lu:
                    val = emsl_row.iat[machine_lu[source_slug]]
                else:
                    val = pd.NA

            # 1‑to‑1 slug matches
            elif slug in display_lu:
                val = emsl_row.iat[display_lu[slug]]
            elif slug in machine_lu:
                val = emsl_row.iat[machine_lu[slug]]

            # Fuzzy match fallback
            else:
                candidates = list(display_lu.keys()) + list(machine_lu.keys())
                match = get_close_matches(slug, candidates, n=1, cutoff=0.85)
                if match:
                    src_slug = match[0]
                    val = (
                        emsl_row.iat[display_lu.get(src_slug)]
                        if src_slug in display_lu
                        else emsl_row.iat[machine_lu[src_slug]]
                    )
                else:
                    val = pd.NA

            record[header_idx[nmdc_col]] = val

        out_records.append(record)

    samples_out = pd.DataFrame(out_records, columns=nmdc_tmpl.columns)

    # Assemble final workbook & write
    final_df = pd.concat([nmdc_tmpl, samples_out], ignore_index=True)
    final_df.to_excel(output_path, index=False, header=False, engine="openpyxl")
    print(f"Wrote {len(out_records)} record(s) ➜ {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reverse ETL: EMSL → NMDC sample_export template."
    )
    parser.add_argument("--input", "-i", required=True, type=Path, help="Input EMSL workbook (*.xlsx)")
    parser.add_argument("--template", "-t", required=True, type=Path, help="NMDC template workbook (*.xlsx)")
    parser.add_argument("--output", "-o", required=True, type=Path, help="Destination workbook (*.xlsx)")
    args = parser.parse_args()

    main(args.input, args.template, args.output)
