"""
Main script for this hacked-together plugin
"""
import sys
import json
import xbmc

def executeLogCommand(cmd):
    """
    Helper for executing commands, with logging if debug mode on.
    """
    raw_req = json.dumps(cmd)
    xbmc.log("JSONRPC request: {}".format(raw_req), xbmc.LOGDEBUG)

    raw_resp = xbmc.executeJSONRPC(raw_req)
    xbmc.log("JSONRPC result: {}".format(raw_resp), xbmc.LOGDEBUG)

    return json.loads(raw_resp)

# Unused utility things I'm copying over from my other plugin that don't yet have a home

    # Play the first item
    playCmd = {
        "jsonrpc": "2.0",
        "params": {
            "item": {
                playlist[0][0]: playlist[0][1]
            },
        },
        "method": "Player.Open",
        "id": "openPlayer"
    }
    playResult = executeLogCommand(playCmd)
    playlist.remove(playlist[0])

    # Get the currently playing playlist from Kodi
    playlistsCmd = {
        "jsonrpc": "2.0",
        "method": "Playlist.GetPlaylists",
        "id": "getPlaylists"
    }
    playlistsResult = executeLogCommand(playlistsCmd)
    videoPlaylist = next(playlist for playlist in playlistsResult["result"] if playlist["type"] == "video")

    # Get the currently active video player from Kodi
    activePlayersCmd = {
        "jsonrpc": "2.0",
        "method": "Player.GetActivePlayers",
        "id": "getActivePlayers"
    }
    activePlayersResult = executeLogCommand(activePlayersCmd)
    activeVideoPlayer = next(player["playerid"] for player in activePlayersResult["result"] if player["type"] == "video")

    # Error out if things aren't going according to plan
    if not activeVideoPlayer and videoPlaylist:
        xbmc.log("error! Could not get a single video player and playlist! Exiting...")
        sys.exit()

    # Add the remainder of our items to the current playlist
    addAllBatchCmd = [
        {
            "jsonrpc": "2.0",
            "method": "Playlist.Add",
            "id": "queueEp{}".format(item[1]),
            "params": {
                "playlistid": videoPlaylist["playlistid"],
                "item": {
                    item[0]: item[1]
                }
            }
        } for item in playlist
    ]
    addAllEpsResult = executeLogCommand(addAllBatchCmd)

"""
Plans for main method:
    get the currently plaing list from kodi
    did this script make that list?
        if yes, skip to the next item and ensure queue length
        if no, stop playback, play something, and queue some things
"""

# Sidebar: I'm never going to enqueue all 1000+ items at once. If I enqueue 30 at once (and ensure that many when advancing episodes), that works out to ~10 hours of not touching anything before the list runs out. If that happens, it's probably time to stop watching TV for a bit anyways.

"""
Data, all kept as files on disk:
    master reference list, read only. List of file paths, hand-grepped from Kodi-created m3u file
    3 other files, think of them as such:
        input: files that have yet to be selected in this pass through the master list
        current: what the script thinks the current list of playing items is
        selected: where I "move" file paths after they've been selected
"""
