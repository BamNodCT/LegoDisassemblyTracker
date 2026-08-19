"""
SQL processes, IP Camera Calls, and Brickognize Calls
"""
# Imports
import streamlit as st
import settings
import databasemanager
from contextlib import closing
import requests
import sqlite3
import io
import pandas as pd

# Define Variables 
## IP Camera
cameraURL = settings.CAMERA_API
cameraSnapshot = f"{cameraURL}/video/snapshot"
## ImagePath
imagesLocation = settings.IMAGE_FOLDER
## Brickognize
brickognizeURL = settings.BRICKOGNIZE_API
## Bricktracker DB
bricktrackerDB = settings.BRICKTRACKER_DB
## DataBase Connection
db = databasemanager.DatabaseManager(bricktrackerDB)

''' Session State Functions'''

def initialize_session_state(reset: bool = False, subset: list = []):
    """Initilaze Session State Variables used in app.py for Streamlit.
    If pass in True and a list. Will Reset all values in list. 
    If pass in just True will reset all to defaults

    Args:
        reset (bool, optional): Reset to deafult even if exists. Defaults to False.
        subset (list, optional): List of all values to reset. Defaults to None.
    """
    defaults = {
        # Saved Vars
        'lastSelectedSet': None,
        'lastSelectedSetName': None,
        'lastUpdatePart': None,
        # Saved Results
        'availableSets': None,
        'setsNames': None,
        'disassemblyTracker': None,
        'testResult': None,
        'snapshot': None,
        'sent_brick': None,
        'brick_result': None,
        # Saved Settings
        'setLoaded': False,
        'my_multiselect': [],
        'viewLog': False,
        'flash': False,
    }

    if subset:
        for key, value in defaults.items():
            if key not in subset:
                del defaults[key]

    for key, value in defaults.items():
        if key not in st.session_state or reset:
            st.session_state[key] = value


''' Runtime Support Functions'''

def load_set_list():
    """Load all sets available in Bricktracker

    """
    query = f'''
            select concat(bs.[set], ' | ' ,rs.[name]) as setNameDisplay
                , bs.[set] as setName 
            from bricktracker_sets as bs 
            inner join rebrickable_sets as rs 
                on bs.[set] = rs.[set];
            '''
    try:
        st.session_state.availableSets = db.query_df(query)
        st.session_state.setsNames = dict(zip(st.session_state.availableSets["setNameDisplay"], st.session_state.availableSets["setName"]))
    except Exception as e:
        st.error(f"DB Connection Error: {e}")

def load_tracker(setNameDisplay: str):
    """Load Disassembly Tracker and perform test against BrickTracker.

    Args:
        setNameDisplay (str): Set selected by user
    """
    setName = st.session_state.setsNames[setNameDisplay]
    params = {"setName":setName}
    test_query = f'''
                select p.part
                from bricktracker_parts as p
                inner join bricktracker_sets as s
                on p.id = s.id
                where [set] = :setName
                and not exists (
                    select part, color, spare
                    intersect
                    select part, color, spare
                    from disassembly_tracker
                    where [setName] = :setName) 
                  '''
    dt_query = f'''
                select *
                from disassembly_tracker
                where [setName] = :setName
                '''
    st.session_state.testResult = db.query_df(test_query,params)
    st.session_state.disassemblyTracker = db.query_df(dt_query,params)
    st.session_state.lastSelectedSet = setNameDisplay
    st.session_state.lastSelectedSetNAme = setName
    st.session_state.setLoaded = True

## Get Lego Set Name from Selected Lego Set
def get_name_by_display(df: pd.DataFrame, selectedSet: str):
    """Grab the Set ID used by BrickTracker for the given 

    Args:
        df (pd.DataFrame): Df of
        display_id (str): _description_

    Returns:
        str: Set Name that matches to Bricktracker Set Name
    """
    # 1. Filter and select column
    matches = df.loc[df['setNameDisplay'] == selectedSet, 'setName']
    
    # 2. Return the value if found, otherwise return None
    return matches.iloc[0] if not matches.empty else None