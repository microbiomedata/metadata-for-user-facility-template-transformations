import calendar
from typing import Any

import pandas as pd


USER_FACILITY_DATA_KEYS: dict[str, str] = {
    "emsl": "emsl_data",
    "jgi_mg": "jgi_mg_data",
    "jgi_mg_lr": "jgi_mg_lr_data",
    "jgi_mt": "jgi_mt_data",
}


def create_metadata_dataframe(
    sample_metadata: dict[str, Any],
    user_facility: str,
    sample_set_id: str,
) -> pd.DataFrame:
    facility_key = USER_FACILITY_DATA_KEYS.get(user_facility)
    facility_data = (
        sample_metadata.get(facility_key, {}) if facility_key is not None else {}
    )
    dataframe = pd.DataFrame(facility_data)

    if dataframe.empty:
        raise ValueError(
            f"No key {user_facility} exists in sample set record {sample_set_id}"
        )

    # Create an empty list to store dataframes for each environmental (non-facility) key
    environmental_dataframes: list[pd.DataFrame] = []

    # Loop through non-facility keys and combine with environmental_dataframes by samp_name
    facility_keys = set(USER_FACILITY_DATA_KEYS.values())
    for key, records in sample_metadata.items():
        if key in facility_keys or not records:
            continue

        environmental_dataframe = pd.DataFrame(records)
        environmental_dataframe["sample_isolated_from"] = key
        environmental_dataframes.append(environmental_dataframe)

    # Concatenate sample dataframes into one (if they exist)
    if environmental_dataframes:
        all_environmental_data = pd.concat(
            environmental_dataframes,
            ignore_index=True,
        )
        dataframe = pd.merge(
            dataframe,
            all_environmental_data,
            on="samp_name",
            how="left",
        )

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

    # Auto-fill depth with 0 for JGI facilities if no value is provided
    jgi_facilities = {"jgi_mg", "jgi_mt", "jgi_mg_lr"}
    if user_facility in jgi_facilities:
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

    if "collection_date" in dataframe.columns:
        date_parts = dataframe["collection_date"].str.split("-")
        dataframe["collection_year"] = date_parts.str[0].astype(int)
        dataframe["collection_month"] = date_parts.str[1]
        dataframe["collection_day"] = date_parts.str[2].astype(int)

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

    # Address 'Was sample DNAse treated?' col
    # Change from 'yes/no' to 'Y/N'
    if user_facility in jgi_facilities and "dnase" in dataframe.columns:
        dataframe.loc[dataframe["dnase"] == "yes", "dnase"] = "Y"
        dataframe.loc[dataframe["dnase"] == "no", "dnase"] = "N"

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
    if user_facility in jgi_facilities and "country_name" in dataframe.columns:
        dataframe["country_name"] = dataframe["country_name"].replace(
            usa_names,
            "USA",
        )

    return dataframe
