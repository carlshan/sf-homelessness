import pandas as pd
import numpy as np
import dateutil
import networkx as nx

import cp

ADULT_AGE = 18

def get_hmis_cp():
    # get raw dataframes
    hmis = get_raw_hmis()
    cp = get_raw_cp()

    # convert dates
    hmis = hmis_convert_dates(hmis)
    cp = cp_convert_dates(cp)

    # compute client and family ids across the dataframes
    (hmis, cp) = get_client_family_ids(hmis, cp)

    # get child status
    hmis = hmis_child_status(hmis)
    cp = cp_child_status(cp)

    # generate family characteristics
    hmis_generate_family_characteristics(hmis)
    cp_generate_family_characteristics(cp)

    return (hmis, cp)

###################
# get_raw methods #
###################

def get_raw_hmis():
    program = pd.read_csv('../data/hmis/program with family.csv')
    client = pd.read_csv('../data/hmis/client de-identified.csv')
    # NOTE we're taking an inner join here because the program csv got pulled after
    # the client csv, because we added the family site identifier column to program
    program = program.merge(client, on='Subject Unique Identifier', how='inner')

    return program

def get_raw_cp():
    case = pd.read_csv("../data/connecting_point/case.csv")
    case = case.rename(columns={'caseid': 'Caseid'})
    client = pd.read_csv("../data/connecting_point/client.csv")
    case = case.merge(client, on='Caseid', how='left')

    return case

#############################################
# get_client_family_ids and related methods #
#############################################

def get_client_family_ids(hmis, cp):
    hmis = hmis.rename(columns={'Subject Unique Identifier': 'Raw Subject Unique Identifier'})
    cp = cp.rename(columns={'Clientid': 'Raw Clientid'})

    # create individuals graph
    G_individuals = nx.Graph()
    G_individuals.add_nodes_from([('h', v) for v in hmis['Raw Subject Unique Identifier'].values])
    G_individuals.add_nodes_from([('c', v) for v in cp['Raw Clientid'].values])

    # add edges to compute individuals
    G_individuals.add_edges_from(group_edges('h', pd.read_csv('../data/hmis/hmis_client_duplicates_link_plus.csv'), ['Set ID'], 'Subject Unique Identifier'))
    G_individuals.add_edges_from(group_edges('c', pd.read_csv('../data/connecting_point/cp_client_duplicates_link_plus.csv'), ['Set ID'], 'Clientid'))
    G_individuals.add_edges_from(matching_edges())

    # copy individuals graph and add edges to compute families
    G_families = G_individuals.copy()
    G_families.add_edges_from(group_edges('h', hmis, ['Family Site Identifier','Program Start Date'], 'Raw Subject Unique Identifier'))
    G_families.add_edges_from(group_edges('c', cp, ['Caseid'], 'Raw Clientid'))

    # compute connected components and pull out ids for each dataframe for individuals and families
    hmis_individuals = [get_ids_from_nodes('h', c) for c in nx.connected_components(G_individuals)]
    cp_individuals = [get_ids_from_nodes('c', c) for c in nx.connected_components(G_individuals)]
    hmis_families = [get_ids_from_nodes('h', c) for c in nx.connected_components(G_families)]
    cp_families = [get_ids_from_nodes('c', c) for c in nx.connected_components(G_families)]

    # create dataframes
    hmis_individuals = create_dataframe_from_grouped_ids(hmis_individuals, 'Subject Unique Identifier')
    hmis_families = create_dataframe_from_grouped_ids(hmis_families, 'Family Identifier')
    cp_individuals = create_dataframe_from_grouped_ids(cp_individuals, 'Clientid')
    cp_families = create_dataframe_from_grouped_ids(cp_families, 'Familyid')

    # merge
    hmis = hmis.merge(hmis_individuals, left_on='Raw Subject Unique Identifier', right_index=True, how='left')
    hmis = hmis.merge(hmis_families, left_on='Raw Subject Unique Identifier', right_index=True, how='left')
    cp = cp.merge(cp_individuals, left_on='Raw Clientid', right_index=True, how='left')
    cp = cp.merge(cp_families, left_on='Raw Clientid', right_index=True, how='left')

    return (hmis, cp)

