"""
Main script for this hacked-together plugin
"""
import json
import xbmc

# Constants
PLAYLIST_CONFIDENCE_NUMBER = 4
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

"""
Unused utility things I'm copying over from my other plugin that don't yet have a home

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
    playResult = execute_log_command(playCmd)
    playlist.remove(playlist[0])

    # Get the currently playing playlist from Kodi
    # Get the currently active video player from Kodi
    activePlayersCmd = {
        "jsonrpc": "2.0",
        "method": "Player.GetActivePlayers",
        "id": "getActivePlayers"
    }
    activePlayersResult = execute_log_command(activePlayersCmd)
    activeVideoPlayer = next(player["playerid"] for player in activePlayersResult["result"] if player["type"] == "video")

    # Error out if things aren't going according to plan
    if not activeVideoPlayer and currentVideoPlaylist:
        xbmc.log("error! Could not get a single video player and playlist! Exiting...")
        sys.exit()

    # Add the remainder of our items to the current playlist
    addAllBatchCmd = [
        {
            "jsonrpc": "2.0",
            "method": "Playlist.Add",
            "id": "queueEp{}".format(item[1]),
            "params": {
                "playlistid": currentVideoPlaylist["playlistid"],
                "item": {
                    item[0]: item[1]
                }
            }
        } for item in playlist
    ]
    addAllEpsResult = execute_log_command(addAllBatchCmd)
"""

"""
Plans for main method:
    get the currently plaing list from kodi
    did this script make that list?
        if yes, skip to the next item and ensure queue length
        if no, stop playback, play something, and queue some things
"""
def main():
    """
    Main script method
    """
    # Get the currently playing playlist, or None if nothing is playing
    current_playlists_cmd = {
        "jsonrpc": "2.0",
        "method": "Playlist.GetPlaylists",
        "id": "getCurrentPlaylists"
    }
    playlists_result = execute_log_command(current_playlists_cmd)
    current_playlist = next(
        (playlist for playlist in playlists_result["result"] if playlist["type"] == "video"),
        None
    )
    if current_playlist:
        playlist_contents_cmd = {
            "jsonrpc": "2.0",
            "method": "Playlist.GetItems",
            "id": "getPlaylistItems",
            "params": {
                "playlistid": current_playlist["playlistid"]
            }
        }
        current_playlist_contents = execute_log_command(playlist_contents_cmd)
        # DEBUG TIME
        item_ids = [
            item["id"]
            for item in current_playlist_contents["result"]["items"]
            if item["type"] == "episode"
        ]
        xbmc.log("playlist items: {}".format(item_ids), xbmc.LOGDEBUG)

    # Now, compare current playlist with what we queued the last time this script ran
    # If the last few items match, we assume it's still the same playlist

"""
Sidebar: I'm never going to enqueue all 1000+ items at once.
If I enqueue 30 at once (and ensure that many when advancing episodes), that works out to ~10 hours
of not touching anything before the list runs out. If that happens, it's probably time to stop
watching TV for a bit anyways.

Data, all kept as files on disk:
    master reference list, read only. List of file paths, hand-grepped from Kodi-created m3u file
    3 other files, think of them as such:
        input: files that have yet to be selected in this pass through the master list
        current: what the script thinks the current list of playing items is
        selected: where I "move" file paths after they've been selected
"""

if __name__ == '__main__':
    main()
