from riotwatcher import LolWatcher, ApiError
import traceback
import os
import pandas as pd
import streamlit as st
import json
import time
from src.s3 import check_if_s3_key_exists, create_s3_path, upload_df_to_s3, read_s3_df_file, upload_dict_to_s3

watcher = LolWatcher(st.secrets['riot_api_key'])

def get_league_summoners(region, queue, tier, division, pages=1):
    all_entries = []
    for page in range(0, pages):
        entries = watcher.league.entries(region, queue, tier, division, page + 1)
        
        all_entries += entries
        time.sleep(1)
    return all_entries


def pull_historical_frames(region,  tier, s3_path, number_matches=10, division='I', queue='RANKED_SOLO_5x5', match_id=None, summoner_id=None, single_match=False):
    processed_summoners= read_s3_df_file('s3://league-pred-tool/raw_data/processed_summoners.csv')
    
    if not check_if_s3_key_exists(s3_path):
        for folder in ['raw_match_frames', 'raw_match_context', 'raw_summoner_ranked_data', 'raw_summoner_champion_mastery_data']:
            create_s3_path('league-pred-tool', s3_path + '/' + folder)
        
    if not single_match:
        entries = get_league_summoners(region, queue, tier, division, pages=15)
        summoner_ids = [s['summonerId'] for s in entries if s['summonerId'] not in processed_summoners['summonerId'].unique()] 
        summoner_ids = summoner_ids[0:number_matches]
    else:
        summoner_ids = [summoner_id]
    for id in summoner_ids:
        try:
            stop = False
            while not stop:
                
                # Get PUUID per summoner (required to retrieve match list)
                puuid = watcher.summoner.by_id(region, id)['puuid']
                
                # Update processed_summoners
                processed_summoners = pd.concat([processed_summoners, pd.DataFrame([[id, puuid]], columns=['summonerId', 'puuid'])])
                upload_df_to_s3(processed_summoners, 's3://league-pred-tool/raw_data/processed_summoners.csv')
                
                # Match Timeframe Data
                if not single_match:
                    match_ids = watcher.match.matchlist_by_puuid(region=region, puuid=puuid, count=1, queue=420)
                else:
                    match_ids = [match_id]
                for match_id in match_ids:
                    time.sleep(1)
                    
                    # Match context: champions IDs and role only - we don't look at the rest because it's postgame data
                    context = watcher.match.by_id(region, match_id)
                    context = context['info']['participants']
                    
                    context = {i: {'championId': j['championId'], 'individualPosition': j['individualPosition']} for i, j in enumerate(context)}
                    # keep only frames where each team has the 5 roles (jg, bottom, utility, mid, top)
                    for position in ['JUNGLE', 'UTILITY', 'BOTTOM', 'MIDDLE', 'TOP']:
                        if len([key for key, value in context.items() if value['individualPosition'] == position]) != 2:
                            stop = True
                            
                    upload_dict_to_s3(context, s3_path + '/raw_match_context/' + match_id + '.json')
                    timeframe = watcher.match.timeline_by_match(region=region, match_id = match_id)
                    upload_dict_to_s3(timeframe,  s3_path + '/raw_match_frames/' + match_id + '.json')
                
                    for participant_puuid in timeframe['metadata']['participants']:
                        participant_id = watcher.summoner.by_puuid(region, participant_puuid)['id']
                        # Ranked data
                        ranked_stats = watcher.league.by_summoner(region, participant_id)
                        upload_dict_to_s3(ranked_stats, s3_path + '/raw_summoner_ranked_data/' + participant_puuid + '.json')
                        # Mastery data
                        mastery = watcher.champion_mastery.by_summoner(region, participant_id)
                        upload_dict_to_s3(mastery,  s3_path + '/raw_summoner_champion_mastery_data/' + participant_puuid + '.json')
                        if not single_match:
                            time.sleep(2)
                stop = True
        except Exception as e:
            raise ValueError(traceback.format_exc())
            time.sleep(10)
    return s3_path

        
        