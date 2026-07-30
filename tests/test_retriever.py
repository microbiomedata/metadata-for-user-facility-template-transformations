from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from mutts.retriever import MetadataRetriever


@pytest.fixture
def retriever(monkeypatch: pytest.MonkeyPatch) -> MetadataRetriever:
    monkeypatch.setattr(
        "mutts.retriever.dotenv_values",
        lambda _path: {},
    )
    monkeypatch.setenv(
        "SUBMISSION_PORTAL_BASE_URL",
        "https://example.test",
    )
    monkeypatch.setenv(
        "DATA_PORTAL_REFRESH_TOKEN",
        "refresh-token",
    )
    return MetadataRetriever("sample-set-123", "emsl")


def successful_refresh_response() -> Mock:
    response = Mock()
    response.json.return_value = {
        "access_token": "access-token",
        "token_type": "bearer",
    }
    return response


def successful_sample_set_response() -> Mock:
    response = Mock()
    response.json.return_value = {
        "id": "sample-set-123",
        "name": "Unit-test sample set",
        "templates": ["soil"],
        "status": "In Progress",
        "created": "2026-07-30T00:00:00Z",
        "date_last_modified": "2026-07-30T00:00:00Z",
        "navigation_validation": {
            "multi_omics_data": None,
            "sample_environment": None,
            "sample_metadata": None,
        },
        "multi_omics_form": {},
        "sample_environment_form": {},
        "sender_shipping_info_form": {},
        "sample_data": {
            "data": {
                "emsl_data": [{"samp_name": "sample-1"}],
                "soil": [{"samp_name": "sample-1"}],
            },
            "validation": None,
        },
    }
    return response


def test_retrieves_sample_metadata_from_sample_set_endpoint(
    retriever: MetadataRetriever,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify retrieval uses the sample-set endpoint and returns sample data."""
    refresh_response = successful_refresh_response()
    sample_set_response = successful_sample_set_response()
    post = Mock(return_value=refresh_response)
    get = Mock(return_value=sample_set_response)
    monkeypatch.setattr("mutts.retriever.requests.post", post)
    monkeypatch.setattr("mutts.retriever.requests.get", get)

    result = retriever.retrieve_sample_metadata()

    assert result == {
        "emsl_data": [{"samp_name": "sample-1"}],
        "soil": [{"samp_name": "sample-1"}],
    }
    post.assert_called_once_with(
        "https://example.test/auth/refresh",
        json={"refresh_token": "refresh-token"},
    )
    refresh_response.raise_for_status.assert_called_once_with()
    get.assert_called_once_with(
        "https://example.test/api/metadata_submission/sample_set/sample-set-123",
        headers={
            "content-type": "application/json; charset=UTF-8",
            "Authorization": "Bearer access-token",
        },
    )
    sample_set_response.raise_for_status.assert_called_once_with()


def test_propagates_refresh_request_failure(
    retriever: MetadataRetriever,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify token refresh HTTP failures propagate without requesting data."""
    error = requests.HTTPError("refresh failed")
    refresh_response = Mock()
    refresh_response.raise_for_status.side_effect = error
    get = Mock()
    monkeypatch.setattr(
        "mutts.retriever.requests.post",
        Mock(return_value=refresh_response),
    )
    monkeypatch.setattr("mutts.retriever.requests.get", get)

    with pytest.raises(requests.HTTPError, match="refresh failed"):
        retriever.retrieve_sample_metadata()

    get.assert_not_called()


def test_propagates_sample_set_request_failure(
    retriever: MetadataRetriever,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify sample-set HTTP failures propagate to the caller."""
    sample_set_response = Mock()
    sample_set_response.raise_for_status.side_effect = requests.HTTPError(
        "sample set failed"
    )
    monkeypatch.setattr(
        "mutts.retriever.requests.post",
        Mock(return_value=successful_refresh_response()),
    )
    monkeypatch.setattr(
        "mutts.retriever.requests.get",
        Mock(return_value=sample_set_response),
    )

    with pytest.raises(requests.HTTPError, match="sample set failed"):
        retriever.retrieve_sample_metadata()


def test_public_method_orchestrates_retrieval_and_transformation(
    retriever: MetadataRetriever,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the public method connects retrieval to DataFrame transformation."""
    sample_metadata = {
        "emsl_data": [{"samp_name": "sample-1"}],
    }
    expected = pd.DataFrame([{"samp_name": "sample-1"}])
    retrieve = Mock(return_value=sample_metadata)
    transform = Mock(return_value=expected)
    monkeypatch.setattr(
        retriever,
        "retrieve_sample_metadata",
        retrieve,
    )
    # This is mocked here because the logic of `create_metadata_dataframe` is tested in
    # `test_dataframe.py`, so we don't need to test it again here.
    monkeypatch.setattr(
        "mutts.retriever.create_metadata_dataframe",
        transform,
    )

    result = retriever.retrieve_metadata_records("samp_name")

    assert result is expected
    retrieve.assert_called_once_with()
    transform.assert_called_once_with(
        sample_metadata,
        "emsl",
        "sample-set-123",
    )
