from distutils.command.upload import upload
from multiprocessing.sharedctypes import Value
import json
from src.s3 import list_bucket, read_s3_json_file, upload_df_to_s3
import pandas as pd 
import streamlit as st

# 100 = blue side

def compute_blue_lead(teams_dict):
    blue_lead_dict = {}
    for team_color, team_stats in teams_dict.items():
        for stat_obj_name, stat_obj_value in team_stats.items():
            if type(stat_obj_value) == dict: # individual positions  (jg, mid, bot, etc)
                for stat_name, stat_value in stat_obj_value.items():
                    if stat_name not in blue_lead_dict.keys():
                        blue_lead_dict[stat_name] = 0
                    if stat_obj_name + '_' + stat_name not in blue_lead_dict.keys():
                        blue_lead_dict[stat_obj_name + '_' + stat_name] = 0
                    if team_color == 'blue':
                        blue_lead_dict[stat_name] += stat_value
                        blue_lead_dict[stat_obj_name + '_' + stat_name] += stat_value
                    else:
                        blue_lead_dict[stat_name] -= stat_value
                        blue_lead_dict[stat_obj_name + '_' + stat_name] -= stat_value
            else: # team stats only
                if stat_obj_name not in blue_lead_dict.keys():
                    blue_lead_dict[stat_obj_name] = 0
                if team_color == 'blue':
                    blue_lead_dict[stat_obj_name] += stat_obj_value
                else:
                    blue_lead_dict[stat_obj_name] -= stat_obj_value
    return {key: value for key, value in sorted(blue_lead_dict.items())}
            
    
def process_participant_frames(participantFrames, team_individual_position_mapping):
    # First we process all the frames: for each individual position (jg, mid, etc), we compute the blue advantage on all available stats and store it into a dict called "blue_lead_dict"
    # In addition to the indiviual advantages, we also compute a team advantage because League is a team game
    frame_data_dict = {'blue': {}, 'red': {}}
    # First we flatten the raw dict into a simpler dict that will look like:
    # {
    #     'blue':
    #       top' : {
    #         'armor': 10,
    #         ...
    #         }
    #     }
    # }
    for index, participantFrame in participantFrames.items():
        individual_position = team_individual_position_mapping[str(int(index) - 1)]['individualPosition']
        team_color = 'blue' if int(index) <= 5 else 'red'
        frame_data_dict[team_color][individual_position] = {}
        for stat_categorie, stat_value in participantFrame.items():
            # Avalailable stats: championStats, currentGold, damageStats, goldPerSecond, jungleMinionsKilled, level, minionsKilled, timeEnemySpentControlled, totalGold, xp
            if stat_categorie in ['championStats', 'damageStats']: # dict type: 
                for key, value in stat_value.items():    
                    frame_data_dict[team_color][individual_position][key] = value
            elif stat_categorie not in ['position', 'participantId', 'currentGold']: # ignore this one
                frame_data_dict[team_color][individual_position][stat_categorie] = stat_value
    
    # Then we compute all the differences between blue and red teams, for each stat, at role and team levels
    sorted_blue_lead_dict = compute_blue_lead(frame_data_dict)
    return sorted_blue_lead_dict
    


