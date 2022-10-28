from autogluon.tabular import TabularPredictor, TabularDataset
import streamlit as st 

@st.cache(ttl=10)
def train_autogluon_model(df, time_limit, save_path):
    df = TabularDataset(df)
    train = df.sample(frac=0.8,random_state=200) #random state is a seeż value
    test = df.drop(train.index)

    label = 'winner'
    predictor = TabularPredictor(label=label, path=save_path).fit(train, time_limit=time_limit)

    
