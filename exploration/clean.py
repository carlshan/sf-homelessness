import pandas as pd
import numpy as np
import dateutil
import networkx as nx

import cp

def get_program():
    program = pd.read_csv('../data/program with family.csv')

    # join personal information
    client_de_identified = pd.read_csv('../data/client de-identified.csv')
    program = program.merge(client_de_identified , on='Subject Unique Identifier')

    # convert dates
    program['Unconverted Program Start Date'] = program['Program Start Date']
    program['Program Start Date'] = pd.to_datetime(program['Program Start Date'])
    program['Unconverted Program End Date'] = program['Program End Date']
    program['Program End Date'] = pd.to_datetime(program['Program End Date'])
    program['Unconverted DOB'] = program['DOB']
    program['DOB'] = pd.to_datetime(program['DOB'])

    # get age and child/adult status
    program['Age Entered'] = program.apply(get_program_age_entered, axis=1)
    program['Child?'] = program['Age Entered'] < 18
    program['Adult?'] = ~program['Child?']
    
    # deduplicate individuals
    #
    # We do an inner join because, since we pulled the program data after doing de-duplication,
    # there are some clients who appear in program but don't appear in hmis_client_duplicates.
    hmis_client_duplicates = pd.read_csv('../data/hmis_client_duplicates.csv')
    program = program.merge(hmis_client_duplicates, on='Subject Unique Identifier', how='inner')
    program['Deduplicated Subject Unique Identifier'] = program['Duplicate ClientID'].fillna(program['Subject Unique Identifier'])
    program.drop('Duplicate ClientID', axis=1, inplace=True)

    # generate families
    program = generate_families(program)

    # generate family characteristics
    program['With Child?'] = program.groupby(['Family Identifier','Program Start Date'])['Child?'].transform(any)
    program['With Adult?'] = program.groupby(['Family Identifier','Program Start Date'])['Adult?'].transform(any)
    program['With Family?'] = program['With Child?'] & program['With Adult?']
    program['Family?'] = program.groupby(['Family Identifier'])['With Family?'].transform(any)

    return program

# For now, we're just using connected components: if persons A & B enter a shelter at the same time with the same
# Family Site Identifier, then we call them connected; if persons B & C do the same, then we call them connected,
# and thus A & C are connected as well.
def generate_families(program):
    # begin by getting relevant fields, then join it on itself to get all first-degree connections, and drop duplicates
    families = program[['Deduplicated Subject Unique Identifier', 'Family Site Identifier', 'Program Start Date']].dropna()
    families = families.set_index(['Family Site Identifier', 'Program Start Date'])

    # create graph
    edges = families.merge(families, left_index=True, right_index=True)
    G = nx.Graph([tuple(e) for e in edges.values])

    # compute connected components
    components = [f for f in nx.connected_components(G)]

    # create a dataframe from the conneted components, and merge it into program
    family_identifiers = pd.DataFrame({'Family Identifier': pd.Series({cuid: idx for idx, component in enumerate(components) for cuid in component})})
    return program.merge(family_identifiers, left_on='Deduplicated Subject Unique Identifier', right_index=True, how='left')

def get_cp_case():
    case = pd.read_csv("../data/cp_case.csv")

    # join causes of homelessness
    causes_of_homelessness = pd.read_csv("../data/cp_causes_of_homelessness.csv")
    causes_of_homelessness['HomelesscauseId'] = causes_of_homelessness['HomelesscauseId'].replace(cp.causes_of_homelessness)
    causes_of_homelessness.columns = ['caseid','Homelesscause']
    case = case.merge(causes_of_homelessness, on='caseid')

    return case

def get_cp_client():
    client = pd.read_csv("../data/cp_client.csv")

    # deduplicate individuals
    cp_client_duplicates = pd.read_csv('../data/cp_client_duplicates.csv')
    client = client.merge(cp_client_duplicates[['clientid', 'Duplicate ClientID']], left_on='Clientid', right_on='clientid')
    client['Deduplicated ClientID'] = client['Duplicate ClientID'].fillna(client['Clientid'])
    client.drop(['clientid', 'Duplicate ClientID'], axis=1, inplace=True)

    return client

def get_program_age_entered(row):
    start_date = row['Program Start Date']
    dob = row['DOB']
    if start_date is pd.NaT or dob is pd.NaT:
        return np.NaN
    else:
        return dateutil.relativedelta.relativedelta(start_date, dob).years
