import sys
import pandas as pd     #pip install pandas
import numpy as np      #pip install numpy
from datetime import datetime, timedelta
import pytz

#==========CONFIGURATIONS: EVERY TIME========================================================================================================================================================
'''download datasheets
1) download datasheets 
    courseworks (Grades -> Action -> Export)
    gradescope (Dashboard -> <Assignment> -> Review Grades -> Download Grades -> Download CSV)
    codio (Courses -> 3 dots beside <Assignment> -> Download CSV)
2) move the csv files to directory containing autolatehours.py
3) enter the filenames to the respectivs variables below:
'''

DEADLINE_ET_STRING = '2021-07-26-23:59:59' #assignment deadline ET | format: year-month-date-hour:minute:second

CW_CSV_FILENAME = '2021-07-28T1604_Grades-COMSW3134_001_2021_2_-_DATA_STRUCTURES_IN_JAVA.csv'   #current: HW5/6
GS_CSV_FILENAME = 'Homework_5_scores.csv'                                                       #current: HW5/6
CODIO_CSV_FILENAME = 'coms-w3134---summer-2021_homework-6_1627460049979.csv'                    #current: HW5/6
OUTPUT_CSV_FILENAME = 'hw5&6_final_late_hours.csv'    #name of output csv file

WRIT_OVERRIDES_DICT = {} #add key=uni & value=waived late hours
PROG_OVERRIDES_DICT = {} #add key=uni & value=waived late hours

#==========CONFIGURATIONS: BEGINNING OF SEMESTER============================================================================================================================================
GRACE_PERIOD_HOURS = 1  #number of late hours we give away for free

#Check if column names in CSVs changed
CW_UNI = 'SIS User ID'  #column name: column of student unis
CW_NAMES = 'Student'    #column name: column of student names
CW_LATE_HOURS = 'Late Hours (663459)'

GS_UNI = 'SID'  #column name: unis
GS_SUBMIT_STATUS = 'Status' #column name: ungraded/graded or missing
GS_LATENESS = 'Lateness (H:M:S)'

CODIO_FIRSTNAME = 'first name'  #column name: usually contains mostly unis
CODIO_EMAIL = 'email'
CODIO_SUBMIT_TIME = 'completed date'    #column name: submission date & time (in UTC)
CODIO_SUBMIT_STATUS = 'completed'       #column name: TRUE or FALSE

#==========POTENTIAL IMPROVEMENTS===========================================================================================================================================================
#prog_lateness: days:hour:minute:second -> hour:minute:second only
#prog_lateness takes grace period hours into account, writ_lateness doesn't (both final late hours account for grace hours)
#Try; add .values to vectorised parameters (https://engineering.upside.com/a-beginners-guide-to-optimizing-pandas-code-for-speed-c09ef2c6a4d6)

#==========DO NOT TOUCH THE CODE BELOW=====================================================================================================================================================
DIVIDER_STRING = '======================================================================================================================='
CODIO_SUBMIT_TIMEZONE = pytz.timezone('UTC')    #timezone of codio submission timestamp
DEADLINE_TIMEZONE = pytz.timezone('US/Eastern') #timezone of DEADLINE_ET_STRING
DEADLINE_ET_wGPH = DEADLINE_TIMEZONE.localize( datetime.strptime(DEADLINE_ET_STRING, "%Y-%m-%d-%H:%M:%S") + timedelta(hours=GRACE_PERIOD_HOURS) ) #extract datetime from string -> add grace period hours -> convert to ET

#input cw & gs & codio & overrides csv -> load to dataframes
def inputs(cw_csv_nameString, gs_csv_nameString, codio_csv_nameString):
    main_df_columns = [CW_UNI, CW_NAMES, CW_LATE_HOURS]                                 #columns needed from courseworks csv
    main_df = pd.read_csv(cw_csv_nameString, usecols=main_df_columns)[main_df_columns]  #parse csv columns to df (usecols=only grab the rows we want, set column order for naming)//set column order: https://stackoverflow.com/questions/40024406/keeping-columns-in-the-specified-order-when-using-usecols-in-pandas-read-csv
    main_df.columns = ['uni', 'names', 'total_late_hours']                              #set column name

    main_df = main_df.dropna(subset=['uni'])  #drop empty rows (fake student rows)

    #set uni as index & record late hour overrides
    main_df = main_df.set_index('uni')  #set uni as index
    main_df['writ_overrides'] = main_df.index.to_series().map(WRIT_OVERRIDES_DICT)  #parse written hw overrides
    main_df['prog_overrides'] = main_df.index.to_series().map(PROG_OVERRIDES_DICT)  #parse programming hw overrides

    gs_df_columns = [GS_UNI, GS_LATENESS, GS_SUBMIT_STATUS]                         #columns needed from gradescope csv
    gs_df = pd.read_csv(gs_csv_nameString, usecols=gs_df_columns)[gs_df_columns]    #parse csv columns to df 
    gs_df.columns = ['uni','writ_lateness','writ_submit_status']                    #name columns

    codio_df_columns = [CODIO_FIRSTNAME, CODIO_EMAIL, CODIO_SUBMIT_TIME, CODIO_SUBMIT_STATUS]   #columns needed from codio csv
    codio_df = pd.read_csv(codio_csv_nameString, usecols=codio_df_columns)[codio_df_columns]    #parse csv columns to df
    codio_df.columns = ['?uni?', 'email', 'prog_submit_time', 'prog_submit_status']             #name columns

    return gs_df, codio_df, main_df

