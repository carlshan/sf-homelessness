import pandas as pd
import numpy as np
import dateutil
import networkx as nx

import cp

def get_program():
    program = pd.read_csv('../data/hmis/program with family.csv')

    # join personal information
    client_de_identified = pd.read_csv('../data/hmis/client de-identified.csv')
    program = program.merge(client_de_identified , on='Subject Unique Identifier')

    # convert dates
    program['Raw Program Start Date'] = program['Program Start Date']
    program['Program Start Date'] = pd.to_datetime(program['Program Start Date'])
    program['Raw Program End Date'] = program['Program End Date']
    program['Program End Date'] = pd.to_datetime(program['Program End Date'])
    program['Raw DOB'] = program['DOB']
    program['DOB'] = pd.to_datetime(program['DOB'])

    # get age and child/adult status
    program['Age Entered'] = program.apply(get_program_age_entered, axis=1)
    program['Child?'] = program['Age Entered'] < 18
    program['Adult?'] = ~program['Child?']

    # deduplicate individuals
    program['Raw Subject Unique Identifier'] = program['Subject Unique Identifier']
    #program['Subject Unique Identifier'] = program_strict_deduplicate_individuals(program)
    program['Subject Unique Identifier'] = program_fuzzy_deduplicate_individuals(program)

    # generate families
    #program = program.merge(program_generate_families(program), left_on='Subject Unique Identifier', right_index=True, how='left')

    # generate family characteristics
    #program = program_generate_family_characteristics(program)

    return program

# NOTE: this method isn't in use anymore.  If it starts being used again, we should generalize it to work with connecting
# point data as well, like link_plus_deduplicate_individuals is.
def program_strict_deduplicate_individuals(program):
    # We do an inner join because, since we pulled the program data after doing de-duplication,
    # there are some clients who appear in program but don't appear in hmis_client_duplicates.
    hmis_client_duplicates = pd.read_csv('../data/hmis/hmis_client_duplicates_strict.csv')
    program = program.merge(hmis_client_duplicates, on='Subject Unique Identifier', how='inner')
    #program['Raw Subject Unique Identifier'] = program['Subject Unique Identifier']
    return program['Duplicate ClientID'].fillna(program['Subject Unique Identifier'])

def program_fuzzy_deduplicate_individuals(program):
    return link_plus_deduplicate_individuals(program, 'Subject Unique Identifier', '../data/hmis/hmis_client_duplicates_link_plus.csv')

# For now, we're just using connected components: if persons A & B enter a shelter at the same time with the same
# Family Site Identifier, then we call them connected; if persons B & C do the same, then we call them connected,
# and thus A & C are connected as well.
def program_generate_families(program, suid='Subject Unique Identifier', fid_target='Family Identifier'):
    # begin by getting relevant fields
    families = program[[suid, 'Family Site Identifier', 'Program Start Date']].copy()
    # fill in individuals' FSI with their negated SUID
    families['Family Site Identifier'] = families['Family Site Identifier'].fillna(-families[suid])
    # join it on itself to get all first-degree connections
    families = families.set_index(['Family Site Identifier', 'Program Start Date'])

    # create graph
    edges = families.merge(families, left_index=True, right_index=True)
    G = nx.Graph([tuple(e) for e in edges.values])

    # compute connected components
    components = [f for f in nx.connected_components(G)]

    # create a dataframe from the conneted components, and merge it into program
    return pd.DataFrame({fid_target: pd.Series({cuid: idx for idx, component in enumerate(components) for cuid in component})})

def program_generate_family_characteristics(program):
    program['With Child?'] = program.groupby(['Family Identifier','Program Start Date'])['Child?'].transform(any)
    program['With Adult?'] = program.groupby(['Family Identifier','Program Start Date'])['Adult?'].transform(any)
    program['With Family?'] = program['With Child?'] & program['With Adult?']
    program['Family?'] = program.groupby(['Family Identifier'])['With Family?'].transform(any)
    return program

def get_cp_case():
    case = pd.read_csv("../data/connecting_point/case.csv")

    # join causes of homelessness
    causes_of_homelessness = pd.read_csv("../data/connecting_point/causes_of_homelessness.csv")
    causes_of_homelessness['HomelesscauseId'] = causes_of_homelessness['HomelesscauseId'].replace(cp.causes_of_homelessness)
    causes_of_homelessness.columns = ['caseid','Homelesscause']
    #case = case.merge(causes_of_homelessness, on='caseid')

    return case

def get_cp_client():
    client = pd.read_csv("../data/connecting_point/client.csv")

    # deduplicate individuals
    client['Raw Clientid'] = client['Clientid']
    client['Clientid'] = client_fuzzy_deduplicate_individuals(client)

    return client

def client_fuzzy_deduplicate_individuals(client):
    return link_plus_deduplicate_individuals(client, 'Clientid', '../data/connecting_point/cp_client_duplicates_link_plus.csv')

def get_program_age_entered(row):
    start_date = row['Program Start Date']
    dob = row['DOB']
    if start_date is pd.NaT or dob is pd.NaT:
        return np.NaN
    else:
        return dateutil.relativedelta.relativedelta(start_date, dob).years

def link_plus_deduplicate_individuals(df, ind_id, lp_fname):
    # name of deduplicated individual id column
    dd_ind_id = 'Deduplicated '+ind_id
    # generate dd_ind_id by finding the min ind_id for every group
    lp_duplicates = pd.read_csv(lp_fname)
    lp_duplicates = lp_duplicates.drop_duplicates(ind_id)
    lp_duplicates[dd_ind_id] = lp_duplicates.groupby('Set ID')[ind_id].transform(min)
    # merge those dd_ind_ids
    return df.merge(lp_duplicates[[ind_id, dd_ind_id]], on=ind_id, how='left')[dd_ind_id].fillna(df[ind_id])
