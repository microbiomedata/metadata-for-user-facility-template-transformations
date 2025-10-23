import calendar
import os

import pandas as pd
import requests

from typing import Dict, Any
from dotenv import dotenv_values


class MetadataRetriever:
    """
    Retrieves metadata records from a given submission ID and user facility.
    """

    USER_FACILITY_DICT: Dict[str, str] = {
        "emsl": "emsl_data",
        "jgi_mg": "jgi_mg_data",
        "jgi_mg_lr": "jgi_mg_lr_data",
        "jgi_mt": "jgi_mt_data",
    }

    def __init__(self, metadata_submission_id: str, user_facility: str) -> None:
        """
        Initialize the MetadataRetriever.

        :param metadata_submission_id: The ID of the metadata submission.
        :param user_facility: The user facility to retrieve data from.
        """
        self.metadata_submission_id = metadata_submission_id
        self.user_facility = user_facility
        self.load_and_set_env_vars()
        self.base_url = self.env.get("SUBMISSION_PORTAL_BASE_URL")

    def load_and_set_env_vars(self):
        """Loads and sets environment variables from .env file."""
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        env_vars = dotenv_values(env_path)
        for key, value in env_vars.items():
            os.environ[key] = value

        self.env: Dict[str, str] = dict(os.environ)

    def retrieve_metadata_records(self, unique_field: str) -> pd.DataFrame:
        """
        Retrieves the metadata records for the given submission ID and user facility.

        :return: The retrieved metadata records as a Pandas DataFrame.
        """
        self.load_and_set_env_vars()

        refresh_response = requests.post(
            f"{self.base_url}/auth/refresh",
            json={"refresh_token": self.env["DATA_PORTAL_REFRESH_TOKEN"]},
        )
        refresh_response.raise_for_status()
        refresh_body = refresh_response.json()
        access_token = refresh_body["access_token"]

        headers = {
            "content-type": "application/json; charset=UTF-8",
            "Authorization": f"Bearer {access_token}",
        }
        response: Dict[str, Any] = requests.get(
            f"{self.base_url}/api/metadata_submission/{self.metadata_submission_id}",
            headers=headers,
        ).json()

        # Get user-facility key data
        common_df: pd.DataFrame = pd.DataFrame()
        if self.user_facility in self.USER_FACILITY_DICT:
            user_facility_data: Dict[str, Any] = response["metadata_submission"][
                "sampleData"
            ].get(self.USER_FACILITY_DICT[self.user_facility], {})
            common_df = pd.DataFrame(user_facility_data)

        # Check if common_df is empty
        if common_df.empty:
            raise ValueError(
                f"No key {self.user_facility} exists in submission metadata record {self.metadata_submission_id}"
            )
        else:
            df = common_df

        # Find non-user-facility keys (ie, plant_associated, water, etc)
        all_keys_data = response["metadata_submission"]["sampleData"]
        user_facility_keys = [
            "emsl_data",
            "jgi_mg_data",
            "jgi_mg_lr_data",
            "jgi_mt_data",
        ]
        sample_data_keys = [
            key for key in all_keys_data if key not in user_facility_keys
        ]

        # Create an empty list to store dataframes for each key
        sample_data_dfs = []

        # Loop through resulting keys and combine with common_df by samp_name
        for key in sample_data_keys:

            sample_data: Dict[str, Any] = response["metadata_submission"][
                "sampleData"
            ].get(key, {})

            # Begin collecting detailed sample data

            # If there's sample data, create a DataFrame and add it to the list
            if sample_data:
                sample_data_df = pd.DataFrame(sample_data)

                # Add the non-UF key name into the df for 'Sample Isolated From' col in jgi mg/mt
                sample_data_df["sample_isolated_from"] = key
                # Append to list of dfs
                sample_data_dfs.append(sample_data_df)

        # Concatenate sample dataframes into one (if they exist)
        if sample_data_dfs:
            all_sample_data_df = pd.concat(sample_data_dfs, ignore_index=True)
            # Merge the combined sample data with df on samp_name
            if not df.empty and not all_sample_data_df.empty:
                df = pd.merge(df, all_sample_data_df, on="samp_name", how="outer")

        # Auto-fill depth with 0 for JGI facilities if no value is provided
        if self.user_facility in ["jgi_mg", "jgi_mt", "jgi_mg_lr"]:
            if "depth" not in df.columns:
                df["depth"] = 0
            else:
                df["depth"] = df["depth"].fillna(0)

        for index, row in df.iterrows():

            if "lat_lon" in df.columns:

                # Check if lat_lon is nan before trying to split it
                if pd.isnull(row["lat_lon"]):
                    df.at[index, "latitude"] = None
                    df.at[index, "longitude"] = None
                else:
                    values = str(row["lat_lon"]).split(" ", 1)
                    # Assign the split values back to the row
                    df.at[index, "latitude"] = values[0]
                    df.at[index, "longitude"] = values[1]

            if "depth" in df.columns:

                # Case - different delimiters used
                row["depth"] = str(row["depth"]).replace("-", " - ")

                # Case - only one value provided for depth (single value will be max and min)
                # Checking if the value is a string, because if there is a dash, that will be the case
                if type(row["depth"]) == str:
                    values = row["depth"].split(" - ")
                    # Check if only one value
                    if len(values) == 1:
                        df.at[index, "minimum_depth"] = float(values[0])
                        df.at[index, "maximum_depth"] = float(values[0])
                    # Check if it's a range
                    elif len(values) == 2:
                        df.at[index, "minimum_depth"] = float(values[0])
                        df.at[index, "maximum_depth"] = float(values[1])
                else:
                    df.at[index, "minimum_depth"] = row["depth"]
                    df.at[index, "maximum_depth"] = row["depth"]

        if "geo_loc_name" in df.columns:
            df["country_name"] = df["geo_loc_name"].str.split(":").str[0]

        if "collection_date" in df.columns:
            df["collection_year"] = df["collection_date"].str.split("-").str[0]
            df["collection_month"] = df["collection_date"].str.split("-").str[1]
            df["collection_day"] = df["collection_date"].str.split("-").str[2]

            # Safely map collection_month to month_name (account for NaN values)
            def get_month_name(month):
                try:
                    return calendar.month_name[int(month)]
                except (ValueError, TypeError):
                    return ""  # return empty string for invalid cases

            df["collection_month_name"] = df["collection_month"].apply(get_month_name)

        # Ensure 'analysis_type' exists in df before modifying it
        if "analysis_type" in df.columns:
            df["analysis_type"] = df["analysis_type"].apply(
                lambda x: "; ".join(x) if isinstance(x, list) else x
            )

        # Address 'Was sample DNAse treated?' col
        # Change from 'yes/no' to 'Y/N'
        if self.user_facility in ["jgi_mg", "jgi_mt"] and "dnase" in df.columns:
            df.loc[df["dnase"] == "yes", "dnase"] = "Y"
            df.loc[df["dnase"] == "no", "dnase"] = "N"

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
        if self.user_facility == "jgi_mg" or self.user_facility == "jgi_mt":
            df["country_name"] = df["country_name"].replace(usa_names, "USA")

        return df
