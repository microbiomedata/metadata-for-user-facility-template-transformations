from collections.abc import Sequence
from typing import Any

from mutts.dataframe import (
    create_metadata_dataframe,
    format_culture_collection_id,
    strip_ncbi_taxon_prefix,
)
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


# ---------------------------------------------------------------------------
# Two isolates, one per sequencing interface:
#
#   "bacillus_from_sed"          a bacterium, submitted for genome sequencing (DNA)
#   "Aspergillus niger DSM 817"  a fungus, submitted for transcriptome sequencing (RNA)
#
# `isolate_data` carries the organism biology for both, keyed by samp_name, and both
# isolates belong on the same JGI Isolate v19 sheet.
# ---------------------------------------------------------------------------

# jgi_isolate_genome_data
BACILLUS_GENOME: dict[str, Any] = {
    "samp_name": "bacillus_from_sed",
    "jgi_sample_name": "b_cerus_sed",
    "analysis_type": ["isolate genome sequencing"],
    "biosafety_mat_cat": "Bacteria",
    "dna_isolate_meth": "phenol/chloroform extraction",
    "dnase": "yes",
    "estimated_size": 5,
    "isolate_ribosomal_seq_type": "16S",
    "sample_isolated_from": "single colony isolate",
}

# jgi_isolate_transcriptome_data
ASPERGILLUS_TRANSCRIPTOME: dict[str, Any] = {
    "samp_name": "Aspergillus niger DSM 817",
    "jgi_sample_name": "a_niger_817",
    "analysis_type": ["isolate transcriptome sequencing"],
    "biosafety_mat_cat": "Fungi",
    "rna_isolate_meth": "phenol/chloroform extraction",
    "rna_collection_date": "2026-01-01",
    "dnase": "yes",
    "sample_isolated_from": "single colony isolate",
}

# isolate_data -- organism biology, keyed to the interfaces above by samp_name.
# `analysis_type` is the one slot the interfaces above also carry.
BACILLUS_BIOLOGY: dict[str, Any] = {
    "samp_name": "bacillus_from_sed",
    "analysis_type": ["isolate genome sequencing"],
    "classified_as": "NCBITaxon:1423",
    "collection_date": "2021-02-19",
    "isolate_single_colony": "yes",
    "organism_genus": "Bacillus",
    "organism_species": "subtilis",
    "strain_name": "sp. sed123",
}

ASPERGILLUS_BIOLOGY: dict[str, Any] = {
    "samp_name": "Aspergillus niger DSM 817",
    "analysis_type": ["isolate transcriptome sequencing"],
    "classified_as": "NCBITaxon:5061",
    "collection_date": "2024-07-12",
    "isolate_single_colony": "yes",
    "organism_genus": "Aspergillus",
    "organism_species": "niger",
    "strain_name": "DSM 817",
}


def isolate_submission(
    genome: Sequence[dict[str, Any]] = (BACILLUS_GENOME,),
    transcriptome: Sequence[dict[str, Any]] = (ASPERGILLUS_TRANSCRIPTOME,),
    biology: Sequence[dict[str, Any]] = (BACILLUS_BIOLOGY, ASPERGILLUS_BIOLOGY),
) -> dict[str, Any]:
    """Assemble an isolate payload, overriding whichever part a test needs.

    Called with no arguments it yields one genome record, one transcriptome record,
    and the organism biology for both.
    """
    sample_metadata: dict[str, Any] = {}
    if genome:
        sample_metadata["jgi_isolate_genome_data"] = list(genome)
    if transcriptome:
        sample_metadata["jgi_isolate_transcriptome_data"] = list(transcriptome)
    if biology:
        sample_metadata["isolate_data"] = list(biology)
    return sample_metadata


def test_stacks_both_isolate_interfaces_into_one_frame() -> None:
    """Verify genome and transcriptome records become rows of a single frame.

    The bacterium is submitted for genome sequencing and the fungus for
    transcriptome sequencing, but both go on one JGI Isolate sheet.
    """
    result = create_dataframe(isolate_submission(), "jgi_isolate")

    assert result["samp_name"].tolist() == [
        "bacillus_from_sed",
        "Aspergillus niger DSM 817",
    ]
    assert result["jgi_sample_name"].tolist() == ["b_cerus_sed", "a_niger_817"]
    assert result["biosafety_mat_cat"].tolist() == ["Bacteria", "Fungi"]


