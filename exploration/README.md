HMIS and Connecting Point cleaning and analysis
===

**Compiled 20 November 2014 for the City of San Francisco Mayor's Office**

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

De-duplicating individuals and determining families across time proved the hardest part of cleaning this dataset.

In Connecting Point, if the same person or family enters the waitlist as before, there is no record that they are the same family: one must instead compare personally identifying fields, (e.g. name, birth date,) to determine who is the same individual, and from there, extrapolate who is in the same family.

Similarly in HMIS, if the same person or family enters a different housing program as before, they may or may not be given the same `Family Site Identifier`, depending on if the programs are managed by the same organization.  So, like in Connecting Point, one must instead compare personally identifying fields, (e.g. name, birth date,) to determine who is the same individual, and from there, extrapolate who is in the same family.

The City of San Francisco provided us, (Bayes Impact,) with fuzzy matchings across time within and between the two datasets, created using the *RecLink* and *Link Plus* probabilistic matching software, and we used those to generate global individual and family identifiers across the two datasets.

We devised the following methodology, relying on the concept of [connected components](http://en.wikipedia.org/wiki/Connected_component_(graph_theory)) in graph theory.

1. Create a graph where each vertex represents an individual identifier, either in HMIS or in Connecting Point.
- Connect every pair of vertices in the graph that are said to be the same person by the fuzzy matchings provided by the City; this gives us a graph where each connected component represents exactly one person.
- Duplicate the graph, and connect every pair of vertices in the graph that ever showed up together, either in Connecting Point, (with the same `Caseid`,) or in HMIS, (with the same `Family Site Identifier` issued on the same date); this gives us a graph where each connected component represents exactly one family.
- For each graph, enumerate all the connected components, and assign the same global individual and family identifier to each person in the individual and family connected components, respectively.

This methodology assigns every record of the same person the same global individual identifier, (across datasets,) and assigns every record of a person in the same family the same global family identifier, (also across datasets).  This allows us to accurately see the unique families within and across datasets, (by avoiding double-counting families,) and allows us to connect families across datasets, (to see, for example, if the same family that left the waitlist entered shelter right after).