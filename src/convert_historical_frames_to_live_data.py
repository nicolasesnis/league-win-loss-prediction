import os
import pandas as pd
import json
import streamlit as st

# builds liveclient-affine data object.
def build_final_object_liveclient(match, game_events_path):
    
    game_events = pd.read_csv(game_events_path)
    all_frames = []
    # Determine winner
    if len(match['metadata']['participants']) != 10: # Ignore invalid games (less than 10 participants) (???)
        return None
    frames = match['info']['frames']
    if len([f for f in frames if f['participantFrames']]) == 0: # Ignore frames without participantFrames data (early ff?)
        return None
	
    last_frame = frames[-1]
    last_event = last_frame['events'][-1]
    assert last_event['type'] == 'GAME_END'
    winner = last_event['winningTeam']
    
    mapping = {
		'abilityPower': 'abilityPower',
		'armor': 'armor',
		# 'armorPenetrationFlat': 'armorPen', # all Os
		# 'armorPenetrationPercent':'armorPenPercent', # all Os
		'attackDamage':'attackDamage',
		'attackSpeed':'attackSpeed',
		# 'bonusArmorPenetrationPercent':'bonusArmorPenPercent',
		# 'bonusMagicPenetrationPercent':'bonusMagicPenPercent', # all Os
		# 'cooldownReduction':'cooldownReduction', # all Os
		'currentHealth':'health',
		'maxHealth': 'healthMax',
		'healthRegenRate': 'healthRegen',
		'lifesteal':'lifesteal',
		'magicPenetrationFlat': 'magicPen',
		'magicPenetrationPercent': 'magicPenPercent',
		'magicResist':'magicResist',
		'moveSpeed':'movementSpeed',
		'resourceValue': 'power',
		'resourceMax':'powerMax',
		'resourceRegenRate':  'powerRegen',
		'spellVamp':'spellVamp',
        'SKILL_LEVEL_UP':'SKILL_LEVEL_UP',
        'ITEM_PURCHASED': 'ITEM_PURCHASED',
        'WARD_PLACED': 'WARD_PLACED',
        'YELLOW_TRINKET_PLACED': 'YELLOW_TRINKET_PLACED',
        'CONTROL_WARD_PLACED': 'CONTROL_WARD_PLACED',
        'CHAMPION_KILL': 'CHAMPION_KILL',
        'KILL_ASSIST': 'KILL_ASSIST',
        'BOUNTY':'BOUNTY',
        'SHUTDOWN_BOUNTY': 'SHUTDOWN_BOUNTY',
        'DEATH': 'DEATH',
        'KILL_FIRST_BLOOD': 'KILL_FIRST_BLOOD',
        'ITEM_DESTROYED': 'ITEM_DESTROYED',
        'LEVEL': 'LEVEL',
        'WARD_KILL': 'WARD_KILL',
        'YELLOW_TRINKET_DESTROYED': 'YELLOW_TRINKET_DESTROYED',
        'CONTROL_WARD_DESTROYED': 'CONTROL_WARD_DESTROYED',
        'ITEM_SOLD': 'ITEM_SOLD',
        'MID_TURRET_PLATE_DESTROYED': 'MID_TURRET_PLATE_DESTROYED',
        'TOP_TURRET_PLATE_DESTROYED': 'TOP_TURRET_PLATE_DESTROYED',
        'BOT_TURRET_PLATE_DESTROYED': 'BOT_TURRET_PLATE_DESTROYED',
        'DRAGON_KILL': 'DRAGON_KILL',
        'ASSIST_DRAGON_KILL': 'ASSIST_DRAGON_KILL',
        'BOUNTY_DRAGON' : 'BOUNTY_DRAGON',
        'RIFTHERALD_KILL': 'RIFTHERALD_KILL',
        'ASSIST_RIFTHERALD_KILL': 'ASSIST_RIFTHERALD_KILL',
        'BOUNTY_RIFTHERALD' : 'BOUNTY_RIFTHERALD',
        'BARON_NASHOR_KILL': 'BARON_NASHOR_KILL',
        'ASSIST_BARON_NASHOR_KILL': 'ASSIST_BARON_NASHOR_KILL',
        'BOUNTY_BARON_NASHOR' : 'BOUNTY_BARON_NASHOR',
        'OUTER_TURRET_MID_LANE_TOWER_BUILDING_KILL':'OUTER_TURRET_MID_LANE_TOWER_BUILDING_KILL',
        'INNER_TURRET_MID_LANE_TOWER_BUILDING_KILL':'INNER_TURRET_MID_LANE_TOWER_BUILDING_KILL',
        'BASE_TURRET_MID_LANE_TOWER_BUILDING_KILL':'BASE_TURRET_MID_LANE_TOWER_BUILDING_KILL',
        'NEXUS_TURRET_MID_LANE_TOWER_BUILDING_KILL':'NEXUS_TURRET_MID_LANE_TOWER_BUILDING_KILL',
        'MID_LANE_INHIBITOR_BUILDING_KILL':'MID_LANE_INHIBITOR_BUILDING_KILL',
        'OUTER_TURRET_BOT_LANE_TOWER_BUILDING_KILL':'OUTER_TURRET_BOT_LANE_TOWER_BUILDING_KILL',
        'INNER_TURRET_BOT_LANE_TOWER_BUILDING_KILL':'INNER_TURRET_BOT_LANE_TOWER_BUILDING_KILL',
        'BASE_TURRET_BOT_LANE_TOWER_BUILDING_KILL':'BASE_TURRET_BOT_LANE_TOWER_BUILDING_KILL',
        # 'NEXUS_TURRET_BOT_LANE_TOWER_BUILDING_KILL':'NEXUS_TURRET_BOT_LANE_TOWER_BUILDING_KILL',
        'BOT_LANE_INHIBITOR_BUILDING_KILL':'BOT_LANE_INHIBITOR_BUILDING_KILL',
        'OUTER_TURRET_TOP_LANE_TOWER_BUILDING_KILL':'OUTER_TURRET_TOP_LANE_TOWER_BUILDING_KILL',
        'INNER_TURRET_TOP_LANE_TOWER_BUILDING_KILL':'INNER_TURRET_TOP_LANE_TOWER_BUILDING_KILL',
        'BASE_TURRET_TOP_LANE_TOWER_BUILDING_KILL':'BASE_TURRET_TOP_LANE_TOWER_BUILDING_KILL',
        # 'NEXUS_TURRET_TOP_LANE_TOWER_BUILDING_KILL':'NEXUS_TURRET_TOP_LANE_TOWER_BUILDING_KILL',
        'TOP_LANE_INHIBITOR_BUILDING_KILL':'TOP_LANE_INHIBITOR_BUILDING_KILL',
        'DRAGON_SOUL_GIVEN': 'DRAGON_SOUL_GIVEN',
        'CHAMPION_TRANSFORM': 'CHAMPION_TRANSFORM',
        'OBJECTIVE_BOUNTY_FINISH': 'OBJECTIVE_BOUNTY_FINISH',
        'KILL_MULTI_LENGTH': 'KILL_MULTI_LENGTH',
        'KILL_MULTI':'KILL_MULTI',
        'KILL_ACE': 'KILL_ACE'
	}
    
    for x in frames:
        for event in x['events']: # Classify all event types        
            if event['type'] not in game_events.event_type.unique() and event['type'] not in ['PAUSE_END', 'GAME_END']:
                for useless_key in ['realTimestamp', 'timestamp', 'position', 'victimDamageReceived', 'victimDamageDealt']:
                    if useless_key in event.keys():
                        del event[useless_key]
                game_events = pd.concat([game_events, pd.DataFrame([[event['type'], event]], columns=['event_type', 'keys'])])
                game_events.to_csv(game_events_path, index=None)
            
            # Feature engineering from events data
            if event['type'] == 'SKILL_LEVEL_UP':
                x['participantFrames'][str(event['participantId'])]['championStats']['SKILL_LEVEL_UP'] = 1
            elif event['type'] == 'ITEM_PURCHASED':
                x['participantFrames'][str(event['participantId'])]['championStats']['ITEM_PURCHASED'] = 1
            elif event['type'] == 'WARD_PLACED':
                if event['creatorId'] != 0:  # ???
                    x['participantFrames'][str(event['creatorId'])]['championStats']['WARD_PLACED'] = 1
                if event['wardType'] == 'YELLOW_TRINKET':
                    x['participantFrames'][str(event['creatorId'])]['championStats']['YELLOW_TRINKET_PLACED'] = 1
                elif event['wardType'] == 'CONTROL_WARD':
                    x['participantFrames'][str(event['creatorId'])]['championStats']['CONTROL_WARD_PLACED'] = 1
            elif event['type']  == 'CHAMPION_KILL':
                if event['killerId'] != 0: # bots destroying a tower?
                    x['participantFrames'][str(event['killerId'])]['championStats']['CHAMPION_KILL'] = 1
                if 'victimId' in event:
                    x['participantFrames'][str(event['victimId'])]['championStats']['DEATH'] = 1
                if 'bounty' in event:
                    if event['killerId'] != 0: # ???
                        x['participantFrames'][str(event['killerId'])]['championStats']['BOUNTY'] = event['bounty']
                if 'shutdownBounty' in event:
                    if event['killerId'] != 0: # ???
                        x['participantFrames'][str(event['killerId'])]['championStats']['SHUTDOWN_BOUNTY'] = event['shutdownBounty']
                if 'assistingParticipantIds' in event: 
                    for pid in event['assistingParticipantIds']:
                        x['participantFrames'][str(pid)]['championStats']['KILL_ASSIST'] = 1
            if event['type'] == 'CHAMPION_SPECIAL_KILL':
                if event['killType'] == 'KILL_FIRST_BLOOD':
                    x['participantFrames'][str(event['killerId'])]['championStats']['KILL_FIRST_BLOOD'] = 1
                elif event['killType'] == 'KILL_MULTI':
                    x['participantFrames'][str(event['killerId'])]['championStats']['KILL_MULTI'] = 1
                    x['participantFrames'][str(event['killerId'])]['championStats']['KILL_MULTI_LENGTH'] = event['multiKillLength']
                elif event['killType'] == 'KILL_ACE':
                    x['participantFrames'][str(event['killerId'])]['championStats']['KILL_ACE'] = 1
                    
                else: 
                    st.write(event)
            if event['type'] == 'ITEM_DESTROYED':
                x['participantFrames'][str(event['participantId'])]['championStats']['ITEM_DESTROYED'] = 1
            if event['type'] == 'LEVEL_UP':
                x['participantFrames'][str(event['participantId'])]['championStats']['LEVEL'] = event['level']
            if event['type'] == 'WARD_KILL':
                x['participantFrames'][str(event['killerId'])]['championStats']['WARD_KILL'] = 1
                if event['wardType'] == 'YELLOW_TRINKET':
                    x['participantFrames'][str(event['killerId'])]['championStats']['YELLOW_TRINKET_DESTROYED'] = 1
                elif event['wardType'] == 'CONTROL_WARD':
                    x['participantFrames'][str(event['killerId'])]['championStats']['CONTROL_WARD_DESTROYED'] = 1
            if event['type'] == 'ITEM_SOLD':
                x['participantFrames'][str(event['participantId'])]['championStats']['ITEM_SOLD'] = 1
            if event['type'] == 'TURRET_PLATE_DESTROYED':
                if event['killerId'] != 0: # minions
                    lane =event['laneType']
                    x['participantFrames'][str(event['killerId'])]['championStats'][lane.replace('_LANE', '') + '_TURRET_PLATE_DESTROYED'] = 1

            if event['type'] == 'ELITE_MONSTER_KILL':
                mt = event['monsterType']
                if event['killerId'] != 0: # ??? Probably when nashor kills herald
                    x['participantFrames'][str(event['killerId'])]['championStats'][mt + '_KILL'] = 1
                
                if 'assistingParticipantIds' in event: 
                    for pid in event['assistingParticipantIds']:
                        x['participantFrames'][str(pid)]['championStats']['ASSIST_' + mt + '_KILL'] = 1
                if 'bounty' in event:
                    if event['killerId'] != 0: # ???:
                        x['participantFrames'][str(event['killerId'])]['championStats']['BOUNTY_' + mt] = 1
            if event['type'] == 'BUILDING_KILL':
                # Assign building kill to whole team - regardless who did it -- can be improved yes
                bt = event['buildingType']
                lane = event['laneType']
                if 'towerType' in event: 
                    tt = event['towerType']
                    to_join = [tt, lane, bt]
                else: # inhibitor
                    to_join = [lane, bt]
                if event['teamId'] == 100:
                    for i in [1,2,3,4,5]:
                        x['participantFrames'][str(i)]['championStats']['_'.join(to_join) + '_KILL'] = 1
                else:
                    for i in [6,7,8,9,10]:
                        x['participantFrames'][str(i)]['championStats']['_'.join(to_join) + '_KILL'] = 1
            if event['type'] == 'DRAGON_SOUL_GIVEN':
                if event['teamId'] == 100:
                    for i in [1,2,3,4,5]:
                        x['participantFrames'][str(i)]['championStats']['DRAGON_SOUL_GIVEN'] = 1
                else:
                    for i in [6,7,8,9,10]:
                        x['participantFrames'][str(i)]['championStats']['DRAGON_SOUL_GIVEN'] = 1
            if event['type'] == 'CHAMPION_TRANSFORM':
                x['participantFrames'][str(event['participantId'])]['championStats']['CHAMPION_TRANSFORM'] = 1
            if event['type'] == 'OBJECTIVE_BOUNTY_FINISH':
                if event['teamId'] == 100:
                    for i in [1,2,3,4,5]:
                        x['participantFrames'][str(i)]['championStats']['OBJECTIVE_BOUNTY_FINISH'] = 1
                else:
                    for i in [6,7,8,9,10]:
                        x['participantFrames'][str(i)]['championStats']['OBJECTIVE_BOUNTY_FINISH'] = 1
                
        for y in range(1, 11): # 1 frame per all of the 10 players
            frame = {
                "matchId": match['metadata']['matchId'],
				"timestamp": int(round(x['timestamp']/1000/60, 0)),
                "playerPosition": int(y)
			}
            for live_key, frame_value in mapping.items():
                if frame_value in x['participantFrames'][str(y)]['championStats']:
                    frame[live_key] = x['participantFrames'][str(y)]['championStats'][frame_value]
                else:
                    frame[live_key] = 0
            if y in [1,2,3,4,5]:
                frame['winner'] = 1 if winner == 100 else 0
                frame['teamColor'] = 'red'    
            else:
                frame['winner'] = 1 if winner == 200 else 0
                frame['teamColor'] = 'blue'
            all_frames.append(frame)
            del frame
    return all_frames

# CLASSIFIER MODEL (LIVE CLIENT API AFFINITY DATA)
def process_predictor_liveclient(path, number_matches=999999):
    # my_bar = st.progress(0)
    timeframes = os.listdir(path+ '/raw_frames')
    for i, timeframe in enumerate(timeframes):
        if i > number_matches:
            return
        with open(path + '/raw_frames/' + timeframe, 'r') as f:
            content = json.load(f)
        # build data similar to the one given by the Live Client API from Riot.		
        processed_frames = build_final_object_liveclient(content, game_events_path = path + '/game_events.csv')
        if processed_frames:
            pd.DataFrame(processed_frames).to_csv(path + '/processed_frames/' + timeframe.replace('json', 'csv'), index=None)
        # my_bar.progress(i)