## To run Streamlit app
# streamlit run ./legoDisassemblyTracker/app.py --server.port=8501

import streamlit as st
from studs import universe

st.set_page_config(
    page_title="Home",
    page_icon="👾",
)

st.write("# Lego Disassembly Tracker")

# Text Blurbs
## Always Display
intro = """
LEGO Disassembly Tracker is an open-source app designed to help with the tedious task of tracking LEGO piecies when disassembling or gathering LEGO pieces for known sets. 
"""
## Display if BT not set up
setup = """
To set up the LEGO Brick Tracker please see the [LEGO Disassembly Tracker GitHub Page](https://github.com/BamNodCT/LegoDisassemblyTracker) for further instructions. (Coming Soon)
"""
## Display if BT set up but no sets
startguide = """
Congrats you were able to get BrickTracker up and running!

## To use the LEGO Brick Tracker:
1. Add sets to BrickTracker application that you want to track. 
2. Use the LEGO Disassembly Tracker to track your part collection.
    * You can either look up parts manually, or use the Webcam feature to allow for automatic indentifcation and keying.
3. Generate Reports to view current tracking status (Coming Soon)
"""
## Display if BT Set up with sets but no DT
btstartguide = """
You are so close! You have added sets to BrickTracker, now all you need to do is use the LEGO Disassembly Tracker!

Use the side panel <--- to select LEGO Dissasembly Tracker to get started!
"""
## Normal
normaltext = """
## Welcome back!

Here is your current status (Coming Soon)
"""

# Start the printing!

st.markdown(intro)

## Perform DB test
test_db = universe.test_db()
allPassed = False

if not test_db["BT"]:
    st.markdown(setup)
elif not test_db["Sets"]:
    st.markdown(startguide)
elif not test_db["DT"]:
    st.markdown(btstartguide)
else:
    allPassed = True

if allPassed:

    st.markdown(normaltext)

    