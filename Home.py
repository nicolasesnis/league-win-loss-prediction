import streamlit as st 
from st_aggrid.shared import JsCode
from st_aggrid import GridOptionsBuilder, AgGrid

import pandas as pd
import plotly.express as px
from riotwatcher import LolWatcher, ApiError
import numpy as np
from src.sagemaker_util import predict
from src.get_data import pull_historical_frames
from src.build_dataset import build_training_dataset, build_match_data
from src.s3 import list_bucket, check_if_s3_key_exists


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
def get_summoner_info(region, summoner_name):
    me =     watcher.summoner.by_name(region, summoner_name)
    my_ranked_stats = watcher.league.by_summoner(region, me['id'])
    my_ranked_stats = [s for s in my_ranked_stats if s['queueType'] == 'RANKED_SOLO_5x5'][0]
    my_matches = watcher.match.matchlist_by_puuid(region=region, puuid=me['puuid'], queue=420)
    return me, my_ranked_stats, my_matches

if summoner_name != '':
    me, my_ranked_stats, my_matches = get_summoner_info(region, summoner_name)
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

    s3_path = 's3://league-pred-tool/raw_data/' + '/'.join([region, tier, division])
    
    # # Load model with params: Tier, Region
    # if st.button('Pull 1000 matches'):
    #     path = pull_historical_frames(region=region.upper(), tier=tier, division=division, number_matches = 10000)
    # if st.button('Process raw data'):    
    #     build_training_dataset(s3_path, dataset_name=region + '_' + tier + '_' + division + '.csv')


    champions = watcher.data_dragon.champions(version=versions['n']['profileicon'])['data']
    champions = {int(v['key']): {
        'name': v['name'],
        'image': 'http://ddragon.leagueoflegends.com/cdn/' + versions['n']['profileicon'] + '/img/champion/' + v['image']['full']
    } for k, v in champions.items()}
    
    match_id = st.selectbox('Pick a match', my_matches)
    
    if not check_if_s3_key_exists(s3_path + '/raw_match_context/' + match_id + '.json' ):    
        pull_historical_frames(region=region.upper(), tier=tier, division=division, number_matches = 1, summoner_id = me['id'], match_id = match_id, single_match=True, s3_path=s3_path)
        
    df = build_match_data(match_id + '.json', s3_path)
    match_context  = watcher.match.by_id(region, match_id)
    
    start_time = pd.to_datetime(match_context['info']['gameCreation'], unit='ms')
    winner = 'blue' if match_context['info']['teams'][0]['win'] else 'red'
    # st.write(match_context)
    st.write('Game start time: '+ str(start_time))
    st.write('Winning team: ' + winner)
    
    mc = pd.DataFrame(match_context['info']['participants'])
    mc['championImg'] = mc['championId'].apply(lambda x: champions[x]['image'])
    mc['kda'] = mc.apply(lambda x: '/'.join(str(x[i]) for i in ['kills', 'deaths', 'assists']) ,axis=1)
    for item in range(7):
        mc['item' + str(item)] = mc['item' + str(item)].apply(lambda x:'https://ddragon.leagueoflegends.com/cdn/12.21.1/img/item/' + str(x)+ '.png' if x != 0 else '') 
    
    mc = mc[['championImg', 'championName', 'item0', 'item1', 'item2', 'item3', 'item4', 'item5', 'item6', 'kda']]
    blue = mc.iloc[0:5].reset_index(drop=True)
    blue.columns = ['blue_' + c for c in blue.columns]
    red = mc.iloc[5:10].reset_index(drop=True)
    red.columns = ['red_' + c for c in red.columns]
    mc = pd.concat([blue, red], axis=1)
    
    gb = GridOptionsBuilder.from_dataframe(mc)
    
    for team in ['blue', 'red']:
        for col in mc.columns:
            if 'item' in col or 'Img' in col:
                ShowImage = JsCode("""function (params) {
                        var element = document.createElement("span");
                        var imageElement = document.createElement("img");
                    
                        if (params.data.""" + col + """ != '') {
                            imageElement.src = params.data.""" + col + """;
                            imageElement.width="20";
                        } else { imageElement.src = ""; }
                        element.appendChild(imageElement);
                        return element;
                        }""")
                gb.configure_column( col, cellRenderer=ShowImage, width=45)
            else:
                gb.configure_column(col, width=100)
    
    vgo = gb.build()
    AgGrid(mc, 
           gridOptions=vgo, 
           allow_unsafe_jscode=True )
    
    
    model_endpoints = {
        'SILVER': 'silver-endpoint-v7-1',
    }
    # if not tier in model_endpoints.keys():
    #     st.error('No prediction model available for ' + tier)
    
    # @st.cache(allow_output_mutation=True)
    def make_predictions(without_label):
        def pred_row(row):
            input = ','.join([str(i) for i in row])
            pred =  predict(endpoint_name='silver-endpoint-v7-1', input=input)
            blue_win_win_proba =  1 - float(pred.split(',')[1])
            return blue_win_win_proba
        df['blue_win_win_proba'] = without_label.apply(lambda x: pred_row(x), axis=1)
        return df
    without_label = df.fillna(0).drop('blue_team_wins', axis=1)
    df = make_predictions(without_label)
    
    
    predicted_winner = df.loc[df.minute == 15, 'blue_win_win_proba'].values[0]
    predicted_winner = 'blue' if predicted_winner > 0.5 else 'red'
    st.write('Predicted winner at 15mn: ' + predicted_winner)
    
    col = st.selectbox('Pick a column', options=df.columns, index=list(df.columns).index('blue_win_win_proba'))
    
    df["line_color"] = np.where(df[col]<0, 'red', 'blue')
    fig = px.bar(df, x="minute", y=col, barmode='group', color='line_color')
    st.plotly_chart(fig)    

    