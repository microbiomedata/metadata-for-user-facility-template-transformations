from typing import Any

from mutts.dataframe import create_metadata_dataframe
import pandas as pd
import pytest


def create_dataframe(
    sample_metadata: dict[str, Any],
    user_facility: str,
    sample_set_id: str = "sample-set-123",
) -> pd.DataFrame:
    return create_metadata_dataframe(
        sample_metadata,
        user_facility,
        sample_set_id,
    )


@pytest.mark.parametrize(
    ("user_facility", "metadata_key"),
    [
        ("emsl", "emsl_data"),
        ("jgi_mg", "jgi_mg_data"),
        ("jgi_mg_lr", "jgi_mg_lr_data"),
        ("jgi_mt", "jgi_mt_data"),
    ],
)
def test_selects_records_for_each_user_facility(
    user_facility: str,
    metadata_key: str,
) -> None:
    """Verify each facility selects records from its corresponding metadata key."""
    sample_metadata = {
        metadata_key: [
            {
                "samp_name": "sample-1",
                "geo_loc_name": "Canada: Ontario",
            }
        ]
    }

    result = create_dataframe(sample_metadata, user_facility)

    assert result["samp_name"].tolist() == ["sample-1"]


def test_merges_environmental_records_by_sample_name() -> None:
    """Verify environmental records merge with facility data by sample name."""
    sample_metadata = {
        "emsl_data": [
            {"samp_name": "sample-1", "facility_value": "first"},
            {"samp_name": "sample-2", "facility_value": "second"},
        ],
        "soil": [
            {"samp_name": "sample-1", "environment_value": "soil-value"},
        ],
        "water": [
            {"samp_name": "sample-2", "environment_value": "water-value"},
        ],
    }

    result = create_dataframe(sample_metadata, "emsl")

    assert result["environment_value"].tolist() == [
        "soil-value",
        "water-value",
    ]
    assert result["sample_isolated_from"].tolist() == ["soil", "water"]


def test_returns_facility_records_when_environmental_data_is_absent() -> None:
    """Verify facility records remain usable without environmental metadata."""
    sample_metadata = {
        "emsl_data": [
            {"samp_name": "sample-1", "facility_value": "facility-only"},
        ]
    }

    result = create_dataframe(sample_metadata, "emsl")

    assert result.to_dict(orient="records") == [
        {"samp_name": "sample-1", "facility_value": "facility-only"}
    ]


def test_raises_when_requested_facility_data_is_missing() -> None:
    """Verify missing data for the requested facility raises an error."""
    with pytest.raises(
        ValueError,
        match="No key emsl exists in sample set record sample-set-123",
    ):
        create_dataframe({"soil": [{"samp_name": "sample-1"}]}, "emsl")


def test_defaults_missing_jgi_depth_to_zero() -> None:
    """Verify JGI records without depth receive a depth of zero."""
    result = create_dataframe(
        {
            "jgi_mg_data": [
                {
                    "samp_name": "sample-1",
                    "geo_loc_name": "Canada: Ontario",
                }
            ]
        },
        "jgi_mg",
    )

    assert result.loc[0, "depth"] == 0
    assert result.loc[0, "minimum_depth"] == 0.0
    assert result.loc[0, "maximum_depth"] == 0.0


@pytest.mark.parametrize(
    ("depth", "minimum", "maximum"),
    [
        (None, 0.0, 0.0),
        ("2.5", 2.5, 2.5),
        ("1-3", 1.0, 3.0),
    ],
)
def test_derives_jgi_depth_bounds(
    depth: str | None,
    minimum: float,
    maximum: float,
) -> None:
    """Verify null, scalar, and range depths produce the expected min/max values."""
    result = create_dataframe(
        {
            "jgi_mg_data": [
                {
                    "samp_name": "sample-1",
                    "depth": depth,
                    "geo_loc_name": "Canada: Ontario",
                }
            ]
        },
        "jgi_mg",
    )

    assert result.loc[0, "minimum_depth"] == minimum
    assert result.loc[0, "maximum_depth"] == maximum


def test_splits_coordinates_and_preserves_null_coordinates() -> None:
    """Verify lat/lon coordinates split correctly while null coordinates remain null."""
    result = create_dataframe(
        {
            "emsl_data": [
                {"samp_name": "sample-1", "lat_lon": "12.5 -45.25"},
                {"samp_name": "sample-2", "lat_lon": None},
            ]
        },
        "emsl",
    )

    assert result.loc[0, "latitude"] == "12.5"
    assert result.loc[0, "longitude"] == "-45.25"
    assert pd.isna(result.loc[1, "latitude"])
    assert pd.isna(result.loc[1, "longitude"])


def test_derives_location_date_and_list_analysis_fields() -> None:
    """Verify location, date, and list-valued analysis fields are normalized."""
    result = create_dataframe(
        {
            "emsl_data": [
                {
                    "samp_name": "sample-1",
                    "geo_loc_name": "Canada: Ontario",
                    "collection_date": "2025-07-09",
                    "analysis_type": ["metagenomics", "metabolomics"],
                },
                {
                    "samp_name": "sample-2",
                    "geo_loc_name": "Canada: Quebec",
                    "collection_date": "2024-01-02",
                    "analysis_type": "metagenomics",
                },
            ]
        },
        "emsl",
    )

    row = result.loc[0]
    assert row["country_name"] == "Canada"
    assert row["collection_year"] == 2025
    assert row["collection_month"] == "07"
    assert row["collection_day"] == 9
    assert row["collection_month_name"] == "July"
    assert row["analysis_type"] == "metagenomics; metabolomics"
    assert result.loc[1, "analysis_type"] == "metagenomics"


@pytest.mark.parametrize(
    "user_facility",
    ["jgi_mg", "jgi_mg_lr", "jgi_mt"],
)
def test_normalizes_dnase_and_usa_for_jgi_facilities(
    user_facility: str,
) -> None:
    """Verify DNase flags and USA names are normalized for JGI."""
    metadata_key = {
        "jgi_mg": "jgi_mg_data",
        "jgi_mg_lr": "jgi_mg_lr_data",
        "jgi_mt": "jgi_mt_data",
    }[user_facility]
    result = create_dataframe(
        {
            metadata_key: [
                {
                    "samp_name": "sample-1",
                    "dnase": "yes",
                    "geo_loc_name": "United States: California",
                },
                {
                    "samp_name": "sample-2",
                    "dnase": "no",
                    "geo_loc_name": "Canada: Ontario",
                },
            ]
        },
        user_facility,
    )

    assert result["dnase"].tolist() == ["Y", "N"]
    assert result["country_name"].tolist() == ["USA", "Canada"]
