import streamlit as st

def get_params():    
    col1,col2,col3, col4 = st.columns(4)
    with col1:
        division = st.selectbox('Division', ['II'])
    with col2:
        tier = st.selectbox('Tier', ['SILVER'])
    with col3:
        queue = st.selectbox('Queue', ['RANKED_SOLO_5x5'])
    with col4:
        region = st.selectbox('Region', ['na1'])
    return region, queue, tier, division
