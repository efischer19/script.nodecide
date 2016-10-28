"""
Main script for this hacked-together plugin
"""
import json
import os
from random import randint
import xbmc
import xbmcaddon

# Constants and contextual variables
__settings__ = xbmcaddon.Addon(id='script.nodecide')
__cwd__ = __settings__.getAddonInfo('path')
MASTER_INPUT = os.path.join(__cwd__, "resources", "master_ref.data")
TEST_DATA = os.path.join(__cwd__, "resources", "test.data")
CURRENT_DATA = os.path.join(__cwd__, "resources", "current.data")

IDEAL_QUEUE_LENGTH = 6  # Double Netflix idle time

def execute_log_command(cmd):
    """
    Helper for executing commands, with logging if debug mode on.
    """
    raw_req = json.dumps(cmd)
    xbmc.log("JSONRPC request: {}".format(raw_req), xbmc.LOGDEBUG)

    raw_resp = xbmc.executeJSONRPC(raw_req)
    xbmc.log("JSONRPC result: {}".format(raw_resp), xbmc.LOGDEBUG)

    return json.loads(raw_resp)

def current_playlist():
    """
    Gets the current video playlist.
    """
    current_playlists_cmd = {
        "jsonrpc": "2.0",
        "method": "Playlist.GetPlaylists",
        "id": "getCurrentPlaylists"
    }
    playlists_result = execute_log_command(current_playlists_cmd)
    current = next(
        (playlist for playlist in playlists_result["result"] if playlist["type"] == "video"),
        None
    )
    if current:
        playlist_contents_cmd = {
            "jsonrpc": "2.0",
            "method": "Playlist.GetItems",
            "id": "getPlaylistItems",
            "params": {
                "playlistid": current["playlistid"],
            }
        }
        current_playlist_contents = execute_log_command(playlist_contents_cmd)
        return {
            "id": current["playlistid"],
            "items": current_playlist_contents["result"].get("items", [])
        }
    return None

def active_video_player():
    """
    Returns the playerid of the currently active video player, or None.
    """
    current_players_cmd = {
        "jsonrpc": "2.0",
        "method": "Player.GetActivePlayers",
        "id": "getCurrentPlayers"
    }
    players_result = execute_log_command(current_players_cmd)
    player = next(
        (player for player in players_result["result"] if player["type"] == "video"),
        None
    )
    if player is not None:
        return player["playerid"]
    return None

def first_run():
    """
    Since m3u files save file paths and this script works best with episodeids,
    we need to convert them. The hacky way to do this is "queue everything, then
    ask for the current playlist"
    """
    with open(MASTER_INPUT, "r") as infile:
        seed = infile.readline()
        play_cmd = {
            "jsonrpc": "2.0",
            "method": "Player.Open",
            "id": "openPlayer",
            "params": {
                "item": {
                    "file": seed.rstrip("\n")
                },
            }
        }
        execute_log_command(play_cmd)

        playlistid = current_playlist()["id"]
        for item in infile:
            queue_cmd = [
                {
                    "jsonrpc": "2.0",
                    "method": "Playlist.Add",
                    "id": "queueEp",
                    "params": {
                        "playlistid": playlistid,
                        "item": {
                            "file": item.rstrip("\n")
                        }
                    }
                }
            ]
            execute_log_command(queue_cmd)

    items = current_playlist()["items"]
    with open(TEST_DATA, "w") as outfile:
        outfile.write(unicode([item["id"] for item in items]))

def sort_json():
    with open(TEST_DATA, "r") as infile:
        data = json.load(infile)
    data["startlist"] = sorted(data["startlist"])
    with open(TEST_DATA, "w") as outfile:
        json.dump(data, outfile)

def load_data():
    with open(CURRENT_DATA, "r") as infile:
        data = json.load(infile)
    return data

def reset_data(data):
    while data["watched"]:
        data["to_watch"].append(data["watched"].pop())
    data["to_watch"] = sorted(data["to_watch"])
    data["currently_playing"] = []
    return data

def clear_playlist(data, playlistid):
    clear_cmd = [
        {
            "jsonrpc": "2.0",
            "method": "Playlist.Clear",
            "id": "clearPlaylist",
            "params": {
                "playlistid": playlistid,
            }
        }
    ]
    execute_log_command(clear_cmd)
    data["currently_playing"] = []
    return data

def add_item(data, playlistid, num_to_add=1):
    # get a random num_to_add number of items, and add them to the current playlist
    batch_add_cmd = []
    for _ in range(num_to_add):
        randex = randint(0, len(data["to_watch"]))
        to_add = data["to_watch"].pop(randex)
        data["currently_playing"].append(to_add)
        data["watched"].append(to_add)
        batch_add_cmd.append(
            {
                "jsonrpc": "2.0",
                "method": "Playlist.Add",
                "id": "queueEp",
                "params": {
                    "playlistid": playlistid,
                    "item": {
                        "episodeid": to_add,
                    }
                }
            }
        )
    execute_log_command(batch_add_cmd)
    return data

def play_new_queue(data, playlistid):
    data = clear_playlist(data, playlistid)

    data = add_item(data, playlistid, IDEAL_QUEUE_LENGTH)
    play_cmd = {
        "jsonrpc": "2.0",
        "method": "Player.Open",
        "id": "openPlayer",
        "params": {
            "item": {
                "playlistid": playlistid,
            },
        }
    }
    execute_log_command(play_cmd)
    return data

def skip():
    player = active_video_player()
    goto_next_cmd = {
        "jsonrpc": "2.0",
        "method": "Player.GoTo",
        "id": "gotoNext",
        "params": {
            "playerid": player,
            "to": "next"
        }
    }
    execute_log_command(goto_next_cmd)

def fullscreen():
    fullscreen_cmd = {
        "jsonrpc": "2.0",
        "method": "GUI.SetFullscreen",
        "id": "fullscreen",
        "params": {
            "fullscreen": True
        }
    }
    execute_log_command(fullscreen_cmd)


def main():
    """
    Main script method
    """
    #first_run()
    #sort_json()

    data = load_data()
    playlist = current_playlist()
    if len(data["to_watch"]) < IDEAL_QUEUE_LENGTH:
        # reset from scratch
        data = reset(data)
        data = play_new_queue(data, playlist["id"])

    else:
        # Are we currently watching the last thing we queued?
        current_items = playlist["items"]
        id_list = sorted([item["id"] for item in current_items])
        active = active_video_player() != None
        xbmc.log(
            "active: {}, current: {}, saved: {}".format(
                active,
                id_list,
                sorted(data["currently_playing"])
            ),
            xbmc.LOGNOTICE
        )
        if active and id_list and id_list == sorted(data["currently_playing"]):
            # Add a new item, and skip to the next item in the list
            data = add_item(data, playlist["id"])
            skip()
        else:
            # Assume something else happened, restart from scratch
            data = play_new_queue(data, playlist["id"])

    fullscreen()

    # save updated data
    with open(CURRENT_DATA, "w") as outfile:
        json.dump(data, outfile)

if __name__ == '__main__':
    main()