@pytest.mark.parametrize(
    ("interface", "record", "samp_name"),
    [
        ("genome", BACILLUS_GENOME, "bacillus_from_sed"),
        ("transcriptome", ASPERGILLUS_TRANSCRIPTOME, "Aspergillus niger DSM 817"),
    ],
)
def test_accepts_a_single_isolate_interface(
    interface: str,
    record: dict[str, Any],
    samp_name: str,
) -> None:
    """Verify a submission that uses only one isolate interface still converts."""
    empty = {"genome": (), "transcriptome": ()} | {interface: (record,)}

    result = create_dataframe(isolate_submission(**empty), "jgi_isolate")

    assert result["samp_name"].tolist() == [samp_name]


def test_raises_when_no_isolate_interface_has_records() -> None:
    """Verify isolate biology alone is not enough to build a JGI submission.

    `isolate_data` describes the organism but carries none of the JGI submission
    logistics, so there is nothing to put on the sheet.
    """
    with pytest.raises(
        ValueError,
        match="No key jgi_isolate exists in sample set record sample-set-123",
    ):
        create_dataframe(
            isolate_submission(genome=(), transcriptome=()),
            "jgi_isolate",
        )


def test_isolate_biology_merges_without_overwriting_sample_isolated_from() -> None:
    """Verify `isolate_data` merges in as biology, not as an environmental package.

    Both records carry "single colony isolate" in `sample_isolated_from`. That is a
    real free-text slot on the isolate interfaces, so it must survive rather than
    being replaced with the `isolate_data` key name the way a package key would be.
    """
    result = create_dataframe(isolate_submission(), "jgi_isolate")

    assert result["organism_genus"].tolist() == ["Bacillus", "Aspergillus"]
    assert result["strain_name"].tolist() == ["sp. sed123", "DSM 817"]
    assert result["sample_isolated_from"].tolist() == ["single colony isolate"] * 2


def test_isolate_biology_never_supplies_sample_isolated_from() -> None:
    """Verify `isolate_data` cannot become the value of `sample_isolated_from`.

    An environmental package key is turned into that column's value -- "soil_data"
    becomes "soil" -- but `isolate_data` names an interface, not a habitat. A record
    that left the slot blank must stay blank rather than inheriting the key name,
    which is the only case where the exemption is load-bearing: where the interface
    did fill the slot in, the facility side of the merge already wins.
    """
    result = create_dataframe(
        isolate_submission(genome=({**BACILLUS_GENOME, "sample_isolated_from": ""},)),
        "jgi_isolate",
    )

    assert result.loc[0, "sample_isolated_from"] == ""


@pytest.mark.parametrize(
    ("interface_value", "biology_value", "expected"),
    [
        (
            ["isolate genome sequencing"],
            ["isolate genome sequencing"],
            "isolate genome sequencing",
        ),
        ([], ["isolate genome sequencing"], "isolate genome sequencing"),
        (["isolate genome sequencing"], [], "isolate genome sequencing"),
        (["isolate genome sequencing"], ["metagenomics"], "isolate genome sequencing"),
    ],
)
def test_overlapping_slot_survives_the_merge_under_its_own_name(
    interface_value: list[str],
    biology_value: list[str],
    expected: str,
) -> None:
    """Verify a slot carried by both the interface and `isolate_data` keeps its name.

    `analysis_type` is the slot the two sides share. Without the explicit suffixes
    pandas renames both to `_x`/`_y`, the mapper can no longer find the slot, and the
    column silently comes out blank. Where both sides have a value the interface wins;
    the last case gives them different values to show which one that is.
    """
    result = create_dataframe(
        isolate_submission(
            genome=({**BACILLUS_GENOME, "analysis_type": interface_value},),
            transcriptome=(),
            biology=({**BACILLUS_BIOLOGY, "analysis_type": biology_value},),
        ),
        "jgi_isolate",
    )

    assert result.loc[0, "analysis_type"] == expected
    assert not [
        column for column in result.columns if column.endswith("_environmental")
    ]


