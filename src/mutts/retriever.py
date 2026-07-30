import os

import pandas as pd
import requests

from typing import Dict, Any
from dotenv import dotenv_values

from mutts.dataframe import create_metadata_dataframe


class MetadataRetriever:
    """
    Retrieves metadata records from a given sample set ID and user facility.
    """

    def __init__(self, sample_set_id: str, user_facility: str) -> None:
        """
        Initialize the MetadataRetriever.

        :param sample_set_id: The ID of the sample set.
        :param user_facility: The user facility to retrieve data from.
        """
        self.sample_set_id = sample_set_id
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

    def retrieve_sample_metadata(self) -> dict[str, Any]:
        """Retrieve sample metadata for the configured sample set."""
        self.load_and_set_env_vars()

        refresh_response = requests.post(
            f"{self.base_url}/auth/refresh",
            json={"refresh_token": self.env["DATA_PORTAL_REFRESH_TOKEN"]},
        )
        refresh_response.raise_for_status()
        access_token = refresh_response.json()["access_token"]

        response = requests.get(
            f"{self.base_url}/api/metadata_submission/sample_set/{self.sample_set_id}",
            headers={
                "content-type": "application/json; charset=UTF-8",
                "Authorization": f"Bearer {access_token}",
            },
        )
        response.raise_for_status()
        return response.json()["sample_data"]["data"]

    def retrieve_metadata_records(self, unique_field: str) -> pd.DataFrame:
        """
        Retrieves the metadata records for the given sample set ID and user facility.

        :param unique_field: Retained for compatibility with the existing API.
        :return: The retrieved metadata records as a Pandas DataFrame.
        """
        sample_metadata = self.retrieve_sample_metadata()
        return create_metadata_dataframe(
            sample_metadata,
            self.user_facility,
            self.sample_set_id,
        )
