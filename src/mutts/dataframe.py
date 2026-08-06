import calendar
from typing import Any

import pandas as pd


# A user facility maps to one or more sample data keys in the submission record.
# Isolate submissions are split across a genome and a transcriptome interface, and
# both feed the same JGI Isolate (NA) v19 template.
USER_FACILITY_DATA_KEYS: dict[str, tuple[str, ...]] = {
    "emsl": ("emsl_data",),
    "jgi_mg": ("jgi_mg_data",),
    "jgi_mg_lr": ("jgi_mg_lr_data",),
    "jgi_mt": ("jgi_mt_data",),
    "jgi_isolate": ("jgi_isolate_genome_data", "jgi_isolate_transcriptome_data"),
}

# The JGI submission types for microbiome samples, which GOLD curates by habitat and
# geographic location. Their template carries the collection-site columns — latitude,
# longitude, depth, elevation, country — that the JGI Isolate template has none of;
# an isolate is a single organism, curated by NCBI taxonomy instead.
JGI_MICROBIOME_TEMPLATES = {"jgi_mg", "jgi_mt", "jgi_mg_lr"}

# Every JGI template. They all spell yes/no answers as Y/N.
JGI_TEMPLATES = JGI_MICROBIOME_TEMPLATES | {"jgi_isolate"}

# Slots whose yes/no values JGI templates expect as Y/N.
YES_NO_SLOTS = (
    "dnase",
    "isolate_single_colony",
    "isolate_fungal_16s_screening",
    "isolate_its_match_unite",
)

# Non-facility keys that describe the sample itself rather than the environment it
# came from. They are merged in on samp_name like any other, but must not be turned
# into a `sample_isolated_from` value: the isolate interfaces already carry a real
# `sample_isolated_from` slot that the user filled in.
NON_ENVIRONMENTAL_DATA_KEYS = {"isolate_data"}


def _is_blank(value: object) -> bool:
    """True for values that should be treated as missing (NaN, None or empty).

    Some slots hold lists (`analysis_type`), for which `pd.isna` returns an array
    rather than a bool, so they are checked for emptiness directly.

    >>> _is_blank(None), _is_blank(float("nan")), _is_blank("")
    (True, True, True)
    >>> _is_blank("   "), _is_blank([])
    (True, True)

    A zero is a value, not a missing one -- depth of 0 means the surface.

    >>> _is_blank(0), _is_blank("soil"), _is_blank(["metagenomics"])
    (False, False, False)
    """
    if isinstance(value, (list, tuple, set, dict)):
        return not value
    if isinstance(value, str):
        return not value.strip()
    return bool(pd.isna(value))


def _coalesce(primary: pd.Series, fallback: pd.Series) -> pd.Series:
    """Take values from `primary`, falling back to `fallback` where primary is blank.

    Row by row: keep the primary value if it has one, otherwise reach for the same
    row of the fallback. Here the first row keeps its own value and the other two,
    being blank, take the fallback's.

    >>> primary = pd.Series(["CTAB", "", None])
    >>> fallback = pd.Series(["unused", "TRIzol", "TRIzol"])
    >>> _coalesce(primary, fallback).tolist()
    ['CTAB', 'TRIzol', 'TRIzol']

    A blank fallback leaves the row blank rather than filling it in.

    >>> _coalesce(pd.Series(["", "kept"]), pd.Series([None, "unused"])).tolist()
    [None, 'kept']
    """
    return primary.where(~primary.map(_is_blank), fallback)


def strip_ncbi_taxon_prefix(value: object) -> object:
    """Reduce an NCBITaxon CURIE to the bare taxon ID JGI templates ask for.

    >>> strip_ncbi_taxon_prefix("NCBITaxon:511145")
    '511145'

    A bare ID is already what JGI wants, so it passes through.

    >>> strip_ncbi_taxon_prefix("511145")
    '511145'
    """
    if isinstance(value, str) and value.startswith("NCBITaxon:"):
        return value.split(":", 1)[1]
    return value


