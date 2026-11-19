## To run Streamlit app
# streamlit run ./legoDisassemblyTracker/app.py --server.port=8501

import streamlit as st

page = st.navigation(
    [
        st.Page("pages/1_Welcome.py", title="Info", icon="📝"),
        st.Page("pages/2_Tracker.py", title="LEGO Disassembly Tracker", icon="🧱"),
    ]
)
page.run()