import streamlit as st 
import plotly.express as px
from riotwatcher import LolWatcher, ApiError
import pandas as pd
from src.sagemaker_util import get_model_endpoint, predict
from src.get_data import pull_historical_frames
from src.build_dataset import build_training_dataset, build_match_data
from src.s3 import list_bucket


st.set_page_config(layout='wide', initial_sidebar_state='collapsed')
st.title('Historical Game Win/Loss Prediction')
st.info('Riot does not offer a real-time live game API. This tool allows the win probablity evolution (minute level) for past games only.')

col1, col2, col3, col4, col5 = st.columns([2,2,1,1,3])
with col1:
    summoner_name = st.text_input('Enter Your Summoner Name', value='joyeux2cocotier')
with col2:
    region = st.selectbox('Region', ['na1'])


watcher = LolWatcher(st.secrets['riot_api_key'])
versions = watcher.data_dragon.versions_for_region(region)

icons=  watcher.data_dragon.profile_icons(version=versions['n']['profileicon'])

@st.cache
def get_me(region, summoner_name):
    me =     watcher.summoner.by_name(region, summoner_name)
    my_ranked_stats = watcher.league.by_summoner(region, me['id'])
    my_ranked_stats = [s for s in my_ranked_stats if s['queueType'] == 'RANKED_SOLO_5x5'][0]
    my_matches = watcher.match.matchlist_by_puuid(region=region, puuid=me['puuid'], queue=420)
    return me, my_ranked_stats, my_matches

if summoner_name != '':
    me, my_ranked_stats, my_matches = get_me(region, summoner_name)
    with col4:
        icon_id_filename = icons['data'][str(me['profileIconId'])]['image']['full']
        st.image('http://ddragon.leagueoflegends.com/cdn/' + versions['n']['profileicon'] + '/img/profileicon/' + icon_id_filename, width=100)
    with col5:
        st.write(summoner_name + ' | Level ' + str(me['summonerLevel']))
        tier = my_ranked_stats['tier'] 
        if tier not in ['SILVER', 'DIAMOND']:
            st.warning('This tool only works with SILVER or DIAMOND data for now.')
        division = 'I'
        st.write(tier + ' ' + my_ranked_stats['rank'] + ' | ' + str(my_ranked_stats['leaguePoints']) + ' points') 
        wr = my_ranked_stats['wins']  / my_ranked_stats['losses']
        hot_streak = my_ranked_stats['hotStreak']
        fresh_blood = my_ranked_stats['freshBlood'] 
        st.write('Hot Streak: ' + str(hot_streak) + ' | ' + 'Fresh Blood: ' + str(fresh_blood))
        st.write('Win Rate: ' + str(round(100 * wr, 2)) + '% ('  + str(my_ranked_stats['wins']) + ' wins ; ' + str(my_ranked_stats['losses'])  + ' losses)')

    # Load model with params: Tier, Region
    
    
    match_id = st.selectbox('Pick a match', my_matches)
    
    
    def check_if_match_is_on_s3(match_id):
        is_on_s3 =  match_id + '.json'  in list_bucket('s3://league-pred-tool/' + '/'.join(['raw_data', region.upper(), tier, division]) + '/raw_match_context', return_filenames_only=True)
        return is_on_s3
    is_on_s3 = check_if_match_is_on_s3(match_id)
    if not is_on_s3:
        
        pull_historical_frames(region=region.upper(), tier=tier, division=division, number_matches = 1, id = me['id'], match_id = match_id)
    
    df = build_match_data(match_id + '.json', '/'.join(['raw_data', region.upper(), tier, division]))
    # df.fillna(0, inplace=True)
    without_label = df.fillna(0).drop('blue_team_wins', axis=1)
    
    def pred_row(row):
        input = ','.join([str(i) for i in row])
        pred =  predict(endpoint_name='silver-endpoint-v7-1', input=input)
        # blue_win_prediction = int(pred.split(',')[0].split('.')[0])
        blue_win_win_proba =  1 - float(pred.split(',')[1])
        return blue_win_win_proba
    
    # @st.cache(allow_output_mutation=True)
    def make_predictions(without_label):
        df['blue_win_win_proba'] = without_label.apply(lambda x: pred_row(x), axis=1)
        return df
    df = make_predictions(without_label)
    
    st.write('Actual match winner: blue' if df.blue_team_wins.unique()[0] == 1 else 'Match winner: red')
    predicted_winner = df.loc[df.minute == 15, 'blue_win_win_proba'].values[0]
    predicted_winner = 'blue' if predicted_winner > 0.5 else 'red'
    st.write('Predicted winner at 15mn: ' + predicted_winner)
    col = st.selectbox('Pick a column', options=df.columns, index=list(df.columns).index('blue_win_win_proba'))
    import numpy as np
    df["line_color"] = np.where(df[col]<0, 'red', 'blue')
    fig = px.bar(df, x="minute", y=col, barmode='group', color='line_color')
    st.plotly_chart(fig)    

    
    # if st.button('Pull 1000 matches'):
    #     path = pull_historical_frames(region=region.upper(), tier=tier, division=division, number_matches = 10000)
    # if st.button('Process raw data'):
    #       dataset_name = region + '_' + tier + '_' + division + '.csv'
    #     build_training_dataset(path='raw_data/NA1/SILVER/I', dataset_name=dataset_name)
    
    
    
    
    # st.subheader('Dataset Exploration')
    