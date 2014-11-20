HMIS and Connecting Point cleaning and analysis
===

**Compiled for the City of San Francisco Mayor's Office**

*Carl Shan, Isaac Hollander McCreery, Brent Gaisford, Swati Jain, Bayes Impact*

Overview
---

This package was created by the team at Bayes Impact for the San Francisco Mayor's Office as a final deliverable for the Fall 2014 data exploration conducted in pursuit of a Pay for Success (PFS) model to be implemented in San Francisco's homelessness services system.

Over the course of 6 weeks, the Bayes Impact team assessed, cleaned, and analyzed the data provided by the City's HMIS and Compass Connecting Point systems.  In this package are the scripts we wrote to clean the data, as well as notebooks we used for exploration and data analysis.

The files included in this package are listed below.

- **clean.py** is the script we wrote to clean the data.  It is explained more below, in the section *Data Cleaning*, and is also annotated inline.
- **util.py** is a package of a few utilities we wrote to assist with analysis.  It is annotated inline.
- TODO explanations of notebooks we are (or are not?) including.

Data Cleaning
---

The bulk of the work done on this project was in data cleaning.  **clean.py** is the authoritative source on what cleaning was done, but a brief overview is provided here.

`get_hmis_cp` is the main function to call in this script.  It pulls in relevant CSVs from `../data/`, merges them, cleans them, and returns a tuple containing the cleaned HMIS data and the cleaned Connecting Point data.  All other functions in **clean.py** are in service of `get_hmis_cp`.

Cleaning has a few steps:

1. `get_raw_hmis` and `get_raw_cp` import the raw data and merge it appropriately;
- `hmis_convert_dates` and `cp_convert_dates` parse the date columns in each dataframe;
- `get_client_family_ids` uses both dataframes, pulls in other files, and determines which people in the dataset are
	a. the same person, and
	b. in the same family
and returns the dataframes with the raw identifiers moved to `Raw ...` columns, and the new identifiers in the proper columns, (more explanation provided below);
- `hmis_child_status` and `cp_child_status` determine whether each person is a child or adult; and
- `hmis_generate_family_characteristics` and `cp_generate_family_characteristics` determine other family characteristics, such as if the person is in a family for that record, and if they are ever in a family anywhere in the dataset.

### De-duplicating individuals and determining families across time

TODO