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
import base64
from pathlib import Path
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
## Default Session State Variables
defaults = {
    # Saved Vars
    'lastSelectedSet': None,
    'lastSelectedSetName': None,
    'lastUpdatePart': None,
    'lastUpdatePartID': None,
    # Saved Results
    'availableSets': None,
    'setsNames': None,
    'disassemblyTracker': None,
    'testResult': None,
    'updatePart': None,
    'snapshot': None,
    'sent_brick': None,
    'brick_result': None,
    # Saved Settings
    'setLoaded': False,
    'my_multiselect': [],
    'viewLog': False,
    'flash': False,
}
## DataBase Connection
db = databasemanager.DatabaseManager(bricktrackerDB)

''' Session State Functions'''

def initialize_session_state():
    """Initilaze Session State Variables used in app.py for Streamlit.

    """
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def reset_session_state(reset_vars: list):
    """Reset Session State Variables to default values

    Args:
        reset_vars (list): List of session state values to reset
    """
    for var in reset_vars:
        value = defaults[var]
        st.session_state[var] = value

def initialize_tables():
    """Creates tables in App.db for tracking

    """
    log_table = f'''
            CREATE TABLE [LegoScanner_Log] ( 
            [id] INTEGER AUTO_INCREMENT NULL,
            [date] DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ,
            [task] VARCHAR(250) NULL,
            [description] VARCHAR(250) NULL,
            PRIMARY KEY ([id])
            );

            '''
    dt_table = f'''
            CREATE TABLE [disassembly_tracker] ( 
            [setID] VARCHAR(250) NOT NULL,
            [setName] VARCHAR(250) NOT NULL,
            [partID] VARCHAR(250) NULL,
            [partIDName] VARCHAR(250) NULL,
            [part] VARCHAR(15) NULL,
            [color] INT NULL,
            [spare] BOOLEAN NULL,
            [imageID] VARCHAR(250) NULL,
            [partName] VARCHAR(250) NULL,
            [setTotal] INT NULL,
            [tracked] INT NULL
            );
            '''

    if not db.table_exists('disassembly_tracker'):
        db.execute(dt_table)
        print("Created disassembly_tracker")
    if not db.table_exists('LegoScanner_Log'):
        db.execute(log_table)
        print("Created LegoScanner_Log")

''' Runtime Support Functions'''

## Load Functions

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
    try:
        st.session_state.testResult = db.query_df(test_query,params)
        st.session_state.disassemblyTracker = db.query_df(dt_query,params)
        st.session_state.lastSelectedSet = setNameDisplay
        st.session_state.lastSelectedSetName = setName
        st.session_state.setLoaded = True
    except Exception as e:
        st.error(f"DB Connection Error: {e}")

def load_log():
    """ Load and Display Log table to Streamlit
    """
    query = f"""
            select *
            from LegoScanner_Log
            """
    st.dataframe(db.query_df(query).sort_values(by='date', ascending=False), hide_index = True)
    
## Database Update
        
def log_task(task: str, description: str):
    """

    Args:
        task (str): task completed
        description (str): description of task completed
    """
    params = {"task":task, "description":description}
    query = f"""insert into LegoScanner_Log (task, description)
                values (:task, :description);"""

    try:
        db.execute(query, params)
    except Exception as e:
        st.error(f"DB Connection Error: {e}")
        
def reset_set():

    setName = st.session_state.lastSelectedSetName
    params = {"setName":setName}

    truncate_query = f"""delete from disassembly_tracker
                         where [setName] = :setName;"""
    insert_query = f"""
                    insert into disassembly_tracker
                    select s.id as setID
                        , s.[set] as [setName]
                        , concat(s.[set],'-',p.part,'-',p.color,'-',iif(p.spare=1,1,0)) as [partID]
                        , concat(s.[set],'-',p.part,'-',p.color,'-',iif(p.spare=1,1,0),' | ',r.name) as [partIDName]
                        , p.part
                        , p.color
                        , p.spare
                        , r.image_id as imageID
                        , r.name as partName
                        , p.quantity as setTotal
                        , 0 as tracked
                    from bricktracker_sets as s
                    inner join bricktracker_parts as p
                        on s.id = p.id
                    inner join rebrickable_parts as r
                        on p.part = r.part
                        and p.color = r.color_id
                    where s.[set] = :setName
                    """
    logTask = "ReloadSet"
    logDescription = f"Reloaded {setName}"
    reset_vars = ["testResult","disassemblyTracker","lastSelectedSet", "lastSelectedSetName","lastUpdatePart","setLoaded","snapshot"]
    try:
        db.execute(truncate_query, params)
        db.execute(insert_query, params)
        log_task(logTask,logDescription)
        reset_session_state(reset_vars)
        st.rerun()
    except Exception as e:
        st.error(f"DB Connection Error: {e}")

def update_disassemblyTracker(updateNumber: int = None, increment: bool = False):

    # Pull in part information
    part = st.session_state.updatePart

    # Determine Number to insert
    if updateNumber:
        newCount = updateNumber
    elif increment:
        newCount = part["tracked"] + 1
    else:
        newCount = 0
    
    # Update Disassembly Tracker
    params = {"partID":part["partID"], "newCount": newCount}
    query = f"""Update disassembly_tracker
                set [tracked] = :newCount
                where [partID] = :partID;"""
    db.execute(query,params)
    
    # Log Task
    logTask = "UpdatePart"
    logDescription = f"Updated{" Spare" if part["spare"] == 1 else ""} Part {part["part"]} with Color {part["color"]} on set {part["setName"]} from {part["tracked"]} to {newCount}"
    log_task(logTask,logDescription)

## Display Functions

def display_disassembly_tracker():

    # Simpler database for display
    disp_disTrack = st.session_state.disassemblyTracker[["partID","imageID","partName","spare","setTotal","tracked"]]
    # Format imageID column to have URI
    disp_disTrack["imageID"] = disp_disTrack["imageID"].apply(lambda x: image_to_data_uri(f"{imagesLocation}/{x}.jpg"))

    st.dataframe(
        disp_disTrack,
        column_config= {
            "imageID": st.column_config.ImageColumn(
                "Part Image",
                help="Visual Preview of Lego Piece",
                width="500px",
            ),
            "partID": "ID",
            "partName": "Name"
        },
        hide_index=True
    )

def display_update_part():

    # Grab Part information
    part = st.session_state.updatePart

    # Grab Image path from BrickTracker
    imagePath = Path(f"{imagesLocation}/{part["imageID"]}.jpg")

    # Display to User Part info
    st.info(f"Updating part {st.session_state.lastUpdatePart}")
    st.image(imagePath)
    st.write(f"Total Parts in Set: {part["setTotal"]}")
    st.write(f"Currently Counted Parts: {part["tracked"]}")

## Support functions

def image_to_data_uri(file_path):
    """ Converts local image path to a Data URI String

    Args:
        file_path (str): Filepath to jpg, jpeg, png
    """
    try:
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            # Determine extension of file for "MIME" Type
            ext = Path(file_path).suffix.lower()
            mime_type = "image/jpeg" if ext in [".jpg",".jpeg"] else "image/png"
            return f"data:{mime_type};base64,{encoded_string}"
    except FileNotFoundError:
        return None

def grab_part(partID: str):
    """Grab all Part information for given part from Disassembly Tracker

    Args:
        partID (str): partID number matching to part in Disassembly Tracker
    """
    return st.session_state.disassemblyTracker[st.session_state.disassemblyTracker["partID"] == partID].iloc[0].to_dict()