def format_culture_collection_id(value: object) -> object:
    """Render a culture collection CURIE the way the JGI template asks for it.

    Submission schema stores these as bioregistry CURIEs (``dsmz:DSM-15171``,
    ``atcc:700808``) but the JGI form wants the collection name and ID together as
    letters and numbers (``DSM 15171``, ``ATCC 700808``). Where the local identifier
    already names the collection, as DSMZ's does, the prefix is dropped rather than
    repeated. Values without a prefix are already in the form JGI wants and pass
    through untouched.

    >>> format_culture_collection_id("dsmz:DSM-15171")
    'DSM 15171'
    >>> format_culture_collection_id("atcc:700808")
    'ATCC 700808'
    >>> format_culture_collection_id("CIP 54.8")
    'CIP 54.8'
    """
    if not isinstance(value, str) or ":" not in value:
        return value

    prefix, local_id = value.split(":", 1)
    if local_id[:1].isalpha():
        return local_id.replace("-", " ")
    return f"{prefix.upper()} {local_id}"


def create_metadata_dataframe(
    sample_metadata: dict[str, Any],
    user_facility: str,
    sample_set_id: str,
) -> pd.DataFrame:
    # A facility can draw on more than one key; stack their records into one frame
    facility_frames = [
        pd.DataFrame(sample_metadata[key])
        for key in USER_FACILITY_DATA_KEYS.get(user_facility, ())
        if sample_metadata.get(key)
    ]
    dataframe = (
        pd.concat(facility_frames, ignore_index=True)
        if facility_frames
        else pd.DataFrame()
    )

    if dataframe.empty:
        raise ValueError(
            f"No key {user_facility} exists in sample set record {sample_set_id}"
        )

    # Create an empty list to store dataframes for each environmental (non-facility) key
    environmental_dataframes: list[pd.DataFrame] = []

    # Loop through non-facility keys and combine with environmental_dataframes by samp_name
    facility_keys = {key for keys in USER_FACILITY_DATA_KEYS.values() for key in keys}
    for key, records in sample_metadata.items():
        if key in facility_keys or not records:
            continue

        environmental_dataframe = pd.DataFrame(records)
        if key not in NON_ENVIRONMENTAL_DATA_KEYS:
            environmental_dataframe["sample_isolated_from"] = key
        environmental_dataframes.append(environmental_dataframe)

    # Concatenate sample dataframes into one (if they exist)
    if environmental_dataframes:
        all_environmental_data = pd.concat(
            environmental_dataframes,
            ignore_index=True,
        )
        # Both frames can define the same slot (samp_name is the join key, but
        # source_mat_id and analysis_type are shared columns too). Suffix the
        # duplicates, prefer the facility value, then fold them back into one column
        # so downstream lookups still find the slot under its own name.
        overlapping_columns = [
            column
            for column in all_environmental_data.columns
            if column in dataframe.columns and column != "samp_name"
        ]
        dataframe = pd.merge(
            dataframe,
            all_environmental_data,
            on="samp_name",
            how="left",
            suffixes=("", "_environmental"),
        )
        for column in overlapping_columns:
            fallback = f"{column}_environmental"
            dataframe[column] = _coalesce(dataframe[column], dataframe[fallback])
            dataframe = dataframe.drop(columns=fallback)

    if "lat_lon" in dataframe.columns:
        for index, coordinate in dataframe["lat_lon"].items():
            # Check if lat_lon is nan before trying to split it
            if pd.isnull(coordinate):
                dataframe.at[index, "latitude"] = None
                dataframe.at[index, "longitude"] = None
                continue

            latitude, longitude = str(coordinate).split(" ", 1)
            # Assign the split values back to the row
            dataframe.at[index, "latitude"] = latitude
            dataframe.at[index, "longitude"] = longitude

    # Auto-fill depth with 0 for JGI microbiome templates if no value is provided
    if user_facility in JGI_MICROBIOME_TEMPLATES:
        if "depth" not in dataframe.columns:
            dataframe["depth"] = 0
        else:
            dataframe["depth"] = dataframe["depth"].where(
                dataframe["depth"].notna(),
                0,
            )

    if "depth" in dataframe.columns:
        for index, depth in dataframe["depth"].items():
            values = str(depth).replace("-", " - ").split(" - ")
            # Check if only one value
            if len(values) == 1:
                minimum = float(values[0])
                maximum = minimum
            # Check if it's a range
            elif len(values) == 2:
                minimum = float(values[0])
                maximum = float(values[1])
            else:
                continue

            dataframe.at[index, "minimum_depth"] = minimum
            dataframe.at[index, "maximum_depth"] = maximum

    if "geo_loc_name" in dataframe.columns:
        dataframe["country_name"] = dataframe["geo_loc_name"].str.split(":").str[0]

    # The two isolate interfaces answer the same template column with different
    # slots, so fold each pair into the single column the mapper points at.
    if (
        "rna_isolate_meth" in dataframe.columns
        or "dna_isolate_meth" in dataframe.columns
    ):
        dataframe["isolate_meth"] = _coalesce(
            dataframe.get("rna_isolate_meth", pd.Series(pd.NA, index=dataframe.index)),
            dataframe.get("dna_isolate_meth", pd.Series(pd.NA, index=dataframe.index)),
        )

    # RNA isolates record the date of the lab experiment rather than the date the
    # sample was collected in the field, and JGI wants that date in the collection
    # year/month/day columns.
    if "rna_collection_date" in dataframe.columns:
        dataframe["collection_date"] = _coalesce(
            dataframe["rna_collection_date"],
            dataframe.get("collection_date", pd.Series(pd.NA, index=dataframe.index)),
        )

    if "classified_as" in dataframe.columns:
        dataframe["ncbi_tax_id"] = dataframe["classified_as"].apply(
            strip_ncbi_taxon_prefix
        )

    if "host_taxid" in dataframe.columns:
        dataframe["host_taxid"] = dataframe["host_taxid"].apply(strip_ncbi_taxon_prefix)

    if "source_mat_id" in dataframe.columns:
        dataframe["culture_collection_id"] = dataframe["source_mat_id"].apply(
            format_culture_collection_id
        )

    if "collection_date" in dataframe.columns:
        date_parts = dataframe["collection_date"].str.split("-")
        dataframe["collection_year"] = pd.array(date_parts.str[0], dtype="Int64")
        dataframe["collection_month"] = date_parts.str[1]
        dataframe["collection_day"] = pd.array(date_parts.str[2], dtype="Int64")

        # Safely map collection_month to month_name (account for NaN values)
        def get_month_name(month: object) -> str:
            try:
                return calendar.month_name[int(month)]
            except (ValueError, TypeError):
                # return empty string for invalid cases
                return ""

        dataframe["collection_month_name"] = dataframe["collection_month"].apply(
            get_month_name
        )

    # Ensure 'analysis_type' exists in df before modifying it
    if "analysis_type" in dataframe.columns:
        dataframe["analysis_type"] = dataframe["analysis_type"].apply(
            lambda value: "; ".join(value) if isinstance(value, list) else value
        )

    # Address 'Was sample DNAse treated?' and the isolate yes/no cols
    # Change from 'yes/no' to 'Y/N'
    if user_facility in JGI_TEMPLATES:
        for slot in YES_NO_SLOTS:
            if slot not in dataframe.columns:
                continue
            dataframe.loc[dataframe[slot] == "yes", slot] = "Y"
            dataframe.loc[dataframe[slot] == "no", slot] = "N"

    # Address standardizing "USA" country name for MG and MT
    # Replace "country_name" with "USA" if it exists
    usa_names = [
        "United States",
        "United States of America",
        "US",
        "America",
        "usa",
        "united states",
        "united states of america",
        "us",
        "america",
    ]
    if (
        user_facility in JGI_MICROBIOME_TEMPLATES
        and "country_name" in dataframe.columns
    ):
        dataframe["country_name"] = dataframe["country_name"].replace(
            usa_names,
            "USA",
        )

    return dataframe
