# Metadata for User facility Template Transformations (MUTTs)

## Table of Contents
- [Metadata for User facility Template Transformations (MUTTs)](#metadata-for-user-facility-template-transformations-mutts)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [MUTTs User Documentation](#mutts-user-documentation)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
    - [Usage](#usage)
      - [Example 1: Generate a JGI Metagenome spreadsheet](#example-1-generate-a-jgi-metagenome-spreadsheet)
      - [Example 2: Generate a JGI Metagenome v15 spreadsheet](#example-2-generate-a-jgi-metagenome-v15-spreadsheet)
      - [Example 3: Generate an EMSL spreadsheet](#example-3-generate-an-emsl-spreadsheet)
      - [Command Options](#command-options)
  - [MUTTs Developer Documentation](#mutts-developer-documentation)
    - [Software Requirements](#software-requirements)
    - [Development Installation](#development-installation)
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

Create a `.env` file in your working directory:
```bash
echo "DATA_PORTAL_REFRESH_TOKEN=your_token_here" > .env
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
- For JGI Metagenome: `jgi_mg_header.json` or `jgi_mg_header_v15.json`
- For JGI Metatranscriptome: `jgi_mt_header.json` or `jgi_mt_header_v15.json`

### Usage

Run the `mutts` command with the required options:

```bash
mutts --help
```

Note: In the below examples there is a `--submission` optional argument that requires you to pass it an NMDC Submission UUID as value, and the way you would get that is from the URL of the Submission page when you open it up from the Submission Portal.

An example would look like below:

```
https://data.microbiomedata.org/submission/<submission-uuid>/samples
```

#### Example 1: Generate a JGI Metagenome spreadsheet
```bash
mutts --submission <submission-uuid> \
      --unique-field samp_name \
      --user-facility jgi_mg \
      --mapper input-files/jgi_mg_header.json \
      --output my-samples_jgi.xlsx
```

#### Example 2: Generate a JGI Metagenome v15 spreadsheet
```bash
mutts --submission <submission-uuid> \
      --unique-field samp_name \
      --user-facility jgi_mg \
      --mapper input-files/jgi_mg_header_v15.json \
      --output my-samples_jgi_v15.xlsx
```

#### Example 3: Generate an EMSL spreadsheet
```bash
mutts --submission <submission-uuid> \
      --user-facility emsl \
      --mapper input-files/emsl_header.json \
      --header \
      --unique-field samp_name \
      --output my-samples_emsl.xlsx
```

#### Command Options

- `-s, --submission`: Your NMDC metadata submission UUID (required)
- `-u, --user-facility`: Target facility (required): `emsl`, `jgi_mg`, `jgi_mg_lr`, or `jgi_mt`
- `-m, --mapper`: Path to the JSON mapper file (required)
- `-uf, --unique-field`: Field to uniquely identify records (required, typically `samp_name`)
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

1. **`mutts` CLI**
- Command-line application that performs the metadata conversion
- Consumes mapper files and submission data as inputs

### Software Requirements
- [Poetry](https://python-poetry.org/docs/#installing-with-the-official-installer)
- [Python](https://www.python.org/downloads/release/python-390/) 3.12 or higher

### Development Installation

1. Clone this repository
```bash
git clone https://github.com/microbiomedata/metadata-for-user-facility-template-transformations.git
cd metadata-for-user-facility-template-transformations
```

2. Install dependencies with Poetry
```bash
poetry install
```

This installs the `mutts` package in development mode and creates the `mutts` command-line tool.

3. Set up your `.env` file
```bash
cp .env.example .env  # if available, or create a new .env file
```

Add your NMDC API token:
```
DATA_PORTAL_REFRESH_TOKEN=your_token_here
```

Get your token from: https://data.microbiomedata.org/user

4. Run the CLI in development mode
```bash
poetry run mutts --help
```

### Creating Custom Mapper Files

To create a custom mapper for a new user facility, refer to the existing examples:
- [emsl_header.json](input-files/emsl_header.json) - EMSL configuration
- [jgi_mg_header.json](input-files/jgi_mg_header.json) - JGI Metagenome configuration
- [jgi_mt_header.json](input-files/jgi_mt_header.json) - JGI Metatranscriptome configuration
- [jgi_mg_header_v15.json](input-files/jgi_mg_header_v15.json) - JGI Metagenome v15 configuration
- [jgi_mt_header_v15.json](input-files/jgi_mt_header_v15.json) - JGI Metatranscriptome v15 configuration
