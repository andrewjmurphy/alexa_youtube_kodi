#!/usr/bin/python

from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.tools import argparser
import os
import json
import requests


# Set DEVELOPER_KEY to the API key value from the APIs & auth > Registered apps
# tab of
#   https://cloud.google.com/console
# Please ensure that you have enabled the YouTube Data API for your project.

DEVELOPER_KEY = os.getenv('DEV_KEY')
if not DEVELOPER_KEY or DEVELOPER_KEY == 'None':
  DEVELOPER_KEY = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
APPLICATION_ID = os.getenv('APP_ID')
if not APPLICATION_ID or APPLICATION_ID == 'None':
  APPLICATION_ID = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

def lambda_handler(event, context):
    if (event["session"]["application"]["applicationId"] !=
            APPLICATION_ID):
        raise ValueError("Invalid Application ID")
    if event["session"]["new"]:
        on_session_started({"requestId": event["request"]["requestId"]}, event["session"])
    if event["request"]["type"] == "IntentRequest":
        return on_intent(event["request"], event["session"])
        
def on_session_started(session_started_request, session):
    print "Starting new session."
    
    
def on_intent(intent_request, session):
    intent = intent_request["intent"]
    intent_name = intent_request["intent"]["name"]

    if intent_name == "PlayVideo":
        return playvideo(intent)
    else:
        raise ValueError("Invalid intent")
        
def playvideo(intent):
    search_string = intent['slots']['searchstring']['value']
    title = search_and_play(search_string)
    session_attributes = {}
    card_title = "NO"
    speech_output = title
    reprompt_text = ""
    should_end_session = True
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))
        
def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        "outputSpeech": {
            "type": "PlainText",
            "text": output
        },
        "card": {
            "type": "Simple",
            "title": title,
            "content": output
        },
        "reprompt": {
            "outputSpeech": {
                "type": "PlainText",
                "text": reprompt_text
            }
        },
        "shouldEndSession": should_end_session
    }

def build_response(session_attributes, speechlet_response):
    return {
        "version": "1.0",
        "sessionAttributes": session_attributes,
        "response": speechlet_response
    }

def search_and_play(searchstring):
  youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
    developerKey=DEVELOPER_KEY)

  # Call the search.list method to retrieve results matching the specified
  # query term.
  search_response = youtube.search().list(
    q=searchstring,
    part="id,snippet",
    maxResults=1,
    type="video"
  ).execute()

  videos = []
  videoid=""
  title=""

  # Add each result to the appropriate list, and then display the lists of
  # matching videos, channels, and playlists.
  for search_result in search_response.get("items", []):
    if search_result["id"]["kind"] == "youtube#video":
      videoid=search_result["id"]["videoId"]
      title=search_result["snippet"]["title"]
      videos.append("%s (%s)" % (search_result["snippet"]["title"],
                                 search_result["id"]["videoId"]))

  kodiresponse = sendvideo(videoid)
  print kodiresponse
  return title


def sendvideo(title):

  KODI = os.getenv('KODI_ADDRESS')
  if not KODI or KODI == 'None':
    KODI = '127.0.0.1'
  PORT = os.getenv('KODI_PORT')
  if not PORT or PORT == 'None':
    PORT = '8080'
  AUTH = os.getenv('KODI_AUTH')
  if not AUTH or AUTH == 'None':
    AUTH = 'kodi'

  url = 'http://%s:%s/jsonrpc' % (KODI, PORT)
  headers = {'content-type': 'application/json', 'Authorization': AUTH}
  filename = "plugin://plugin.video.youtube/play/?video_id=" + title

  payload = [
    {
      "params": {
        "playlistid": 1
      },
      "method": "Playlist.Clear",
      "id": 890,
      "jsonrpc": "2.0"
    },
    {
      "params": {
        "item": {
          "file": filename
        },
        "playlistid": 1
      },
      "method": "Playlist.Add",
      "id": 28,
      "jsonrpc": "2.0"
    },
    {
      "params": {
        "item": {
          "position": 0,
          "playlistid": 1
        }
      },
      "method": "Player.Open",
      "id": 239,
      "jsonrpc": "2.0"
    }
  ]

  response = json.loads(requests.post(url, data=json.dumps(payload), headers=headers).text)
  return response


if __name__ == "__main__":
  argparser.add_argument("--q", help="Search term", default="Google")
  argparser.add_argument("--max-results", help="Max results", default=25)
  args = argparser.parse_args()

  try:
    title = search_and_play(args.q)
    print title
  except HttpError, e:
    print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
