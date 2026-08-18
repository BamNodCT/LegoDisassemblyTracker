## To run Streamlit app
# streamlit run ./src/app.py --server.port=8501

#%%
# Imports
import streamlit as st
#from streamlit_webrtc import webrtc_streamer, WebRtcMode
#from aiortc.contrib.media import MediaPlayer
import requests
import json
import pandas as pd
# from contextlib import closing
import base64
from pathlib import Path
import io
#%%
#%%
# Webhook
webhook_url = "http://localhost:5678/webhook/legoscanner"
# IP Camera url
camera_url = "http://localhost:4444"
snapshot_url = "http://localhost:4444/video/snapshot"
# ImagePath
imagesLocation = "/workspaces/legoscanner/bricktracker/parts"
# Brickognize
brick_url = "https://api.brickognize.com"
#%%
#%%
# Helper functions
## Get Set Name from selected set
def get_name_by_display(df, display_id):
    # 1. Filter and select column
    matches = df.loc[df['setNameDisplay'] == display_id, 'setName']
    
    # 2. Return the value if found, otherwise return None
    return matches.iloc[0] if not matches.empty else None

def get_col2_by_col1(df, col1, col2, display_id):
    # 1. Filter and select column
    matches = df.loc[df[col1] == display_id, col2]
    
    # 2. Return the value if found, otherwise return None
    return matches.iloc[0] if not matches.empty else None

## Construct Payload
def payload(task,setName=None,partID=None,tracked=None,log_task=None,description=None):
    return {
        "task":task
        , "setName":setName
        , "partID":partID
        , "tracked":tracked
        , "log_task":log_task
        , "description":description
    }
## Call Webhook
def call_n8n(n8n_payload, webhook=webhook_url):
    return requests.post(webhook,n8n_payload,timeout=60)
## Convert images to data uri
def image_to_data_uri(file_path):
    """Converts a local image path to a Data URI string."""
    try:
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            # Determine extension for MIME type (simplified for jpg/png)
            ext = Path(file_path).suffix.lower()
            mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
            return f"data:{mime_type};base64,{encoded_string}"
    except FileNotFoundError:
        return None
## Read Snapshot into memory
def fetch_snapshot():
    try:
        response = requests.get(snapshot_url, timeout=10)
        response.raise_for_status()
        return response
    except Exception as e:
        print(f"❌ Failed to fetch from camera: {e}")
        return None
## Call Brickognize
def call_brickognize(image_file ,pred_color = 'false' ,top_k_items = 10, top_k_colors = 5, min_similarity_items = 0.5, min_similarity_colors=0.2):
    # Save image to memory
    image_file_like = io.BytesIO(image_file)
    # Query Params
    query_params = {
        'predict_color':pred_color
        , 'top_k_items':top_k_items
        , 'top_k_colors':top_k_colors
        , 'min_similarity_items':min_similarity_items
        , 'min_similarity_colors':min_similarity_colors
    }
    # Files
    files = {
            'query_image':('camera_capture.jpg', image_file_like, 'image/jpeg')
        }
    # Send to Brickognize
    try:
        brick_response = requests.post(f"{brick_url}/predict/parts/", params=query_params, files=files, timeout = 30)
        brick_response.raise_for_status()
        return brick_response
    except Exception as e:
        print(f"❌ Failed to get prediction: {e}")
        print(f"Response details: {brick_response.text}")
# Call flash to turn on and off
def flash(swit = 'toggle'):
    query_param = {
        "torch":swit
    }
    try:
        x = requests.get(f"{camera_url}/",params=query_param)
        x.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to start Flash: {e}")
# Create function to reset multiselect on updating part
def reset_multiselect():
    st.session_state["my_multiselect"] = []

#%%

test = False
if test:
    #%%
    # Test Webhook
    webhook_url_test = "http://localhost:5678/webhook-test/legoscanner"
    # response = requests.post(webhook_url,json=payload,timeout=60)
    #response = call_n8n(payload("GetDisTrack",setName="8811-1"),webhook_url_test)
    call_n8n(payload("Log",log_task="test",description="This is a test"),webhook_url_test)
    #%%
    #%%
    
    df = pd.DataFrame(response.json())
    test = df[df["partIDName"] == "8811-1-47297-0-0 | Large Figure Skeletal, Limb, with 2 Ball Joints (Toa Metru)"]
    test["partID"].iloc[0]
    #%%

    #%%
    flash()
    #%%

    #%%
    image_test = fetch_snapshot()
    brick_test = call_brickognize(image_test.content)
    #%%

    #%%
    brick_test.text
    #%%


# Session State Initalization
if 'lastSelectedSet' not in st.session_state:
    st.session_state.lastSelectedSet = None
