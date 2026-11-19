## To run Streamlit app
# streamlit run ./legoDisassemblyTracker/app.py --server.port=8501

import streamlit as st

st.set_page_config(
    page_title="Info",
    page_icon="📝",
)

st.write("# Lego Disassembly Tracker")

intro = """
LEGO Disassembly Tracker is an open-source app designed to help with the tedious task of tracking LEGO piecies when disassembling or gathering LEGO pieces for known sets. 

To set up the LEGO Brick Tracker please see the [LEGO Disassembly Tracker GitHub Page](https://github.com/BamNodCT/LegoDisassemblyTracker) for further instructions.
"""

st.markdown(intro)

## Create If statement to check if database exists, if Webcam is active, and sets exist in database
startguide = """
## To use the LEGO Brick Tracker:
1. Add sets to BrickTracker application that you want to track. 
2. Use the LEGO Disassembly Tracker to track your part collection.
    * You can either look up parts manually, or use the Webcam feature to allow for automatic indentifcation and keying.
3. Generate Reports to view current tracking status (Coming Soon)
"""

st.markdown(startguide)