"""
Main script for this hacked-together plugin
"""
import json
import xbmc

# Constants
IDEAL_QUEUE_LENGTH = 30  # This works out to ~10 hours of tv if uninterrupted
LAST_QUEUE_FILE = "resources/last_queue.json"

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
            "items": current_playlist_contents["result"]["items"]
        }
    return None

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
    return player["playerid"]

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
    return result["result"]["lastplayed"]

def seed_last_queued():
    """
    Seed the queue of script-determined items to play.
    """
    raise NotImplementedError()

def play_and_queue(items, index):
    """
    Plays items[index] from where it was last stopped, and queues items[index:].
    """
    xbmc.log(
        "in play_and_queue, items: {}, index: {}".format(
            items, index
        ), xbmc.LOGDEBUG
    )

def trim_active_playlist():
    """
    Removes all items in the currently active playlist that occur before the current item.
    """
    pass  # (Playlist.Remove, using indices and playlistid)

def pad_active_playlist():
    """
    Randomly selects new items to fill out the current playlist.
    """
    pass

def main():
    """
    Main script method
    """
    currently_viewing = current_playlist()
    last_queued = get_last_queued_playlist()
    active_player = active_video_player()
    if (
            last_queued.get("hashed", None) == hash(
                (item["id"] for item in currently_viewing["items"])
            )
            and active_player is not None
    ):
        goto_next(active_player)
    else:
        if len(last_queued) == 0:
            last_queued = seed_last_queued()
            latest_index = -1
        else:
            latest_index = calc_most_recent(last_queued["items"])
        play_and_queue(last_queued, latest_index)
        currently_viewing = current_playlist()

    trim_active_playlist()
    pad_active_playlist()
    save_current_playlist((item["id"] for item in current_playlist()))

if __name__ == '__main__':
    main()
