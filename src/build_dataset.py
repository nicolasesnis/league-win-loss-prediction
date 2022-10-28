from multiprocessing.sharedctypes import Value
from src.s3 import list_bucket, read_s3_json_file
import pandas as pd 
import streamlit as st

# 100 = blue side

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
    blue_lead_dict = {}
    for team_color, team_stats in frame_data_dict.items():
        for individual_position, individual_stats in team_stats.items():
            for stat_name, stat_value in individual_stats.items():
                if stat_name not in blue_lead_dict.keys():
                    blue_lead_dict[stat_name] = 0
                if individual_position + '_' + stat_name not in blue_lead_dict.keys():
                    blue_lead_dict[individual_position + '_' + stat_name] = 0
                if team_color == 'blue':
                    blue_lead_dict[stat_name] += stat_value
                    blue_lead_dict[individual_position + '_' + stat_name] += stat_value
                else:
                    blue_lead_dict[stat_name] -= stat_value
                    blue_lead_dict[individual_position + '_' + stat_name] -= stat_value
    
    sorted_blue_lead_dict = {key: value for key, value in sorted(blue_lead_dict.items())}
    


def process_events_frames(events):
    # Quick function to keep it DRY
    def increment_dict(d, team_color, key, value=1):
        if key not in d[team_color].items():
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
        elif event['type'] in ['DRAGON_SOUL_GIVEN', 'OBJECTIVE_BOUNTY_FINISH']:
            events_data_dict = increment_dict(events_data_dict, team_color, event['type'])
        if 'assistingParticipantIds' in event.keys(): # CHAMPION_KILL, ELITE_MONSTER_KILL
            for id in event['assistingParticipantIds']:
                events_data_dict = increment_dict(events_data_dict, team_color, 'ASSIST_' +  event['type']) 

    blue_events_lead = {} 
    for team_color, team_events in events_data_dict.items():
        for event_name, event_value in team_events.items():
            if event_name not in blue_events_lead.keys():
                blue_events_lead[event_name] = 0
            if team_color == 'blue':
                blue_events_lead[event_name] += event_value
            else:
                blue_events_lead[event_name] -= event_value
    
    sorted_blue_lead_dict = {key: value for key, value in sorted(blue_events_lead.items())}
    return sorted_blue_lead_dict


def process_frame(frame, team_individual_position_mapping):
    blue_stats_lead = process_participant_frames(frame['participantFrames'], team_individual_position_mapping)
    blue_events_lead = process_events_frames(frame['events'])
    st.code(blue_events_lead)
    

def build(path):
    output = pd.DataFrame()
    # Path is like raw_data/NA1/SILVER/I
    match_id_fnames = list_bucket('s3://league-pred-tool/' + path + '/raw_match_frames', return_filenames_only=True)
    for match_id_fname in match_id_fnames:
        team_individual_position_mapping = read_s3_json_file('s3://league-pred-tool/' + path + '/raw_match_context/' + match_id_fname)
        frames = read_s3_json_file('s3://league-pred-tool/' + path + '/raw_match_frames/' + match_id_fname)
        for frame in frames['info']['frames']:
            process_frame(frame, team_individual_position_mapping)
            
  
        
# TBD:
# add timestamp to each frame
# concat events data overtime
# add summoner related data