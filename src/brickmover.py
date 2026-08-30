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
    'lastSnapshot': None,
    # Saved Results
    'availableSets': None,
    'setsNames': None,
    'disassemblyTracker': None,
    'testResult': None,
    'updatePart': None,
    'snapshot': None,
    'sent_brick': None,
    'brick_result': None,
    'camera_available': False,
    'camera_streaming': False,
    # Prediction Results
    'pred_success': False,
    'pred_score_overall': None,
    'pred_score_part': None,
    'pred_score_color': None,
    'pred_part_bl': None,
    'pred_color_bl': None,
    'pred_part': None,
    'pred_color': None,
    # Saved Settings
    'setLoaded': False,
    'my_multiselect': [],
    'viewLog': False,
    'flash': False,
    'predAddMulti': False,
    'setNotAvailable' : False,
}
## Prediction Options
pred_opt = {
    "predict_color": 'true',
    "top_k_items": 10, 
    "top_k_colors": 5, 
    "min_similarity_items": 0.5, 
    "min_similarity_colors": 0.2
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
            [id] INTEGER PRIMARY KEY,
            [date] DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ,
            [task] VARCHAR(250) NULL,
            [description] VARCHAR(250) NULL
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
            [tracked] INT NULL,
            [completed] BOOLEAN GENERATED ALWAYS AS (setTotal = tracked) STORED
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
    """ Load and Display LegoScanner_Log table to Streamlit
    """
    query = f"""
            select *
            from LegoScanner_Log
            """
    st.dataframe(db.query_df(query).sort_values(by='date', ascending=False), hide_index = True)

def load_predicted_part():
    """ Convert predicted Brick Link part and color to BrickTracker part and color.

    Args:
        part (str): PartID from bricklink
        color (str): Color id from bricklink
    """
    bounding_box = st.session_state.brick_result["bounding_box"]
    part = st.session_state.brick_result["items"][0]
    color = st.session_state.brick_result["colors"][0]

    # Grab Prediction Results
    st.session_state.pred_score_overall = bounding_box["score"]
    st.session_state.pred_score_part = part["score"]
    st.session_state.pred_score_color = color["score"]
    st.session_state.pred_part_bl = part["id"]
    st.session_state.pred_part_name_bl = part["name"]
    st.session_state.pred_color_bl = color["id"]
    st.session_state.pred_color_name_bl = color["name"]

    # Load Bricktracker PartID and Color
    params = {"part":part["id"], "color":color["id"], "setName":st.session_state.lastSelectedSetName}
    query = f"""
                select distinct r.[part] 
                    , r.[color_id]
                    , dt.PartID
                from rebrickable_parts as r
                left join disassembly_tracker as dt
                    on r.[part] = dt.[part]
                    and r.[color_id] = dt.[color]
                    and dt.setName = :setName
                where r.[bricklink_part_num] = :part
                    and r.[bricklink_color_id] = :color
            """

    try:
        partsInfo = db.query_df(query,params)
        if partsInfo.empty:
            st.error("Part not found in Bricktracker")
            st.session_state.setNotAvailable = True
            st.session_state.pred_part = None
            st.session_state.pred_color = None
            return
        partInfo = partsInfo.iloc[0].to_dict()
        st.session_state.pred_part = partInfo["part"]
        st.session_state.pred_color = partInfo["color_id"]
        partIDs = partsInfo["partID"].to_list()
        if partIDs[0] is None:
            st.error(f"Part in database but not for {st.session_state.lastSelectedSet}")
            display_other_sets(st.session_state.pred_part, st.session_state.pred_color)
            st.session_state.setNotAvailable = True
            return
    except Exception as e:
        st.error(f"{e}")
        st.session_state.pred_part = None
        st.session_state.pred_color = None
        return

    # Load part from Dissasembly Tracker
    for i, bt_partID in enumerate(partIDs):
        bt_part = grab_part(bt_partID)
        if bt_part["tracked"] < bt_part["setTotal"] or i == len(partIDs) - 1:
            if bt_part["tracked"] >= bt_part["setTotal"]:
                st.error("Part is fully collected. Below are sets with missing parts. Loading Full Part")
                display_other_sets(st.session_state.pred_part, st.session_state.pred_color)
                st.session_state.setNotAvailable = True
            st.session_state.updatePart = bt_part
        
## Database Update
        
def log_task(task: str, description: str):
    """Log Task in LegoScanner_Log table

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
    """Reset the Set in Disassembly Tracker back to match to BrickTracker Default
    """
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
    """Update Disassembly Tracker table for selected Part. Either to a specific number, or incrementing what is already in table

    Args:
        updateNumber (str): Number of Parts to update Disassembly Tracker with
        increment (bool): Set Tracked to one more than it currently is
    """
    # Pull in part information
    part = st.session_state.updatePart

    # Determine Number to insert
    if updateNumber:
        newCount = updateNumber
    elif increment:
        newCount = part["tracked"] + 1
    else:
        newCount = 0

    if newCount > part["setTotal"]:
        st.error(f"{newCount} is greater than Set Total of {part["setTotal"]}")
        logTask = "UpdatePart"
        logDescription = f"Did not update Part {part["part"]} with Color {part["color"]} on set {part["setName"]} from {part["tracked"]} to {newCount} due to part being full"
        log_task(logTask,logDescription)
        return
    
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
    
def grab_sets(partNum: str, color:str):
    """Grab all sets that a part belongs to in current bricktracker catalouge

    Args:
        partNum (str): BrickTracker Part Number
        color (str): BrickTracker Color ID
    """
    params = {"partNum":partNum, "color":color}
    query = f"""
            select setName as [Set ID], partID as [Part ID], tracked as [Current], setTotal as [Total], completed
            from disassembly_tracker
            where part = :partNum
                and color = :color
            """
    try:
        return db.query_df(query,params)  
    except Exception as e:
        st.error(f"{e}")
        return pd.dataframe(columns=['Set ID','Part ID','Current','Total'])
## Display Functions

def display_disassembly_tracker():
    """Display Disassemble Tracker Table
    """
    # Display Stats for Set
    numParts = st.session_state.disassemblyTracker["partID"].nunique()
    completedParts = st.session_state.disassemblyTracker["partID"][st.session_state.disassemblyTracker["completed"] == 1].nunique()
    completed = completedParts / numParts

    numTotalParts = int(st.session_state.disassemblyTracker["setTotal"].sum())
    completedTotalParts = int(st.session_state.disassemblyTracker["tracked"].sum())
    completedTotal = completedTotalParts / numTotalParts
    pa = st.progress(0)
    with pa: 
        st.progress(completed)
    st.markdown(f"{completedParts} / {numParts} ({completed:.0%}) unique parts completed")
    pb = st.progress(0)
    with pb:
        st.progress(completedTotal)
    st.markdown(f"{completedTotalParts} / {numTotalParts} ({completedTotal:.0%}) parts collected")
    
    # Simpler database for display
    disp_disTrack = st.session_state.disassemblyTracker[["completed","partID","imageID","partName","spare","setTotal","tracked"]]
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
            "completed" : st.column_config.CheckboxColumn(
                "✅",
                help="Part is completed",
                width="250px",
            ),
            "partID": "ID",
            "partName": "Name"
        },
        hide_index=True,
        row_height=100
    )

def display_update_part():
    """Display Update Part Selection Option when part is selected
    """
    # Grab Part information
    part = st.session_state.updatePart

    # Grab Image path from BrickTracker
    imagePath = Path(f"{imagesLocation}/{part["imageID"]}.jpg")

    # Display to User Part info
    st.info(f"Updating part {st.session_state.lastUpdatePart}")
    st.image(imagePath)
    st.write(f"Total Parts in Set: {part["setTotal"]}")
    st.write(f"Currently Counted Parts: {part["tracked"]}")

def display_prediction_add_multiparts():
    """Manually set the part count for predicted part
    """
    # Grab Part information
    part = st.session_state.updatePart

    st.write(f"Total Parts in Set: {part["setTotal"]}")
    st.write(f"Currently Counted Parts: {part["tracked"]}")
    
def display_pred():
    """Display Prediction Results from Brickognize.
    """

    # Prediction
    pred_score = f":gray-background[Overall Score:] {st.session_state.pred_score_overall:.2f} || :violet-background[Part:] {st.session_state.pred_score_part:.2f} || :rainbow-background[Color:] {st.session_state.pred_score_color:.2f}"
    pred_part = f":violet-background[{st.session_state.pred_part_bl} - {st.session_state.pred_part_name_bl}] "
    pred_color = f":rainbow-background[{st.session_state.pred_color_bl} - {st.session_state.pred_color_name_bl}] "

    # Matched Part
    if st.session_state.updatePart is not None:
        match_part = f":violet-background[Match:] {st.session_state.updatePart["partIDName"]}"
        match_color = f":rainbow-background[Match:] {st.session_state.updatePart["color"]}"
    else:
        match_part = ":red-background[No Match]"
        match_color = ":red-background[No Match]"

    st.divider()
    st.write("Prediction:")
    col1, col2 = st.columns(2)
    with col1: 
        st.markdown(pred_part)
        st.markdown(match_part)
    with col2:
        st.markdown(pred_color)
        st.markdown(match_color)
    st.markdown(pred_score)
    st.divider()

def display_other_sets(partNum: str, color:str):
    """Display all other sets that have the same Part and are missing parts

    Args:
        partNum (str): BrickTracker Part ID Number
        color (str): BrickTracker Color ID
    """
    # Grab all Sets the part is in
    setsFull = grab_sets(partNum, color)
    sets = setsFull[setsFull["completed"] == 0]
    
    if not sets.empty:
        # Create Lookup dictionary for Set ID to Set Name
        availableSets = dict(zip(st.session_state.availableSets["setName"], st.session_state.availableSets["setNameDisplay"]))
        sets["Set Name"] = sets["Set ID"].map(availableSets)

        st.dataframe(
            sets[["Set Name","Part ID","Current","Total"]],
            hide_index=True
        )
    
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

def reset_prediction():
    """ Reset all Prediction variables
    """
    # Save Last Snapshot
    st.session_state.lastSnapshot = st.session_state.snapshot
    
    # Reset update state
    reset_session_state(["updatePart", "pred_success", "pred_score_overall", "pred_score_part", "pred_score_color", "pred_part_bl", "pred_color_bl", "pred_part", "pred_color","brick_result", "snapshot","predAddMulti","sent_brick","setNotAvailable"])
    st.rerun()
## Camera Functions

def check_webcam():
    """Check if can reach Android Webcam
    """
    try:
        results = requests.get(f"{cameraURL}/control/status").json()['streaming']
        st.session_state.webcam_available = True
        st.session_state.webcam_streaming = results
    except Exception as e:
        #st.error(f"Camera is not reachable {e}")
        st.info("Webcam unavailable")
        st.session_state.webcam_available = False
        st.session_state.webcam_streaming = False

def webcam_toggle():
    """ Toggle the webcam stream on or off

    """
    try:
        response = requests.post(f"{cameraURL}/control/{"stop" if st.session_state.webcam_streaming else "start"}")
        response.raise_for_status()
        st.rerun()
    except Exception as e:
        st.error(f"{e}")
    
def take_webcam_snapshot():
    """ Take Snapshot with Webcam
    """
    with st.spinner("Focusing and capturing..."):
        try:
            response = requests.get(f"{cameraURL}/video/snapshot")
            response.raise_for_status()
            if response.status_code == 200:
                st.session_state.snapshot = response.content
            else:
                st.error("Failed to capture image from webcam.")
        except Exception as e:
            st.error(f"{e}")

def call_flash(command = 'toggle'):
    """ Call Flash toggle in Webcam

    Args:
        command (str): Command to send to Android Webcam.
                        Acceptable Values: ["toggle","on","off"]
    """
    if command not in ["toggle","on","off"]:
        raise ValueError("Invalid command for Flash Command")
    query_param = {
        "torch":command
    }
    try:
        response = requests.get(f"{cameraURL}/",params=query_param)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to start Flash: {e}")

def flash_trigger():
    """ Trigger Flash Toggle
    
    """
    st.session_state.flash = not st.session_state.flash
    call_flash(f"{"on" if st.session_state.flash else "off"}")
    st.rerun()

## Lego Classifaction Functions

def call_brickognize():
    """Call Brickgonize with Snapshot and pred_opt options define in beginning of file. Save results to session
    """
    # Save image to BIO and Type
    files = {
            'query_image':('camera_capture.jpg', io.BytesIO(st.session_state.snapshot), 'image/jpeg')
        }
    # Send to Brickognize
    try:
        brick_response = requests.post(f"{brickognizeURL}/predict/parts/", params=pred_opt, files=files, timeout = 30)
        brick_response.raise_for_status()
        st.session_state.brick_result = brick_response.json()
        st.session_state.sent_brick = st.session_state.snapshot
        st.write("Results Recieved!")
        st.session_state.pred_success = True

    except Exception as e:
        print(f"Failed to get prediction: {e}")
        print(f"Response details: {brick_response.text}")
        st.session_state.pred_success = False