def process_new_events_frames(events):
    # Quick function to keep it DRY
    def increment_dict(d, team_color, key, value=1):
        if key not in d[team_color].keys():
            d[team_color][key] = 0
        d[team_color][key] += value
        return d
        
    # Same as for stats, we flatten the events dict into a simpler dict distributing the events at team level
    events_data_dict = {'blue': {}, 'red': {}}
    for event in events:
        if 'wardType' in event and event['wardType'] == 'UNDEFINED': # ???
            continue
        if 'killerTeamId' in event and event['killerTeamId'] == 300: # when nashor kills herald
            continue
        if event['type'] == 'CHAMPION_KILL' and event['killerId'] == 0: # neutral minion executed
            continue
        if 'teamId' in event:
            team_color = 'blue' if event['teamId'] == 100 else 'red'
        elif 'killerTeamId' in event:
            team_color = 'blue' if event['killerTeamId'] == 100 else 'red'
        else:
            for id_type in ['killerId', 'creatorId', 'participantId']: # the identifier changes depending on the event type
                if id_type in event.keys():
                    if event[id_type] == 0:
                        raise ValueError(event)
                    team_color = 'blue' if int(event[id_type]) <= 5 else 'red'            
        if event['type'] in ['WARD_PLACED', 'WARD_KILL']:
            events_data_dict = increment_dict(events_data_dict, team_color, event['wardType'] + '_' + event['type'])
        for bt_type in ['shutdownBounty', 'bounty']:
            if bt_type in event.keys():
                events_data_dict = increment_dict(events_data_dict, team_color, bt_type.upper() + '_' + event['type'], event[bt_type]) 
        if event['type'] == 'CHAMPION_SPECIAL_KILL':
            events_data_dict = increment_dict(events_data_dict, team_color, event['killType'])
        if event['type'] == 'TURRET_PLATE_DESTROYED':
            events_data_dict = increment_dict(events_data_dict, team_color, event['laneType'] + '_TURRET_PLATE_DESTROYED')
        if event['type'] == 'ELITE_MONSTER_KILL':
            events_data_dict = increment_dict(events_data_dict, team_color, event['monsterType'])
        if event['type'] == 'BUILDING_KILL':
            if 'towerType' in event.keys():
                events_data_dict = increment_dict(events_data_dict, team_color, '_'.join([event['type'], event['towerType'], event['buildingType'], event['laneType']]))
            else: # inhibitor
                events_data_dict = increment_dict(events_data_dict, team_color, '_'.join([event['type'], event['buildingType'], event['laneType']]))
        if event['type'] == 'CHAMPION_KILL' and 'victimId' in event:
            events_data_dict = increment_dict(events_data_dict, 'blue' if team_color == 'red' else 'red', 'DEATHS')
        if event['type'] in ['DRAGON_SOUL_GIVEN', 'OBJECTIVE_BOUNTY_FINISH', 'CHAMPION_KILL']:
            events_data_dict = increment_dict(events_data_dict, team_color, event['type'])
        if 'assistingParticipantIds' in event.keys(): # CHAMPION_KILL, ELITE_MONSTER_KILL
            for id in event['assistingParticipantIds']:
                events_data_dict = increment_dict(events_data_dict, team_color, 'ASSIST_' +  event['type']) 
        if event['type'] == 'GAME_END':
            events_data_dict = increment_dict(events_data_dict, 'blue' if event['winningTeam'] == 100 else 'red', 'blue_team_wins') 
    sorted_blue_lead_dict = compute_blue_lead(events_data_dict)
    return sorted_blue_lead_dict


def process_frame_events(events, prev_blue_events_lead):
    new_blue_events_lead = process_new_events_frames(events)
    if prev_blue_events_lead:
        for key, value in prev_blue_events_lead.items():
            if key not in new_blue_events_lead.keys():
                new_blue_events_lead[key] = value
            else:
                new_blue_events_lead[key] += value
    return new_blue_events_lead
    
    
