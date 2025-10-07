import pandas as pd
from typing import Dict, List, Union


class SpreadsheetCreator:
    """
    Creates a spreadsheet based on a JSON mapper and metadata DataFrame.
    """

    def __init__(
        self,
        user_facility: str,
        json_mapper: Dict[str, Dict[str, Union[str, List[str]]]],
        metadata_df: pd.DataFrame,
    ) -> None:
        """
        Initialize the SpreadsheetCreator.

        :param json_mapper: The JSON mapper specifying column mappings.
        :param metadata_df: The metadata DataFrame to create the spreadsheet from.
        """
        self.user_facility = user_facility
        self.json_mapper = json_mapper
        self.metadata_df = metadata_df

    def combine_headers_df(self, header: bool) -> pd.DataFrame:
        """
        Combines and formats the headers DataFrame.

        :param header: True if the headers should be included, False otherwise.
        :return: The combined headers DataFrame.
        """
        d: Dict[str, List[Union[str, List[str]]]] = {}
        for k, v in self.json_mapper.items():
            l: List[Union[str, List[str]]] = [
                h for h_n, h in v.items() if h_n != "sub_port_mapping"
            ]
            d[k] = l

        headers_df: pd.DataFrame = pd.DataFrame(d)

        if header:
            last_row = headers_df.iloc[-1]
            column_values: List[str] = list(last_row)

            headers_df = headers_df.drop(headers_df.index[-1])
            headers_df.loc[len(headers_df)] = headers_df.columns.to_list()
            headers_df.columns = column_values

            shift = 1
            headers_df = pd.concat(
                [headers_df.iloc[-shift:], headers_df.iloc[:-shift]], ignore_index=True
            )

        return headers_df

    def combine_sample_rows_df(self) -> pd.DataFrame:
        """
        Combines and formats the sample rows DataFrame.

        :return: The combined sample rows DataFrame.
        """
        rows_df: pd.DataFrame = pd.DataFrame()
        for k, v in self.json_mapper.items():
            if (
                "sub_port_mapping" in v
                and v["sub_port_mapping"] in self.metadata_df.columns.to_list()
            ):
                if "header" in v:
                    rows_df[v["header"]] = self.metadata_df[v["sub_port_mapping"]]
                else:
                    rows_df[k] = self.metadata_df[v["sub_port_mapping"]]

        return rows_df

    def combine_headers_and_rows(
        self, headers_df: pd.DataFrame, rows_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Combines the headers and sample rows DataFrames.

        :param headers_df: The headers DataFrame.
        :param rows_df: The sample rows DataFrame.
        :return: The combined DataFrame.
        """

        # Account for specialized EMSL user facility mapping:
        if self.user_facility == "emsl":

            # Extract the header mapping keywords and column titles from headers_df
            # These will be used to map the info in rows_df into the new df
            mapping_keywords = headers_df.iloc[2].values
            column_titles = headers_df.columns

            # Go through rows_df data and select cols where the mapping keywords match
            # (exist in both headers_df and rows_df), and insert NaN for missing data
            matched_data = {
                title: rows_df.get(keyword, pd.Series([None] * len(rows_df)))
                for title, keyword in zip(column_titles, mapping_keywords)
            }

            # Create new df for aligned column data
            matching_rows_df = pd.DataFrame(matched_data)

            # Combind aligned data with headers_df by keeping the header and
            # appending the aligned rows_df data
            combined = pd.concat([headers_df, matching_rows_df], ignore_index=True)

            return combined

        # Otherwise, JGI user facility:
        else:
            return pd.concat([headers_df, rows_df], ignore_index=True)

    def create_spreadsheet(self, header: bool) -> pd.DataFrame:
        """
        Creates the spreadsheet based on the JSON mapper and metadata DataFrame.

        :param header: True if the headers should be included, False otherwise.
        :return: The created spreadsheet.
        """
        headers_df = self.combine_headers_df(header)
        rows_df = self.combine_sample_rows_df()
        spreadsheet = self.combine_headers_and_rows(headers_df, rows_df)
        return spreadsheet
