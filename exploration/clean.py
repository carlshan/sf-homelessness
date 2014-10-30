import pandas as pd

def get_program():
    program = pd.read_csv('../data/program with family.csv')

    # join personal information
    client_de_identified = pd.read_csv('../data/client de-identified.csv')
    program = program.merge(client_de_identified , on='Subject Unique Identifier')

    # convert dates
    program['Converted Program Start Date'] = pd.to_datetime(program['Program Start Date'])
    program['Converted Program End Date'] = pd.to_datetime(program['Program End Date'])
    program['Converted DOB'] = pd.to_datetime(program['DOB'])
    
    # deduplicate individuals
    # we do an inner join because, since we pulled the program data after doing de-duplication,
    # there are some clients who appear in program but don't appear in hmis_client_duplicates
    hmis_client_duplicates = pd.read_csv('../data/hmis_client_duplicates.csv')
    program = program.merge(hmis_client_duplicates, on='Subject Unique Identifier', how='inner')
    program['Deduplicated Subject Unique Identifier'] = program['Duplicate ClientID'].fillna(program['Subject Unique Identifier'])

    return program