def group_edges(node_prefix, df, group_ids, individual_id):
    """
    group_edges returns the edge list from a grouping dataframe, either a Link Plus fuzzy matching,
    or a dataframe where people are connected by appearing in the same family or case.

    :param node_prefix: prefix for the nodes in the edge list.
    :type edge_fields: str.

    :param df: dataframe.
    :type df: Pandas.Dataframe.

    :param group_ids: grouping column names in grouping csv.
    :type group_ids: str.

    :param individual_id: individual id column name in grouping csv.
    :type individual_id: str.
    """
    groups = df[group_ids+[individual_id]].dropna().drop_duplicates().set_index(group_ids)
    edges = groups.merge(groups, left_index=True, right_index=True)
    return [tuple(map(lambda v: (node_prefix, v), e)) for e in edges.values]

def matching_edges():
    """
    matching_edges returns the edge list from a Connecting Point to HMIS matching csv.
    """
    matching = pd.read_csv('../data/matching/cp_hmis_match_results.csv').dropna()
    return [(('c',v[0]),('h',v[1])) for v in matching[['clientid','Subject Unique Identifier']].values]

def get_ids_from_nodes(node_prefix, nodes):
    """
    get_ids_from_subgraph takes a list of nodes from G and returns a list of the
    ids contained in only the nodes with the given prefix.

    param node_prefix: prefix for the nodes to keep.
    type node_prefix: str.

    param nodes: list of nodes from G.
    type nodes: [(str, int)].
    """
    return map(lambda pair: pair[1], filter(lambda pair: pair[0] == node_prefix, nodes))

def create_dataframe_from_grouped_ids(grouped_ids, col):
    """
    create_dataframe_from_grouped_ids takes a list of ids, grouped by individual or family, and creates
    a dataframe where each id in a group has the same id in col.

    param grouped_ids: a list of lists of ids.
    type grouped_ids: [[int]].

    param col: the name to give the single column in the dataframe.
    type col: str.
    """
    return pd.DataFrame({col: pd.Series({id: idx for idx, ids in enumerate(grouped_ids) for id in ids})})

#########################
# convert_dates methods #
#########################

def hmis_convert_dates(hmis):
    hmis['Raw Program Start Date'] = hmis['Program Start Date']
    hmis['Program Start Date'] = pd.to_datetime(hmis['Program Start Date'])
    hmis['Raw Program End Date'] = hmis['Program End Date']
    hmis['Program End Date'] = pd.to_datetime(hmis['Program End Date'])
    hmis['Raw DOB'] = hmis['DOB']
    hmis['DOB'] = pd.to_datetime(hmis['DOB'])

    return hmis

def cp_convert_dates(cp):
    cp['Raw servstart'] = cp['servstart']
    cp['servstart'] = pd.to_datetime(cp['servstart'])
    cp['Raw servend'] = cp['servend']
    cp['servend'] = pd.to_datetime(cp['servend'])

    return cp

####################################
# child_status and related methods #
####################################

def hmis_child_status(hmis):
    hmis['Age Entered'] = hmis.apply(get_hmis_age_entered, axis=1)
    hmis['Child?'] = hmis['Age Entered'] < ADULT_AGE
    hmis['Adult?'] = ~hmis['Child?']

    return hmis

def get_hmis_age_entered(row):
    start_date = row['Program Start Date']
    dob = row['DOB']
    if start_date is pd.NaT or dob is pd.NaT:
        return np.NaN
    else:
        return dateutil.relativedelta.relativedelta(start_date, dob).years

def cp_child_status(cp):
    cp['Child?'] = cp['age'] < ADULT_AGE
    cp['Adult?'] = ~cp['Child?']

    return cp

##############################################
# family_characteristics and related methods #
##############################################

def hmis_generate_family_characteristics(hmis):
    return generate_family_characteristics(hmis, family_id='Family Identifier', edge_fields=['Family Site Identifier', 'Program Start Date'])

def cp_generate_family_characteristics(cp):
    return generate_family_characteristics(cp, family_id='Familyid', edge_fields=['Caseid'])

def generate_family_characteristics(df, family_id, edge_fields):
    df['With Child?'] = df.groupby(edge_fields)['Child?'].transform(any)
    df['With Adult?'] = df.groupby(edge_fields)['Adult?'].transform(any)
    df['With Family?'] = df['With Child?'] & df['With Adult?']
    df['Family?'] = df.groupby(family_id)['With Family?'].transform(any)
    return df
