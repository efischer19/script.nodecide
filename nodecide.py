"""
Main script for this hacked-together plugin
"""
import json
import os
import xbmc
import xbmcaddon

# Constants and contextual variables
__settings__ = xbmcaddon.Addon(id='script.nodecide')
__cwd__ = __settings__.getAddonInfo('path')
LAST_QUEUE_FILE = os.path.join(__cwd__, "resources", "last_queue.json")
INFILE = os.path.join(__cwd__, "resources", "in.data")

IDEAL_QUEUE_LENGTH = 30  # This works out to ~10 hours of tv if uninterrupted

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
                "properties": ["lastplayed"]
            }
        }
        current_playlist_contents = execute_log_command(playlist_contents_cmd)
        return {
            "id": current["playlistid"],
            "items": current_playlist_contents["result"].get("items", [])
        }
    return None

def current_item():
    """
    Returns the id of the item that is currently playing.
    """
    current_item_cmd = {
        "jsonrpc": "2.0",
        "method": "Player.GetItem",
        "id": "getItem",
        "params": {
            "playerid": active_video_player(),
        }
    }
    return execute_log_command(current_item_cmd)["result"]["item"]["id"]

def get_last_queued_playlist():
    """
    Gets this script's record of the last queued playlist.
    """
    with open(LAST_QUEUE_FILE, "r") as readfile:
        return json.load(readfile)

def save_current_playlist(items):
    """
    Serializes information about the current script-defined playlist to file.
    """
    serialized = {
        "items": list(items),
        "hashed": hash(items),
    }
    with open(LAST_QUEUE_FILE, "w") as savefile:
        json.dump(serialized, savefile)

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

def goto_next(player):
    """
    Advances the currently active player to the next item.
    """
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

def calc_most_recent(items):
    """
    Finds the item that was last played, returning the index in items.
    """
    last_played_data = [
        get_last_played(item)
        for item in items
    ]
    latest = max(last_played_data)
    return last_played_data.index(latest)

def get_last_played(item):
    """
    Queries Kodi for lastplayed data for a given item.
    """
    last_played_query = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetEpisodeDetails",
        "id": "last_played_{}".format(item),
        "params": {
            "episodeid": item,
            "properties": ["lastplayed"]
        }
    }
    result = execute_log_command(last_played_query)
    return result["result"]["episodedetails"]["lastplayed"]

def seed_last_queued():
    """
    Return a list of fie paths
    """
    ret = []
    with open(INFILE, "r") as in_data:
        for _ in range(IDEAL_QUEUE_LENGTH):
            ret.append(in_data.readline().rstrip("\n"))
    xbmc.log("Current length: {}".format(len(ret)), xbmc.LOGDEBUG)
    return ret

def play_and_queue(items, index, use_ids=True):
    """
    Plays items[index] from where it was last stopped, and queues items[index:].
    """
    play_cmd = {
        "jsonrpc": "2.0",
        "method": "Player.Open",
        "id": "openPlayer",
        "params": {
            "item": {
                "episodeid" if use_ids else "file": items[index],
            },
        }
    }
    execute_log_command(play_cmd)

    playlistid = current_playlist()["id"]

    batch_queue_cmd = [
        {
            "jsonrpc": "2.0",
            "method": "Playlist.Add",
            "id": "queueEp",
            "params": {
                "playlistid": playlistid,
                "item": {
                    "episodeid" if use_ids else "file": item,
                }
            }
        } for item in items[index:]
    ]
    execute_log_command(batch_queue_cmd)

def trim_active_playlist():
    """
    Removes all items in the currently active playlist that occur before the current item.
    """
    playlist = current_playlist()
    item = current_item()
    if playlist.get("items") is not None:
        xbmc.log("item: {}".format(item), xbmc.LOGDEBUG)
        xbmc.log("playlist['items']: {}".format(playlist["items"]), xbmc.LOGDEBUG)
        xbmc.log("the thing: {}".format([item["id"] for item in playlist["items"]]), xbmc.LOGDEBUG)
        bulk_remove_cmd = []
        for index, item_id in enumerate(playlist["items"]):
            if item_id == item:
                break
            bulk_remove_cmd.append(
                {
                    "jsonrpc": "2.0",
                    "method": "Playlist.Remove",
                    "id": "removeEp",
                    "params": {
                        "playlistid": playlist["id"],
                        "position": index
                    }
                }
            )
        execute_log_command(bulk_remove_cmd)

def pad_active_playlist():
    """
    Add items to fill out the current playlist.
    """
    playlist = current_playlist()
    with open(INFILE, "r+") as infile:
        new_paths = []
        xbmc.log("Current length: {}".format(len(playlist["items"])), xbmc.LOGDEBUG)
        for _ in range(IDEAL_QUEUE_LENGTH - len(playlist["items"])):
            new_paths.append(infile.readline().rstrip("\n"))
        infile.seek(0)
        point = 0
        for path in infile:
            infile.seek(point)
            if path in new_paths:
                infile.write("\n")
            else:
                infile.write(path + "\n")
            point = infile.tell()

    batch_queue_cmd = [
        {
            "jsonrpc": "2.0",
            "method": "Playlist.Add",
            "id": "queueEp",
            "params": {
                "playlistid": playlist["id"],
                "item": {
                    "file": item,
                }
            }
        } for item in new_paths
    ]
    execute_log_command(batch_queue_cmd)

def main():
    """
    Main script method
    """
    currently_viewing = current_playlist()
    last_queued = get_last_queued_playlist()
    active_player = active_video_player()
    xbmc.log("last_queued hash: {}".format(last_queued["hashed"]), xbmc.LOGDEBUG)
    xbmc.log("current items: {}".format(currently_viewing["items"]), xbmc.LOGDEBUG)
    xbmc.log("calc hash: {}".format(hash(
        (item["id"] for item in currently_viewing["items"])
    )), xbmc.LOGDEBUG)
    if (
            last_queued.get("hashed", None) == hash(
                (item["id"] for item in currently_viewing["items"])
            )
            and active_player is not None
    ):
        goto_next(active_player)
    else:
        if len(last_queued) == 0:
            play_and_queue(seed_last_queued(), 0, use_ids=False)
        else:
            latest_index = calc_most_recent(last_queued["items"])
            xbmc.log("last_queued: {}".format(last_queued), xbmc.LOGDEBUG)
            xbmc.log("latest_index: {}".format(latest_index), xbmc.LOGDEBUG)
            play_and_queue(last_queued, latest_index + 1)

    trim_active_playlist()
    pad_active_playlist()
    save_current_playlist((item["id"] for item in current_playlist()["items"]))

if __name__ == '__main__':
    main()
