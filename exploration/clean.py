import pandas as pd
import numpy as np
import dateutil
import networkx as nx

import cp

ADULT_AGE = 18

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
    program['Child?'] = program['Age Entered'] < ADULT_AGE
    program['Adult?'] = ~program['Child?']

    # deduplicate individuals
    program['Raw Subject Unique Identifier'] = program['Subject Unique Identifier']
    #program['Subject Unique Identifier'] = program_strict_deduplicate_individuals(program)
    program['Subject Unique Identifier'] = program_fuzzy_deduplicate_individuals(program)

    # generate families
    program['Family Identifier'] = program_generate_families(program)

    # generate family characteristics
    program = program_generate_family_characteristics(program)

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

def program_generate_families(program, ind_id='Subject Unique Identifier', fid='Family Site Identifier'):
    return generate_families(program, ind_id, fid, edge_fields=['Family Site Identifier', 'Program Start Date'])

def get_program_age_entered(row):
    start_date = row['Program Start Date']
    dob = row['DOB']
    if start_date is pd.NaT or dob is pd.NaT:
        return np.NaN
    else:
        return dateutil.relativedelta.relativedelta(start_date, dob).years

def program_generate_family_characteristics(program):
    program['With Child?'] = program.groupby(['Family Identifier','Program Start Date'])['Child?'].transform(any)
    program['With Adult?'] = program.groupby(['Family Identifier','Program Start Date'])['Adult?'].transform(any)
    program['With Family?'] = program['With Child?'] & program['With Adult?']
    program['Family?'] = program.groupby(['Family Identifier'])['With Family?'].transform(any)
    return program

# If persons A & B enter a shelter at the same time with the same Family Site Identifier, then we call them connected;
# if persons B & C do the same, then we call them connected, and thus A & C are connected as well.
def generate_families(df, ind_id, fid, edge_fields):
    """Given a dataframe, find the family components by creating a graph, in which edges represent two individuals
    appearing in the same program or case at the same time, and finding the connected components among the graph.

    :param df: The dataframe to consider.
    :type df: pandas.Dataframe.

    :param ind_id: The column to use as the individual identifier, (e.g. 'Subject Unique Identifier' or 'Clientid').
    :type ind_id: str.

    :param fid: The field that represents the family or case (e.g. 'Family Site Identnfier' or 'Caseid').  This field
    gets filled in for individuals in order to properly generate family IDs for them.
    :type fid: str.

    :param edge_fields: The fields of df to consider when computing edges, (e.g. ['Family Site Identifier','Program
    Start Date'] or ['Caseid']).
    :type edge_fields: str or [str].

    """
    # begin by getting relevant fields
    families = df[[ind_id]+edge_fields].copy()
    # fill in individuals' FSI with their negated SUID
    families[fid] = families[fid].fillna(-families[ind_id])
    families = families.set_index(edge_fields)

    # join families on itself to get all first-degree connections: this is a two-column dataframe, where each row
    # represents a pair of ind_ids that are directly connected to each other
    edges = families.merge(families, left_index=True, right_index=True)
    # create graph
    G = nx.Graph([tuple(e) for e in edges.values])

    # compute connected components
    components = [f for f in nx.connected_components(G)]

    # make bogus column name for temporary data frame that will be merged into larger dataframe.
    target_fid = 'target_'+fid
    # create a dataframe from the connected components: the index is the ind_id (iid) of the person, and the one column
    # is the family of which they are a part
    fids = pd.DataFrame({target_fid: pd.Series({iid: idx for idx, component in enumerate(components) for iid in component})})

    # merge resulting dataframe with original df to index it correctly, then return the series of target_fids
    return df.merge(fids, left_on=ind_id, right_index=True, how='left')[target_fid]

def get_cp_case():
    case = pd.read_csv("../data/connecting_point/case.csv")
    return case

def get_cp_client():
    client = pd.read_csv("../data/connecting_point/client.csv")

    # deduplicate individuals
    client['Raw Clientid'] = client['Clientid']
    client['Clientid'] = client_fuzzy_deduplicate_individuals(client)

    # generate families
    client['Familyid'] = client_generate_families(client)

    client = client.merge(get_cp_case(), left_on='Caseid', right_on='caseid')

    return client

def client_fuzzy_deduplicate_individuals(client):
    return link_plus_deduplicate_individuals(client, 'Clientid', '../data/connecting_point/cp_client_duplicates_link_plus.csv')

def client_generate_families(client, ind_id='Clientid', fid='Caseid'):
    return generate_families(client, ind_id, fid, edge_fields=[fid])

def link_plus_deduplicate_individuals(df, ind_id, lp_fname):
    # name of deduplicated individual id column
    dd_ind_id = 'Deduplicated '+ind_id
    # generate dd_ind_id by finding the min ind_id for every group
    lp_duplicates = pd.read_csv(lp_fname)
    lp_duplicates = lp_duplicates.drop_duplicates(ind_id)
    lp_duplicates[dd_ind_id] = lp_duplicates.groupby('Set ID')[ind_id].transform(min)
    # merge those dd_ind_ids
    return df.merge(lp_duplicates[[ind_id, dd_ind_id]], on=ind_id, how='left')[dd_ind_id].fillna(df[ind_id])
