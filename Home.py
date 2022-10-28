import streamlit as st 
from riotwatcher import LolWatcher, ApiError
import pandas as pd
from src.sagemaker_util import get_model_endpoint
from src.get_data import pull_historical_frames
from src.build_dataset import build

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

if summoner_name != '':
    me = watcher.summoner.by_name(region, summoner_name)
    my_ranked_stats = watcher.league.by_summoner(region, me['id'])
    my_ranked_stats = [s for s in my_ranked_stats if s['queueType'] == 'RANKED_SOLO_5x5'][0]
    
    with col4:
        icon_id_filename = icons['data'][str(me['profileIconId'])]['image']['full']
        st.image('http://ddragon.leagueoflegends.com/cdn/' + versions['n']['profileicon'] + '/img/profileicon/' + icon_id_filename, width=100)
    with col5:
        st.write(summoner_name + ' | Level ' + str(me['summonerLevel']))
        tier = my_ranked_stats['tier'] 
        st.write(tier + ' ' + my_ranked_stats['rank'] + ' | ' + str(my_ranked_stats['leaguePoints']) + ' points') 
        wr = my_ranked_stats['wins']  / my_ranked_stats['losses']
        hot_streak = my_ranked_stats['hotStreak']
        fresh_blood = my_ranked_stats['freshBlood'] 
        st.write('Hot Streak: ' + str(hot_streak) + ' | ' + 'Fresh Blood: ' + str(fresh_blood))
        st.write('Win Rate: ' + str(round(100 * wr, 2)) + '% ('  + str(my_ranked_stats['wins']) + ' wins ; ' + str(my_ranked_stats['losses'])  + ' losses)')

    # Load model with params: Tier, Region
    model_endpoint = get_model_endpoint(region, tier)
    if model_endpoint ==404 and st.button('Pull 1000 matches'):
        path = pull_historical_frames(region=region.upper(), tier=tier, number_matches = 10)
    if st.button('Process raw data'):
        build(path='raw_data/NA1/SILVER/I')
    
    # my_matches = watcher.match.matchlist_by_puuid(region=region, puuid=me['puuid'])
    # match_id = st.selectbox('Pick a match', my_matches)
    # match_detail = watcher.match.by_id(region=region, match_id=match_id)
    # st.code(match_detail)
    