if 'lastSelectedSetName' not in st.session_state:
    st.session_state.lastSelectedSetName = None
if 'testResult' not in st.session_state:
    st.session_state.testResult = None
if 'disassemblyTracker' not in st.session_state:
    st.session_state.disassemblyTracker = None
if 'setLoaded' not in st.session_state:
    st.session_state.setLoaded = False
if 'lastUpdatePart' not in st.session_state:
    st.session_state.lastUpdatePart = None
if 'viewLog' not in st.session_state:
    st.session_state.viewLog = False
if 'snapshot' not in st.session_state:
    st.session_state.snapshot = None
if 'flash' not in st.session_state:
    st.session_state.flash = False
if 'my_multiselect' not in st.session_state:
    st.session_state["my_multiselect"] = []
if 'brick_result' not in st.session_state:
    st.session_state.brick_result = None
if 'sent_brick' not in st.session_state:
    st.session_state.sent_brick = None

#%%
# Set Data Loading
@st.cache_data 
def load_set_list():
    set_response = call_n8n(payload("GetSets"))
    return pd.DataFrame(set_response.json())

try:
    sets = load_set_list()
    setsNames = sets["setNameDisplay"].to_list()
except Exception as e:
    st.error(f"Server Connection Error: {e}")
    setsNames = []
#%%

# Title of Streamlit Application
st.title("Lego Scanner")

# Always visible: Grab user input for set
setSelect = st.menu_button("Select Set", options=setsNames)

# If new set selected, load new set
if setSelect is not None:
    # Grab setName from selected set
    name = get_name_by_display(sets, setSelect)
    # If not the most recent set, reload data
    if st.session_state.lastSelectedSet != setSelect:
        # Call n8n
        check_response = call_n8n(payload("CheckSet",setName=name))
        track_response = call_n8n(payload("GetDisTrack",setName=name))
        # Save to session_state
        st.session_state.testResult = pd.DataFrame(check_response.json())
        st.session_state.disassemblyTracker = pd.DataFrame(track_response.json())
        st.session_state.lastSelectedSet = setSelect
        st.session_state.lastSelectedSetName = name
        st.session_state.setLoaded = True

