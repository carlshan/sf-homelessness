import pandas as pd
import datetime
import numpy as np

def is_between_dates(date, begin, end):
    """
    Returns:
    ----------
    Returns a boolean indicating whether date is between begin and end
    
    Parameters: 
    ----------
    date : datetime object
    begin : datetime object
    end : datetime object
    """
    if pd.isnull(date):
        return False
    return date >= begin and date <= end

def get_days_stayed_for_quarters_in_year(year, program, valid_programs, 
                                         aggfunc=np.median):
    """
    Returns list of 4 values. Each value is the median (or another aggfunc) 
    of the days stayed by each family during the quarter.
    
    e.g., [56, 60, 70, 55] would indicate the median # of days stayed by
    families that entered in Q1 of the year is 56.
    60 for those who entered in Q2 of the year, and so forth.
    """
    
    quarter_values = []

    q1 = (datetime.datetime(year, 1, 1), datetime.datetime(year, 3, 31))
    q2 = (datetime.datetime(year, 4, 1), datetime.datetime(year, 6, 30))
    q3 = (datetime.datetime(year, 7, 1), datetime.datetime(year, 9, 30))
    q4 = (datetime.datetime(year, 10, 1), datetime.datetime(year, 12, 31))
    
    quarters = (q1, q2, q3, q4)
    
    for quarter in quarters:
        begin = quarter[0]
        end = quarter[1]
        mask = program['Program Start Date'].apply(is_between_dates, 
                                        begin=begin, 
                                        end=end)
        quarter = program[mask 
                          & program['Family?']
                          & program['Program End Date'].notnull()
                          & program['Program Name'].isin(valid_programs)]
        groups = quarter.groupby(['Family Identifier', 'Program Start Date'])
        days_per_stay = groups['Days Stayed'].mean() # taking mean is same as med/max/min
        val = aggfunc(days_per_stay)

        quarter_values.append(val)

    return quarter_values

