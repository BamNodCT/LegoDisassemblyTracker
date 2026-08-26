## To run Streamlit app
# streamlit run ./src/app.py --server.port=8501

################ Imports #######################
# Imports
import streamlit as st
import requests
import json
import pandas as pd
import io
import brickmover as bm
import databasemanager
import settings

################ Variables #######################

# Webhook
webhook_url = "http://localhost:5678/webhook/legoscanner"
# IP Camera url
camera_url = "http://localhost:4444"
snapshot_url = "http://localhost:4444/video/snapshot"
# ImagePath
imagesLocation = "/workspaces/legoscanner/bricktracker/parts"
# Brickognize
brick_url = "https://api.brickognize.com"

################ Functions #######################

# Helper functions

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

################ Test code ################
    
test = False
if test:

    flash()

    image_test = fetch_snapshot()
    brick_test = call_brickognize(image_test.content)

    brick_test.text

    db_test = databasemanager.DatabaseManager(settings.BRICKTRACKER_DB)
    
    truncate_query = f"""delete from disassembly_tracker
                         where [setName] = :setName;"""
    params = {"setName":"8811-1"}
    db_test.execute(truncate_query, params)
    

################ Main App ################

# Tables and Session State Initalization
bm.initialize_tables()
bm.initialize_session_state()

# Load set list
## Updates:
### - AvailableSets
### - SetsNames
bm.load_set_list()

# Title of Streamlit Application
st.title("Lego Scanner")

# Check if anysets loaded
if st.session_state.setsNames:
    # Always visible: Grab user input for set
    setSelect = st.menu_button("Select Set", options=st.session_state.setsNames)

    # If new set selected, load new set
    if setSelect is not None:
        # Load Disassembly Tracker
        bm.load_tracker(setSelect)
        ## Updates: 
        ### - TestResults
        ### - DisassemblyTracker
        ### - LastSelectedSet
        ### - LastSelectedSetName
        ### - SetLoaded

else:
    st.write("Load in set to bricktracker first to start tracking!")


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
        ## Use Menu_Button to make user double confirm they want to reset
        resetSet = st.menu_button("Reload Set into Metrics?",options=['Yes'])
        # If Reloading
        if resetSet == 'Yes':
            # Call reload set
            ## Loads in Set to Disassembly tracker and reset all session data
            bm.reset_set()
            

    # If DisassemblyTracker is not empty
    if not st.session_state.disassemblyTracker["setID"].empty:

        # Display Disassembly Tracker
        st.subheader(f'{st.session_state.lastSelectedSet} - Set metrics')
        bm.display_disassembly_tracker()

        # Display list of parts that can be updated

        parts = dict(zip(st.session_state.disassemblyTracker['partIDName'], st.session_state.disassemblyTracker["partID"]))
        #parts = st.session_state.disassemblyTracker['partIDName'].sort_values().to_list()
        updatePartList = st.multiselect("Update Part",options=sorted(parts),max_selections=1, key = "my_multiselect")

        # Update Session if menu is clicked
        if updatePartList:
            st.session_state.lastUpdatePart = updatePartList[0]
            st.session_state.lastUpdatePartID = parts[updatePartList[0]]
            st.session_state.updatePart = bm.grab_part(st.session_state.lastUpdatePartID)
        
        if st.session_state.lastUpdatePart is not None:
            # Display Update Options for lastUpdatePart
            bm.display_update_part()

            # Ask for input into what part should be updated to
            updateNum = st.number_input("Update Count:",min_value=int(0),max_value=int(st.session_state.updatePart["setTotal"]),step=int(1))
            
            # Display 2 columns
            col1, col2 = st.columns(2)
            with col1:
                # If Update trigged
                if st.button("Update", type='primary', on_click=reset_multiselect):
                    # Update part with new number
                    bm.update_disassemblyTracker(updateNumber = updateNum)
        
                    # Reload Disassembly_Tracker
                    bm.load_tracker(st.session_state.lastSelectedSet)
        
                    # Reset update state
                    bm.reset_session_state(["updatePart","lastUpdatePart","lastUpdatePartID"])
                    st.rerun()
            with col2:
                # Reset update state
                if st.button("Clear", type = 'secondary'):
                    bm.reset_session_state(["updatePart","lastUpdatePart","lastUpdatePartID"])
                    st.rerun()

        ## Notes on things to do
        # With response see if can update disassembly_tracker

        st.subheader("Lego Identification")

        try:
            requests.get(f"{camera_url}/control/status").json()['streaming']
        except Exception as e:
            st.error(f"Camera is not reachable {e}")
            camera_available = False
        
        # Check if Camera is streaming
        if camera_available:
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

#View Log toggle
if st.button("View Log"):
    st.session_state.viewLog = not st.session_state.viewLog

if st.session_state.viewLog:
    bm.load_log()