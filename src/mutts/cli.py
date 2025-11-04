import json
import os

import click
from dotenv import load_dotenv, dotenv_values
from typing import Dict, List, Union

from mutts.retriever import MetadataRetriever
from mutts.spreadsheet import SpreadsheetCreator


@click.command()
@click.option("--submission", "-s", required=True, help="Metadata submission id.")
@click.option(
    "--user-facility", "-u", required=True, help="User facility to send data to."
)
@click.option("--header/--no-header", "-h", default=False, show_default=True)
@click.option(
    "--mapper",
    "-m",
    required=True,
    type=click.Path(exists=True),
    help="Path to user facility specific JSON file.",
)
@click.option(
    "--unique-field",
    "-uf",
    required=True,
    help="Unique field to identify the metadata records.",
)
@click.option(
    "--output",
    "-o",
    required=True,
    help="Path to result output XLSX file.",
)
def cli(
    submission: str,
    user_facility: str,
    header: bool,
    mapper: str,
    unique_field: str,
    output: str,
) -> None:
    """
    Command-line interface for creating a spreadsheet based on metadata records.

    :param submission: The ID of the metadata submission.
    :param user_facility: The user facility to retrieve data from.
    :param header: True if the headers should be included, False otherwise.
    :param mapper: Path to the JSON mapper specifying column mappings.
    :param unique_field: Unique field to identify the metadata records.
    :param output: Path to the output XLSX file.
    """
    load_dotenv()
    env_path = os.path.join(os.getcwd(), ".env")
    env_vars = dotenv_values(env_path)
    for key, value in env_vars.items():
        os.environ[key] = value

    metadata_retriever = MetadataRetriever(submission, user_facility)
    metadata_df = metadata_retriever.retrieve_metadata_records(unique_field)

    with open(mapper, "r") as f:
        json_mapper: Dict[str, Dict[str, Union[str, List[str]]]] = json.load(f)

    spreadsheet_creator = SpreadsheetCreator(user_facility, json_mapper, metadata_df)
    user_facility_spreadsheet = spreadsheet_creator.create_spreadsheet(header)
    user_facility_spreadsheet.to_excel(output, index=False, sheet_name='DATA SHEET')


if __name__ == "__main__":
    cli()
