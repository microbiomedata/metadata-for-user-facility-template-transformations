# Metadata for User facility Template Transformations (MUTTs)

## Table of Contents
- [Metadata for User facility Template Transformations (MUTTs)](#metadata-for-user-facility-template-transformations-mutts)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [MUTTs User Documentation](#mutts-user-documentation)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
    - [Updating to the Latest Version](#updating-to-the-latest-version)
    - [Usage](#usage)
      - [Example 1: Generate a JGI Metagenome spreadsheet](#example-1-generate-a-jgi-metagenome-spreadsheet)
      - [Example 2: Generate a JGI Metagenome v15 spreadsheet](#example-2-generate-a-jgi-metagenome-v15-spreadsheet)
      - [Example 3: Generate an EMSL spreadsheet](#example-3-generate-an-emsl-spreadsheet)
      - [Example 4: Generate a JGI Isolate v19 spreadsheet](#example-4-generate-a-jgi-isolate-v19-spreadsheet)
      - [Command Options](#command-options)
  - [MUTTs Developer Documentation](#mutts-developer-documentation)
    - [Software Requirements](#software-requirements)
    - [Development Installation](#development-installation)
    - [Running Tests](#running-tests)
    - [Creating Custom Mapper Files](#creating-custom-mapper-files)

## Introduction

The programs bundled in this repository automatically retrieve Biosample metadata records for studies submitted to NMDC through the [NMDC Submission Portal](https://data.microbiomedata.org/submission/home), and convert the metadata into Excel spreadsheets that are accepted by [DOE user facilities](https://www.energy.gov/science/office-science-user-facilities).

---

## MUTTs User Documentation

The documentation and setup instructions in this section are meant for any user who would like to install the MUTTs Python package and use it's transformation capabilities to convert data from the NMDC Submission Portal into an Excel spreadsheet that follows a template, based on the MUTTs JSON mapper file that is used.

### Prerequisites
- [Python](https://www.python.org/downloads/) 3.12 or higher
- An [NMDC user account](https://data.microbiomedata.org/) with an API access token

> To create an NMDC user account you will need to sign up at the above link by clicking on the 'ORCID LOGIN' button/link at the top right corner of the NMDC site, and signing in appropriately with your ORCID credentials

**Setting up your API access token**

This is required for running the examples in the [Usage](#usage) section below (after going through all the [Installation](#installation) steps).

Create a `.env` file in your working directory with the following environment variables:
```bash
echo "DATA_PORTAL_REFRESH_TOKEN=your_token_here" > .env
echo "SUBMISSION_PORTAL_BASE_URL=https://data.microbiomedata.org" >> .env
```

To get your access token:
1. Visit https://data.microbiomedata.org/user
2. Copy your Refresh Token
3. Replace `your_token_here` in the `.env` file with your token

### Installation

1. **Create a virtual environment** (recommended)
```bash
python -m venv mutts-env
source mutts-env/bin/activate  # On Windows: mutts-env\Scripts\activate
```

2. **Install the MUTTs package from PyPI**
```bash
pip install mutts
```

3. **Download any of the MUTTs JSON mapper configuration files**

*Note*: It is not mandatory that you need to download/use any of the pre-existing/already defined JSON mapper files that are present in this repository. You can always define your own custom JSON mapper files that follow a format similar to the ones defined in this repo.

Create a directory for your mapper files and download them from this repository:
```bash
mkdir input-files
cd input-files
```

Download the mapper files you need from the [input-files directory](https://github.com/microbiomedata/metadata-for-user-facility-template-transformations/tree/main/input-files):
- For EMSL: `emsl_header.json`
- For JGI Metagenome: `jgi_mg_header.json`, `jgi_mg_header_v15.json` or `jgi_mg_header_v16.json`
- For JGI Metatranscriptome: `jgi_mt_header.json`, `jgi_mt_header_v15.json` or `jgi_mt_header_v16.json`
- For JGI Isolate: `jgi_isolate_header_v19.json`

### Updating to the Latest Version

To ensure you have the latest features and bug fixes, you can upgrade the MUTTs package from PyPI:

```bash
pip install --upgrade mutts
```

To check your currently installed version:
```bash
pip show mutts
```

You can also install a specific version if needed:
```bash
pip install mutts==<version>
```

### Usage

Run the `mutts` command with the required options:

```bash
mutts --help
```

Note: In the below examples there is a `--sample-set` argument that requires you to pass it an NMDC Sample Set UUID as value. Each NMDC Submission has one or more Sample Sets associated with it. You can find the Sample Set UUIDs for your Submission by visiting the NMDC Submission Portal and navigating to the Sample Metadata page for a Sample Set within a Submission. The URL will contain the Sample Set UUID.

An example would look like below:

```
https://data.microbiomedata.org/submission/<submission-uuid>/sample_set/<sample-set-uuid>/samples
```

#### Example 1: Generate a JGI Metagenome spreadsheet
```bash
mutts --sample-set <sample-set-uuid> \
      --user-facility jgi_mg \
      --mapper input-files/jgi_mg_header.json \
      --output my-samples_jgi.xlsx
```

#### Example 2: Generate a JGI Metagenome v15 spreadsheet
```bash
mutts --sample-set <sample-set-uuid> \
      --user-facility jgi_mg \
      --mapper input-files/jgi_mg_header_v15.json \
      --output my-samples_jgi_v15.xlsx
```

#### Example 3: Generate an EMSL spreadsheet
```bash
mutts --sample-set <sample-set-uuid> \
      --user-facility emsl \
      --mapper input-files/emsl_header.json \
      --header \
      --output my-samples_emsl.xlsx
```

#### Example 4: Generate a JGI Isolate v19 spreadsheet
```bash
mutts --sample-set <sample-set-uuid> \
      --user-facility jgi_isolate \
      --mapper input-files/jgi_isolate_header_v19.json \
      --output my-samples_jgi_isolate_v19.xlsx
```

If your submission has both isolate genome (DNA) and isolate transcriptome (RNA) samples, this single command puts them all on one spreadsheet, one row per sample. The organism details you entered once — genus, species, strain, NCBI taxonomy ID — appear on every row for that organism.

Some columns only apply to one kind of sample and are left blank on the others. The ribosomal sequence and fungal screening questions, for example, are asked of genome samples. And on transcriptome rows the collection date columns hold the date of the lab experiment rather than the date the organism was collected, which is what JGI asks for on RNA samples.

#### Command Options

- `-s, --sample-set`: Your NMDC sample set UUID (required)
- `-u, --user-facility`: Target facility (required): `emsl`, `jgi_mg`, `jgi_mg_lr`, `jgi_mt`, or `jgi_isolate`
- `-m, --mapper`: Path to the JSON mapper file (required)
- `-o, --output`: Output Excel file path (required)
- `-h, --header`: Include headers in output (use for EMSL, omit for JGI)

---

## MUTTs Developer Documentation

The documentation and setup instructions in this section are largely meant for any developer/programmer whose primary use case is to extend/improve/build upon the current capabilities of the MUTTs software.

The software consists of two main components:

1. **JSON Mapper Configuration Files**
- Controls/specifies the mapping between columns from the NMDC Submission Portal and column names used in the output spreadsheets
- Top-level keys indicate main headers in the output
- Numbered keys add clarifying header information
- The `header` keyword allows custom column names
- The `sub_port_mapping` keyword specifies mappings between Submission Portal columns/slots (as dictated by the [NMDC submission schema](https://microbiomedata.github.io/submission-schema/)) and user facility template columns
- Examples available in [input-files/](input-files/)

2. **`mutts` CLI**
- Command-line application that performs the metadata conversion
- Consumes mapper files and submission sample set data as inputs

### Software Requirements
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Python](https://www.python.org/downloads/) 3.12 or higher (can be installed via [uv](https://docs.astral.sh/uv/concepts/python-versions/#installing-a-python-version))

### Development Installation

1. Clone this repository
```bash
git clone https://github.com/microbiomedata/metadata-for-user-facility-template-transformations.git
cd metadata-for-user-facility-template-transformations
```

2. Install dependencies
```bash
uv sync
```

This creates or synchronizes the project's virtual environment, installs `mutts` in development mode, includes the development dependencies, and creates the `mutts` command-line tool.

3. Set up your `.env` file
```bash
cp .env.example .env  # if available, or create a new .env file
```

Add your NMDC API token and submission portal base URL:
```
DATA_PORTAL_REFRESH_TOKEN=your_token_here
SUBMISSION_PORTAL_BASE_URL=https://data.microbiomedata.org
```

Get your token from: https://data.microbiomedata.org/user

4. Run the CLI in development mode
```bash
uv run mutts --help
```

### Running Tests

#### Unit Tests

The unit tests are isolated from NMDC services, so they do not require an API token, a `.env` file, or network access. This is also the test suite run for pull requests.

Run the complete unit test suite:

```bash
uv run pytest
```

Run a single test file:

```bash
uv run pytest tests/test_dataframe.py
```

Run a single test function:

```bash
uv run pytest tests/test_dataframe.py::test_merges_environmental_records_by_sample_name
```

#### Integration Test

The integration test makes authenticated, read-only requests to the configured `nmdc-server` instance. It refreshes an access token, reads one stable sample set, and verifies that MUTTs can produce a DataFrame containing an expected sample.

In addition to the URL and token environment variables described above, the integration test requires three additional environment variables. Add these to your `.env` file to run the integration test locally:

```dotenv
INTEGRATION_TEST_SAMPLE_SET_ID=<test-sample-set-id>
INTEGRATION_TEST_USER_FACILITY=<test-user-facility>
INTEGRATION_TEST_EXPECTED_SAMPLE_NAME=<test-sample-name>
```

Then run the integration test with:

```bash
uv run pytest -m integration
```

Pytest excludes integration tests by default. Selecting the integration marker explicitly overrides that default.

The **Dev nmdc-server integration tests** GitHub Actions workflow runs nightly and can also be started manually. It is configured through repository secrets and variables to talk to the deployed dev `nmdc-server` instance. The workflow tests both the default-branch (`main`) source and the latest published MUTTs package:

| Published MUTTs | Default-branch MUTTs | Meaning                                                                                               |
|-----------------|----------------------|-------------------------------------------------------------------------------------------------------|
| Pass            | Pass                 | Dev `nmdc-server` remains compatible with current and future MUTTs.                                   |
| Fail            | Pass                 | A compatible MUTTs change exists but has not been published.                                          |
| Fail            | Fail                 | The `nmdc-server` contract, deployment, authentication, fixture, or shared client path may be broken. |
| Pass            | Fail                 | Published users remain safe; MUTTs development has regressed.                                         |

Failures create or update one GitHub issue. A successful recovery comments on and closes that issue.

### Creating Custom Mapper Files

To create a custom mapper for a new user facility, refer to the existing examples:
- [emsl_header.json](input-files/emsl_header.json) - EMSL configuration
- [jgi_mg_header.json](input-files/jgi_mg_header.json) - JGI Metagenome configuration
- [jgi_mt_header.json](input-files/jgi_mt_header.json) - JGI Metatranscriptome configuration
- [jgi_mg_header_v15.json](input-files/jgi_mg_header_v15.json) - JGI Metagenome v15 configuration
- [jgi_mt_header_v15.json](input-files/jgi_mt_header_v15.json) - JGI Metatranscriptome v15 configuration
- [jgi_mg_header_v16.json](input-files/jgi_mg_header_v16.json) - JGI Metagenome v16 configuration
- [jgi_mt_header_v16.json](input-files/jgi_mt_header_v16.json) - JGI Metatranscriptome v16 configuration
- [jgi_isolate_header_v19.json](input-files/jgi_isolate_header_v19.json) - JGI Isolate v19 configuration

A handful of `sub_port_mapping` values do not name a submission schema slot directly, but a column derived in [`src/mutts/dataframe.py`](src/mutts/dataframe.py) — for example `collection_year`, `collection_month_name` and `country_name`. The JGI Isolate mapper adds three more: `ncbi_tax_id` (from `classified_as`, with the `NCBITaxon:` prefix removed), `culture_collection_id` (from `source_mat_id`, rendered as the collection name and ID rather than a CURIE) and `isolate_meth` (from `dna_isolate_meth` or `rna_isolate_meth`, whichever the row has). A mapping that names neither a slot nor a derived column is silently skipped, leaving that column blank.