def test_coalesces_dna_and_rna_isolation_method_slots() -> None:
    """Verify both interfaces' isolation method slots feed one template column.

    The genome interface records `dna_isolate_meth` and the transcriptome interface
    `rna_isolate_meth`; the JGI sheet has one "Sample Isolation Method" column. Both
    records use phenol/chloroform, so the RNA value is changed here to tell the two
    slots apart.
    """
    result = create_dataframe(
        isolate_submission(
            transcriptome=({**ASPERGILLUS_TRANSCRIPTOME, "rna_isolate_meth": "TRIzol"},)
        ),
        "jgi_isolate",
    )

    assert result["isolate_meth"].tolist() == ["phenol/chloroform extraction", "TRIzol"]


def test_transcriptome_rows_use_the_rna_experiment_date() -> None:
    """Verify RNA rows date from the lab experiment, DNA rows from field collection.

    `isolate_data` dates the fungus to 2024-07-12, when it was collected, but the
    transcriptome interface records the experiment on 2026-01-01. JGI asks for the
    experiment date on RNA samples, so 2026 is what belongs on the sheet. The
    bacterium has no experiment date and keeps its collection date.
    """
    result = create_dataframe(isolate_submission(), "jgi_isolate")

    assert result["collection_year"].tolist() == [2021, 2026]
    assert result["collection_month_name"].tolist() == ["February", "January"]
    assert result["collection_day"].tolist() == [19, 1]


def test_normalizes_isolate_yes_no_slots() -> None:
    """Verify every isolate yes/no slot is rendered the way JGI spells it.

    Both records answer "yes" to DNase treatment and single-colony isolation and leave
    the two fungal screening slots empty, so the "no" answer and the fungal slots are
    filled in here to cover both spellings.
    """
    result = create_dataframe(
        isolate_submission(
            transcriptome=(
                {
                    **ASPERGILLUS_TRANSCRIPTOME,
                    "dnase": "no",
                    "isolate_fungal_16s_screening": "no",
                    "isolate_its_match_unite": "yes",
                },
            )
        ),
        "jgi_isolate",
    )

    assert result["dnase"].tolist() == ["Y", "N"]
    assert result["isolate_single_colony"].tolist() == ["Y", "Y"]
    assert result.loc[1, "isolate_fungal_16s_screening"] == "N"
    assert result.loc[1, "isolate_its_match_unite"] == "Y"


def test_derives_ncbi_tax_id_from_the_classified_as_curie() -> None:
    """Verify the taxonomy CURIE reaches the template as the bare ID JGI expects.

    1423 is Bacillus subtilis and 5061 is Aspergillus niger.
    """
    result = create_dataframe(isolate_submission(), "jgi_isolate")

    assert result["ncbi_tax_id"].tolist() == ["1423", "5061"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("NCBITaxon:1423", "1423"),
        ("NCBITaxon:5061", "5061"),
        ("9606", "9606"),
        ("", ""),
    ],
)
def test_strip_ncbi_taxon_prefix(value: str, expected: str) -> None:
    """Verify only the NCBITaxon prefix is removed, and bare IDs pass through."""
    assert strip_ncbi_taxon_prefix(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("dsmz:DSM-15171", "DSM 15171"),
        ("atcc:700808", "ATCC 700808"),
        ("jcm:20004", "JCM 20004"),
        ("CIP 54.8", "CIP 54.8"),
        ("", ""),
    ],
)
def test_format_culture_collection_id(value: str, expected: str) -> None:
    """Verify stored CURIEs become the collection name and ID the JGI form asks for.

    DSMZ's local identifier already names the collection, so the prefix is dropped
    rather than repeated; ATCC's and JCM's do not, so the prefix supplies the name.
    """
    assert format_culture_collection_id(value) == expected


def test_culture_collection_id_is_derived_from_source_mat_id() -> None:
    """Verify the derivation is wired to the slot the submission portal stores it in.

    Neither isolate fills in `source_mat_id` -- the fungus carries its collection ID
    in `strain_name` instead -- so a value is supplied here.
    """
    result = create_dataframe(
        isolate_submission(
            biology=(
                BACILLUS_BIOLOGY,
                {**ASPERGILLUS_BIOLOGY, "source_mat_id": "dsmz:DSM-817"},
            )
        ),
        "jgi_isolate",
    )

    assert result.loc[1, "culture_collection_id"] == "DSM 817"