#written hw late hours
def writ_latehours(main_df, gs_df):
    #calculate late hours
    gs_df['writ_late_hours'] = pd.to_timedelta(gs_df['writ_lateness']) / pd.Timedelta('1 hour') #convert lateness duration to int & round to hours
    gs_df['writ_late_hours'] = gs_df['writ_late_hours'].apply(np.ceil)  #round up
    gs_df['writ_late_hours'].loc[ (0 < gs_df['writ_late_hours']) & (gs_df['writ_late_hours'] < GRACE_PERIOD_HOURS) ] = 0  #apply grace period hours (case: latehours bn 0 and grace hours -> to avoid -ve arithmetic results below)
    gs_df['writ_late_hours'].loc[ GRACE_PERIOD_HOURS <= gs_df['writ_late_hours'] ] = gs_df['writ_late_hours'] - GRACE_PERIOD_HOURS   #apply grace period hours (case: latehours > grace hours)
    
    #pass gs info to main_df
    gs_df = gs_df[gs_df['uni'].isin(main_df.index)]     #drop unenrolled students from gs_df (to avoid unenrolled students added to main_df as new rows)    //https://stackoverflow.com/questions/27965295/dropping-rows-from-dataframe-based-on-a-not-in-condition
    main_df = main_df.join( gs_df.set_index('uni') )    #join gs_df columns (rows mapped to corresponding unis) https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.join.html
    main_df['writ_late_hours'] = main_df[['writ_overrides','writ_late_hours']].min(axis=1)  #apply overrides     //https://stackoverflow.com/questions/33975128/pandas-get-the-row-wise-minimum-value-of-two-or-more-columns

    return main_df

#programming hw late hours
def prog_latehours(main_df, codio_df):
    #calculate late hours
    codio_df['prog_submit_time'] = pd.to_datetime(codio_df['prog_submit_time']).apply(lambda x: x.tz_localize(CODIO_SUBMIT_TIMEZONE).tz_convert('US/Eastern'))  #convert submit time to datetime -> convert from UTC to ET timezone
    codio_df['prog_lateness'] = pd.to_timedelta(codio_df['prog_submit_time'] - DEADLINE_ET_wGPH)    #find lateness
    codio_df['prog_lateness'].loc[ codio_df['prog_lateness'] <= timedelta(seconds=0) ] = str(timedelta(days=0, hours=0, minutes=0, seconds=0))   #set timely submissions late hours to 0   //https://stackoverflow.com/questions/2591845/comparing-a-time-delta-in-python    //https://docs.python.org/3/library/datetime.html
    codio_df['prog_late_hours'] = codio_df['prog_lateness'] / pd.Timedelta('1 hour')   #convert to int & round to hours
    codio_df['prog_late_hours'] = codio_df['prog_late_hours'].apply(np.ceil)    #round up

    #extract uni (to map to main_df)
    codio_df['uni'] = codio_df.apply(lambda row: row['?uni?'].lower() if row['?uni?'] in main_df.index else row['email'].split('@')[0] if row['email'].split('@')[0] in main_df.index else np.NaN, axis=1)  #extract uni from either first_name or email & check if uni is in main_df AKA if the student is enrolled)
    print(DIVIDER_STRING, "\n[CHECK] prog_latehours(): unable to extract uni OR not enrolled?: \n", codio_df[codio_df['uni'].isna()]) #display rows with no uni (either unable to extract OR not enrolled)

    #pass codio info to main_df
    main_df = main_df.join(codio_df.set_index('uni').drop(columns=['?uni?', 'email']))  #set uni as codio_df index -> drop uni & email column -> join with main_df
    main_df['prog_late_hours'] = main_df[['prog_overrides','prog_late_hours']].min(axis=1)  #apply overrides

    return main_df

#output final updated total late hours
def update_total_late_hours(main_df):
    main_df['writ_late_hours'].fillna(0, inplace=True)    #NaN -> 0 for calculation
    main_df['prog_late_hours'].fillna(0, inplace=True)    #NaN -> 0 for calculation
    main_df['total_late_hours'] -= (main_df['writ_late_hours'] + main_df['prog_late_hours'])    #find final total late hours

    main_df.sort_values(by=['names']).to_csv(OUTPUT_CSV_FILENAME)   #sort by names (to copy and paste to cw csv) & output to csv

#output students who used more than 24 hours
def get_exceed_24_hours(main_df):
    print(DIVIDER_STRING, '\n[OUTPUT] writ late hours > 24hrs\n', main_df[main_df['writ_late_hours'] > 24])
    print(DIVIDER_STRING, '\n[OUTPUT] prog late hours > 24hrs\n', main_df[main_df['prog_late_hours'] > 24])

def main(): #if take file names as arguements: def main(argv):
    gs_df, codio_df, main_df = inputs(CW_CSV_FILENAME, GS_CSV_FILENAME, CODIO_CSV_FILENAME)
    main_df = writ_latehours(main_df, gs_df)
    main_df = prog_latehours(main_df, codio_df)

    main_df = main_df[['names', 'total_late_hours', 'writ_lateness', 'writ_overrides', 'writ_submit_status', 'writ_late_hours', 'prog_submit_time', 'prog_lateness', 'prog_overrides', 'prog_submit_status', 'prog_late_hours']]    #reorder main_df columns
    update_total_late_hours(main_df)
    get_exceed_24_hours(main_df)

main()  #if take file names as arguements: main(sys.argv)