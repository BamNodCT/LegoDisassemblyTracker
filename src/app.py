## To run Streamlit app
# streamlit run ./src/app.py --server.port=8501

################ Imports #######################
# Imports
import streamlit as st
import pandas as pd
import brickmover as bm
import databasemanager
import settings

import importlib

# Set the layout to wide
st.set_page_config(layout="wide")

################ Functions #######################

# Streamlit Helper functions

# Create function to reset multiselect on updating part
def reset_multiselect():
    st.session_state["my_multiselect"] = []

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
            updateNum = st.number_input("Update Count:",min_value=int(0),max_value=int(st.session_state.updatePart["setTotal"]),step=int(1),value=int(st.session_state.updatePart["tracked"]))
            
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

        # Grab Camera status
        bm.check_webcam()
        
        # Check if Camera is available and streaming
        if st.session_state.webcam_available:
            # If Webcam Streaming
            if st.session_state.webcam_streaming:
                col3, col4, col5 = st.columns(3)
                with col3:
                    # Webcam Snapshot Button
                    if st.button("Snap Picture",type="primary"):
                        bm.take_webcam_snapshot()
                with col4:
                    # Flash on or off button
                    if st.button(f"Flash: {"On" if st.session_state.flash else "Off"}",type="secondary"):
                        bm.flash_trigger()
                with col5:
                    # Stop Webcam Button
                    if st.button("Stop Webcam"):
                        bm.webcam_toggle()
            # If Webcam is off
            else:
                if st.button("Start Webcam",type="primary"):
                    bm.webcam_toggle()
            if st.button("Reload last snapshot"):
                st.session_state.snapshot = st.session_state.lastSnapshot
                st.rerun()
                
            # If Snapshot taken or available
            if st.session_state.snapshot is not None:
                # Display Snapshot
                if st.session_state.snapshot != st.session_state.sent_brick:
                    st.image(st.session_state.snapshot, caption="Captured Image", width=750 )
                col6, col7 = st.columns(2)
                with col6:
                    if st.button("Send to Brickgonize"):
                        bm.call_brickognize()
                        st.rerun()
                with col7:
                    if st.button("Clear Image"):
                        st.session_state.lastSnapshot = st.session_state.snapshot
                        st.session_state.snapshot = None
                        st.rerun()
            # If called Brickognize Prediction
            if st.session_state.pred_success:
                col8, col9 = st.columns(2)
                # Show Image Sent
                with col8:
                    st.image(st.session_state.sent_brick, caption="Sent Image", width=750 )
                # Show Part predicted
                with col9:
                    st.image(st.session_state.brick_result["items"][0]["img_url"], caption = "Predicted Part")
                #Display and load Prediction Results
                bm.load_predicted_part()
                bm.display_pred()

                if st.session_state.updatePart is not None:
                    col10, col11, col12 = st.columns(3)
                    with col10:
                        if st.button("Add to Tracker"):
                            bm.update_disassemblyTracker(increment = True)
    
                            # Reload Disassembly_Tracker
                            bm.load_tracker(st.session_state.lastSelectedSet)
                            
                            # Reset update state
                            bm.reset_prediction()
                    with col11:
                        if st.button("Add Multiple Parts to Tracker"):
                            st.session_state.predAddMulti = True
                    with col12:
                        if st.button("Clear Prediction and Sent Image"):
                            bm.reset_prediction()
                    if st.session_state.predAddMulti:
                        bm.display_prediction_add_multiparts()

                        # Ask for input into what part should be updated to
                        updateNum = st.number_input("Update Count:",min_value=int(0),max_value=int(st.session_state.updatePart["setTotal"]),step=int(1),value=int(st.session_state.updatePart["tracked"]))

                        # If Update trigged
                        if st.button("Update", type='primary'):
                            # Update part with new number
                            bm.update_disassemblyTracker(updateNumber = updateNum)
                
                            # Reload Disassembly_Tracker
                            bm.load_tracker(st.session_state.lastSelectedSet)
                            
                            # Reset update state
                            bm.reset_prediction()
                        
                else:
                    if st.button("Clear Prediction and Image"):
                        bm.reset_prediction()

# If set is not loaded    
else:
    # Prompt to select set
    st.write('Select set to view metrics')

#View Log toggle
if st.button("View Log"):
    st.session_state.viewLog = not st.session_state.viewLog

if st.session_state.viewLog:
    bm.load_log()