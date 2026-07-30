import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from mutts import MetadataRetriever


def required_environment_variable(name: str) -> str:
    value = os.getenv(name)
    if not value:
        pytest.fail(f"Missing required integration-test environment variable: {name}")
    return value


@pytest.mark.integration
def test_retrieves_and_transforms_sample_set(
    monkeypatch: pytest.MonkeyPatch,
):
    """Verify MUTTs can retrieve and transform a sample set from the configured
    nmdc-server instance."""
    load_dotenv(Path(__file__).parents[1] / ".env")

    base_url = required_environment_variable("SUBMISSION_PORTAL_BASE_URL")
    refresh_token = required_environment_variable("DATA_PORTAL_REFRESH_TOKEN")
    sample_set_id = required_environment_variable("INTEGRATION_TEST_SAMPLE_SET_ID")
    user_facility = required_environment_variable("INTEGRATION_TEST_USER_FACILITY")
    expected_sample_name = required_environment_variable(
        "INTEGRATION_TEST_EXPECTED_SAMPLE_NAME"
    )

    monkeypatch.setattr("mutts.retriever.dotenv_values", lambda _path: {})
    monkeypatch.setenv("SUBMISSION_PORTAL_BASE_URL", base_url.rstrip("/"))
    monkeypatch.setenv("DATA_PORTAL_REFRESH_TOKEN", refresh_token)

    dataframe = MetadataRetriever(
        sample_set_id,
        user_facility,
    ).retrieve_metadata_records("samp_name")

    assert not dataframe.empty
    assert "samp_name" in dataframe.columns
    assert expected_sample_name in dataframe["samp_name"].astype(str).tolist()