def get_summoners_perf(participants_ids, team_individual_position_mapping, s3_path, game_start_time):
    out = {'blue': {}, 'red': {}}
    for i, participant_id in enumerate(participants_ids):
        championId = team_individual_position_mapping[str(i)]['championId']
        individualPosition = team_individual_position_mapping[str(i)]['individualPosition']
        teamColor= 'blue' if i < 5 else 'red'
        out[teamColor][individualPosition] = {}
        mastery = read_s3_json_file(s3_path + '/raw_summoner_champion_mastery_data/' + participant_id + '.json')
        if mastery != 404:
            mastery = [m for m in mastery if m['championId'] == championId]
            if len(mastery) != 0:
                out[teamColor][individualPosition]['playerChampionLevel'] = mastery[0]['championLevel']
                out[teamColor][individualPosition]['playerChampionPoints'] = mastery[0]['championPoints']
                # out[teamColor][individualPosition]['playerDaysSinceLastPlayChamp'] = (pd.to_datetime(game_start_time, unit='ms') - pd.to_datetime(mastery[0]['lastPlayTime'], unit='ms')).days
                out[teamColor][individualPosition]['playerChampionChestGranted'] = mastery[0]['chestGranted']
        perf = read_s3_json_file(s3_path + '/raw_summoner_ranked_data/' + participant_id + '.json')
        if perf != 404:
            perf = [p for p in perf if p['queueType'] == 'RANKED_SOLO_5x5']
            if len(perf) != 0:
                out[teamColor][individualPosition]['playerWinRate'] = round(perf[0]['wins'] / perf[0]['losses'], 2) if   perf[0]['losses'] > 0 else 1
                out[teamColor][individualPosition]['playerIsVeteran'] = perf[0]['veteran'] 
                out[teamColor][individualPosition]['playerIsInactive'] = perf[0]['inactive'] 
                out[teamColor][individualPosition]['playerIsFreshBlood'] = perf[0]['freshBlood'] 
                out[teamColor][individualPosition]['playerIsHotStreak'] = perf[0]['hotStreak'] 

    sorted_blue_summoners_lead = compute_blue_lead(out)
    return sorted_blue_summoners_lead


def build_match_data(match_id_fname, s3_path):
    team_individual_position_mapping = read_s3_json_file(s3_path + '/raw_match_context/' + match_id_fname)
    all_roles = [value['individualPosition'] for key, value in team_individual_position_mapping.items()]
    if 'Invalid' in all_roles:
        st.warning('Invalid match, please pick another match')
        return pd.DataFrame()
    
    frames = read_s3_json_file(s3_path + '/raw_match_frames/' + match_id_fname)
    
    blue_events_lead = None
    all_blue_leads = {}
    for i, frame in enumerate(frames['info']['frames']):
        if i == 0: # game start
            game_start_time = frame['events'][0]['realTimestamp']
            blue_summoners_lead = get_summoners_perf(participants_ids=frames['metadata']['participants'], 
                                            team_individual_position_mapping=team_individual_position_mapping,
                                            s3_path=s3_path,
                                            game_start_time=game_start_time)
        # convert ts to minute
        all_blue_leads[int(round(frame['timestamp']/1000/60, 0))] = {
            'blue_stats_lead': process_participant_frames(frame['participantFrames'], team_individual_position_mapping),
            'blue_events_lead': process_frame_events(frame['events'], blue_events_lead),
            'blue_summoners_lead': blue_summoners_lead
        }
    df = pd.DataFrame()
    for minute, dicts in all_blue_leads.items():
        row = pd.DataFrame()
        for d_name, d_value in dicts.items():
            row = pd.concat([row, pd.DataFrame([list(d_value.values())], columns = list(d_value.keys()))], axis=1)
        row['minute'] = minute
        df = pd.concat([df, row])
    df['blue_team_wins'] = df[df['blue_team_wins'].notna()]['blue_team_wins'].unique()[0]
    
    # Keep track of all existing columns
    with open("all_columns.txt", "r") as f:
        all_columns = f.read().split('\n')
    for col in df.columns:
        if col not in all_columns:
            all_columns.append(col)
    for col in all_columns:
        if col not in df.columns:
            df[col] = None
    all_columns = sorted(all_columns)
    with open("all_columns.txt", "w") as outfile:
        outfile.write("\n".join(all_columns))
        
    df = df[all_columns]
    
    
    return df
                
                
def build_training_dataset(s3_path, dataset_name):
    # Path is like raw_data/NA1/SILVER/I
    match_id_fnames = list_bucket(s3_path  + '/raw_match_frames', return_filenames_only=True)
    for i, match_id_fname in enumerate(match_id_fnames):
        try:
            df = build_match_data(match_id_fname, s3_path)
            df.to_csv('raw_data/' + dataset_name, index=None, mode='w' if i == 0 else 'a', header = True if i == 0 else False)
        except Exception as e:
            st.warning(e)
    return 200
    # upload_df_to_s3(df, 's3://league-pred-tool/input/' + dataset_name)
        
            
            
            
  
        
# TBD:
# add timestamp to each frame
# concat events data overtime
# add summoner related data