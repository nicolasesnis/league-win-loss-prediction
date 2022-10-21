import requests
import datetime
import time
import streamlit as st
import json
# https://github.com/oracle-devrel/leagueoflegends-optimizer/blob/main/articles/article5.md


# We remove useless data like items (which also cause quotation marks issues in JSON deserialization)
def build_object(content):
    for x in content['allPlayers']:
        del x['items'] # delete items to avoid quotation marks
    built_obj = {
        'activePlayer': content['activePlayer'],
        'allPlayers': content['allPlayers']
    }
    content = json.dumps(content)
    content = content.replace("'", "\"") # for security, but most times it's redundant.
    return content # content will be a string due to json.dumps()

def send_message(message):
    with st.empty():
        st.code(message)

def listen_to_game():
    while True:
        try:
            # We access the endpoint we mentioned above in the article
            response = requests.get('https://127.0.0.1:2999/liveclientdata/allgamedata', verify=False)
        except requests.exceptions.ConnectionError:
            # Try again every 5 seconds
            print('{} | Currently not in game'.format(datetime.datetime.now()))
            time.sleep(5)
            continue

        # Send to RabbitMQ queue.
        if response.status_code != 404:
            st.write(123)
            
            # to_send = build_object(content =  response.json())
            # send_message( to_send)
        time.sleep(5) # wait 30 seconds before making another request