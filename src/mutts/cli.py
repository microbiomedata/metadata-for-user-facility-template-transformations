import json
import os

import click
import pandas as pd
from dotenv import load_dotenv, dotenv_values
from openpyxl.styles import Alignment
import warnings

# Silence the specific OpenPyXL extension warning
warnings.filterwarnings(
    "ignore",
    message=".*extension is not supported and will be removed",
    category=UserWarning,
    module="openpyxl"
)
from typing import Dict, List, Union

from mutts.dataframe import USER_FACILITY_DATA_KEYS
from mutts.retriever import MetadataRetriever
from mutts.spreadsheet import SpreadsheetCreator


# Mappers whose output should carry the INSTRUCTIONS and PLATE LOCATIONS tabs from
# a JGI template, keyed by mapper file name -> workbook under static-excel-tabs/.
# The v15 and v16 metagenome/metatranscriptome mappers share the v15 workbook.
STATIC_TABS_BY_MAPPER = {
    "jgi_mg_header_v15.json": "JGI.Metagenome.NA.v15.xlsx",
    "jgi_mt_header_v15.json": "JGI.Metagenome.NA.v15.xlsx",
    "jgi_mg_header_v16.json": "JGI.Metagenome.NA.v15.xlsx",
    "jgi_mt_header_v16.json": "JGI.Metagenome.NA.v15.xlsx",
    "jgi_isolate_header_v19.json": "JGI.Isolate.NA.v19.xlsx",
}

STATIC_TAB_NAMES = ("INSTRUCTIONS", "PLATE LOCATIONS")


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
@click.option("--sample-set", "-s", required=True, help="Sample set id.")
@click.option(
    "--user-facility",
    "-u",
    required=True,
    type=click.Choice(list(USER_FACILITY_DATA_KEYS.keys()), case_sensitive=False),
    help="User facility to send data to."
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
    "--output",
    "-o",
    required=True,
    help="Path to result output XLSX file.",
)
def cli(
    sample_set: str,
    user_facility: str,
    header: bool,
    mapper: str,
    output: str,
) -> None:
    """
    Command-line interface for creating a spreadsheet based on metadata records.

    :param sample_set: The ID of the sample set.
    :param user_facility: The user facility to retrieve data from.
    :param header: True if the headers should be included, False otherwise.
    :param mapper: Path to the JSON mapper specifying column mappings.
    :param output: Path to the output XLSX file.
    """
    load_dotenv()
    env_path = os.path.join(os.getcwd(), ".env")
    env_vars = dotenv_values(env_path)
    for key, value in env_vars.items():
        os.environ[key] = value

    metadata_retriever = MetadataRetriever(sample_set, user_facility)
    metadata_df = metadata_retriever.retrieve_metadata_records()

    with open(mapper, "r") as f:
        json_mapper: Dict[str, Dict[str, Union[str, List[str]]]] = json.load(f)

    spreadsheet_creator = SpreadsheetCreator(user_facility, json_mapper, metadata_df)
    user_facility_spreadsheet = spreadsheet_creator.create_spreadsheet(header)

    # Write the main data sheet and copy static sheets from template
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Write the generated data to 'DATA SHEET'
        user_facility_spreadsheet.to_excel(writer, index=False, sheet_name='DATA SHEET')

        # Check if the mapper targets a JGI template that ships static tabs
        static_excel_name = STATIC_TABS_BY_MAPPER.get(os.path.basename(mapper))

        if static_excel_name is not None:
            static_excel_path = os.path.join(
                os.path.dirname(__file__), 'static-excel-tabs', static_excel_name
            )

            # Copy INSTRUCTIONS and PLATE LOCATIONS sheets from the JGI template
            # static file if it exists
            if os.path.exists(static_excel_path):
                static_excel = pd.ExcelFile(static_excel_path)
                for tab_name in STATIC_TAB_NAMES:
                    if tab_name in static_excel.sheet_names:
                        tab_df = pd.read_excel(static_excel, tab_name)
                        tab_df.to_excel(writer, index=False, sheet_name=tab_name)

        # Apply formatting to all sheets
        for sheet_name in writer.book.sheetnames:
            worksheet = writer.book[sheet_name]
            format_worksheet(worksheet)

    # Display success message with output file path
    output_path = os.path.abspath(output)
    click.echo(click.style("✓ Success! ", fg="green", bold=True) + f"Output Excel file generated at:\n  {output_path}")


if __name__ == "__main__":
    cli()
