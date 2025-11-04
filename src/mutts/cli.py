import json
import os

import click
import pandas as pd
from dotenv import load_dotenv, dotenv_values
from openpyxl.styles import Alignment
from typing import Dict, List, Union

from mutts.retriever import MetadataRetriever
from mutts.spreadsheet import SpreadsheetCreator


def format_worksheet(worksheet):
    """
    Apply formatting to a worksheet for better readability.

    :param worksheet: The openpyxl worksheet to format.
    """
    # Enable text wrapping and adjust column widths
    for column in worksheet.columns:
        max_length = 0
        column_letter = column[0].column_letter

        for cell in column:
            # Enable text wrapping for all cells
            cell.alignment = Alignment(wrap_text=True, vertical='top')

            # Calculate max length for column width
            try:
                if cell.value:
                    cell_length = len(str(cell.value))
                    if cell_length > max_length:
                        max_length = cell_length
            except:
                pass

        # Set column width with reasonable limits (min 10, max 50)
        adjusted_width = min(max(max_length + 2, 10), 50)
        worksheet.column_dimensions[column_letter].width = adjusted_width


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

    # Write the main data sheet and copy static sheets from template
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Write the generated data to 'DATA SHEET'
        user_facility_spreadsheet.to_excel(writer, index=False, sheet_name='DATA SHEET')

        # Path to static JGI v15 Excel template
        static_excel_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'input-files', 'static-excel-tabs', 'JGI.Metagenome.NA.v15.xlsx'
        )

        # Copy INSTRUCTIONS and PLATE LOCATIONS sheets from JGI v15 template
        # static file if it exists
        if os.path.exists(static_excel_path):
            static_excel = pd.ExcelFile(static_excel_path)
            if 'INSTRUCTIONS' in static_excel.sheet_names:
                instructions_df = pd.read_excel(static_excel, 'INSTRUCTIONS')
                instructions_df.to_excel(writer, index=False, sheet_name='INSTRUCTIONS')
            if 'PLATE LOCATIONS' in static_excel.sheet_names:
                plate_locations_df = pd.read_excel(static_excel, 'PLATE LOCATIONS')
                plate_locations_df.to_excel(writer, index=False, sheet_name='PLATE LOCATIONS')

        # Apply formatting to all sheets
        for sheet_name in writer.book.sheetnames:
            worksheet = writer.book[sheet_name]
            format_worksheet(worksheet)


if __name__ == "__main__":
    cli()