# If set is loaded
if st.session_state.setLoaded:
    # Display set loaded
    st.info(f"{st.session_state.lastSelectedSet}")
    # If set is missing pieces
    if not st.session_state.testResult.empty:
        # Display Missing pieces
        st.warning('⚠️ Missing parts from Bricktracker catalogue')
        st.write(st.session_state.testResult)
        # Give option to reload
        clear = st.menu_button("Reload Set into Metrics?",options=['Yes'])
        # If Reloading
        if clear == 'Yes':
            # Call n8n
            call_n8n(payload("ReloadSet",setName=st.session_state.lastSelectedSetName))
            call_n8n(payload("Log",log_task="ReloadSet",description=f"Reloaded {st.session_state.lastSelectedSetName}"))
            # Reset session_state
            st.session_state.testResult = None
            st.session_state.disassemblyTracker = None
            st.session_state.lastSelectedSet = None
            st.session_state.lastSelectedSetName = None
            st.session_state.lastUpdatePart = None
            st.session_state.setLoaded = False
            st.session_state.snapshot = None
            # Rerun to refresh page
            st.rerun()

    # If DisassemblyTracker is not empty
    if not st.session_state.disassemblyTracker.iloc[0].empty:

        # Display Disassembly Tracker
        st.subheader(f'{st.session_state.lastSelectedSet} - Set metrics')

        disp_disTrack = st.session_state.disassemblyTracker[["partID","imageID","partName","spare","setTotal","tracked"]]
        disp_disTrack['imageID'] = disp_disTrack['imageID'].apply(lambda x: image_to_data_uri(f"{imagesLocation}/{x}.jpg"))

        st.dataframe (
            disp_disTrack,
            column_config={
                "imageID": st.column_config.ImageColumn(
                    "Part Image",
                    help="Visual Preview of the LEGO piece",
                    width="500px",
                ),
                "partID": "ID",
                "partName": "Name"
            },
            hide_index=True
        )

        # Manually update part

        parts = st.session_state.disassemblyTracker['partIDName'].sort_values().to_list()
        updatePartList = st.multiselect("Update Part",options=parts,max_selections=1, key = "my_multiselect")

        # Update Session if menu is clicked
        if updatePartList:
            st.session_state.lastUpdatePart = updatePartList[0]
        
        if st.session_state.lastUpdatePart is not None:
            part = st.session_state.disassemblyTracker[st.session_state.disassemblyTracker["partIDName"] == st.session_state.lastUpdatePart]
            partID = part["partID"].iloc[0]
            setName = part["setName"].iloc[0]
            partName = part["part"].iloc[0]
            color = part["color"].iloc[0]
            spare = part["spare"].iloc[0]
            name= part["setName"].iloc[0]
            imageID = part["imageID"].iloc[0]
            imagePath = Path(f"{imagesLocation}/{imageID}.jpg")
            totalParts = part["setTotal"].iloc[0]
            trackedParts = part["tracked"].iloc[0]

            st.info(f"Updating part {st.session_state.lastUpdatePart}")
            st.image(imagePath)
            st.write(f"Total Parts in Set: {totalParts}")
            st.write(f"Currently Counted Parts: {trackedParts}")
            updateNum = st.number_input("Update Count:",min_value=int(0),max_value=int(totalParts),step=int(1))
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Update", type='primary', on_click=reset_multiselect):
                    # Call n8n
                    call_n8n(payload("UpdatePart",partID=partID,tracked=updateNum))
                    call_n8n(payload("Log",log_task="UpdatePart",description=f"Updated{" Spare" if spare == 1 else ""} Part {partName} with Color {color} on set {setName} from {trackedParts} to {updateNum}"))
                    track_response = call_n8n(payload("GetDisTrack",setName=name))
                    # Save to session_state
                    st.session_state.disassemblyTracker = pd.DataFrame(track_response.json())
                    st.session_state.lastUpdatePart = None
                    st.rerun()
            with col2:
                if st.button("Clear", type = 'secondary'):
                    st.session_state.lastUpdatePart = None
                    st.rerun()

        ## Notes on things to do
        # With response see if can display results
        # With response see if can update disassembly_tracker

        st.subheader("Lego Identification")

        # Check if Camera is streaming
        if requests.get(f"{camera_url}/control/status").json()['streaming']:
            col3, col4, col5 = st.columns(3)
            with col3:
                if st.button("Snap Picture"):
                    with st.spinner("Focusing and capturing..."):
                        response = requests.get(snapshot_url)
                        
                        if response.status_code == 200:
                            st.session_state.snapshot = response.content
                        
                        else:
                            st.error("Failed to capture image from camera.")
            with col4:
                if st.button(f"Flash: {"On" if st.session_state.flash else "Off"}"):
                    st.session_state.flash = not st.session_state.flash
                    flash(f"{"on" if st.session_state.flash else "off"}")
                    st.rerun()
            with col5:
                if st.button("Stop Camera"):
                    requests.post(f"{camera_url}/control/stop")
                    st.rerun()
            
        else:
            if st.button("Start Camera"):
                requests.post(f"{camera_url}/control/start")
                st.rerun()
        if st.session_state.snapshot is not None:
            st.image(st.session_state.snapshot, caption="Captured Image" )
            col6, col7 = st.columns(2)
            with col6:
                if st.button("Send to Brickgonize"):
                    predict = call_brickognize(st.session_state.snapshot,pred_color='True')
                    st.session_state.brick_result = predict.json()
                    st.session_state.sent_brick = st.session_state.snapshot
                    st.write("Results Recieved!")
            with col7:
                if st.button("Clear Image"):
                    st.session_state.snapshot = None
                    st.rerun()
        if st.session_state.brick_result is not None:
            col8, col9 = st.columns(2)
            with col8:
                st.image(st.session_state.sent_brick, caption="Sent Image" )
            with col9:
                st.image(st.session_state.brick_result["items"][0]["img_url"], caption = "Predicted Part")

            p_item = st.session_state.brick_result["items"][0]
            p_color = st.session_state.brick_result["colors"][0]
            pred_item = f":blue-background[Prediction:] {p_item["id"]} - {p_item["name"]} || :blue-background[Score:] {p_item["score"]}"
            pred_color = f":blue-background[Prediction:] {p_color["id"]} - {p_color["name"]} || :blue-background[Score:] {p_color["score"]}"
            st.divider()
            st.markdown(pred_item)
            st.markdown(pred_color)
            st.divider()

            st.write(st.session_state.brick_result)
            col10, col11 = st.columns(2)
            with col10:
                if st.button("Add to Tracker"):
                    st.write("Coming Soon")
            with col11:
                if st.button("Clear Prediction and Image"):
                    st.session_state.snapshot = None
                    st.session_state.brick_result = None
                    st.rerun()

# If set is not loaded    
else:
    # Prompt to select set
    st.write('Select set to view metrics')

if st.button("View Log"):
    st.session_state.viewLog = not st.session_state.viewLog

if st.session_state.viewLog:
    st.write(pd.DataFrame(call_n8n(payload("GetLog")).json()))