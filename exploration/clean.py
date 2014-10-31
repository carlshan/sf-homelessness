import pandas as pd
import numpy as np
import dateutil

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
    # we do an inner join because, since we pulled the program data after doing de-duplication,
    # there are some clients who appear in program but don't appear in hmis_client_duplicates
    hmis_client_duplicates = pd.read_csv('../data/hmis_client_duplicates.csv')
    program = program.merge(hmis_client_duplicates, on='Subject Unique Identifier', how='inner')
    program['Deduplicated Subject Unique Identifier'] = program['Duplicate ClientID'].fillna(program['Subject Unique Identifier'])
    program.drop('Duplicate ClientID', axis=1, inplace=True)

    return program

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
