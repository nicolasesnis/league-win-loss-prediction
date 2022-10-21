import streamlit as st 
import json
from riotwatcher import LolWatcher, ApiError
import pandas as pd
import datetime
from src.get_live_data import listen_to_game

st.set_page_config(layout='wide', initial_sidebar_state='collapsed')


listen_to_game()


st.title('League of Legends Win / Loss Prediction tool')
col1, col2, col3, col4, col5 = st.columns([2,2,2,1,2])
with col1:
    summoner_name = st.text_input('Enter Your Summoner Name', value='joyeux2cocotier')
with col2:
    my_region = st.selectbox('Region', ['na1'])

watcher = LolWatcher(st.secrets['riot_api_key'])
versions = watcher.data_dragon.versions_for_region(my_region)

icons=  watcher.data_dragon.profile_icons(version=versions['n']['profileicon'])

if summoner_name != '':
    me = watcher.summoner.by_name(my_region, summoner_name)
    my_ranked_stats = watcher.league.by_summoner(my_region, me['id'])
    
    with col4:
        icon_id_filename = icons['data'][str(me['profileIconId'])]['image']['full']
        st.image('http://ddragon.leagueoflegends.com/cdn/' + versions['n']['profileicon'] + '/img/profileicon/' + icon_id_filename, width=75)
    with col5:
        st.write(summoner_name)
        st.write('Level ' + str(me['summonerLevel']))
        st.write(my_ranked_stats[0]['tier'] + ' ' + my_ranked_stats[0]['rank']) 

    
    
    
    try:
        current_match = watcher.spectator.by_summoner(region=my_region, encrypted_summoner_id=me['id'])
        st.write(current_match)
        match_id = current_match['platformId'] + '_' + str(current_match['gameId'])
        st.write('Current Match: ' + match_id)
        start_time = datetime.datetime.fromtimestamp(current_match['gameStartTime'] / 1000).replace(microsecond=0)
        game_length = datetime.timedelta(seconds=current_match['gameLength'])
        st.write('Match started at ' + str(start_time) + ' - Time in game so far: ' + str(game_length))
        st.write('Match ID: ' +match_id)
    except ApiError as err:
        if '404' in str(err):
            st.warning('No current game for this summoner. Pulling last game data.')
            my_matches = watcher.match.matchlist_by_puuid(region=my_region, puuid=me['puuid'])
            match_id = my_matches[0]
            st.write('Last Match')
    my_matches = watcher.match.matchlist_by_puuid(region=my_region, puuid=me['puuid'])
    match_id = my_matches[0]
    st.write(my_matches)
    match_detail = watcher.match.by_id(region=my_region, match_id=match_id)
    df = pd.DataFrame(match_detail['info']['participants'])
    
    
    df = pd.concat([df.drop(['challenges'], axis=1), df['challenges'].apply(pd.Series).drop(['killingSprees','turretTakedowns' ], axis=1)], axis=1)
    
    # Columns Explanation
    c_dict_path = 'columns.json'
    with open(c_dict_path, 'r') as f:
        c_dict = json.load(f)
    for c in df.columns:
        if c not in c_dict.keys():
            c_dict[c] = {'description': '', 'type': str(df[c].dtype)}
    col = st.selectbox('Features info.', c_dict.keys())
    st.code(c_dict[col])
    st.code(df[['championName', col]])
    
    
    st.dataframe(df)
    
#     col1, col2 = st.columns(2)
#     with col1:
        
#         st.write(participants[0:4])
#     with col2:
#         st.write(participants[5:9])
    
    
#     st.dataframe(df)
    
    
    




# # # Lets get some champions
# # current_champ_list = watcher.data_dragon.champions(champions_version)
# # st.write(current_champ_list)





