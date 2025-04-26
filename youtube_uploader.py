import os
import csv
import time # To add delays
import sys # To exit gracefully on errors

import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

# --- Configuration ---
CSV_FILE = 'all.csv'
PLAYLIST_NAME = 'Your Target YouTube Playlist Name' # <--- CHANGE THIS
CLIENT_SECRETS_FILE = "client_secrets.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
TOKEN_FILE = 'token.json' # Stores user's access token
PROCESSED_LOG_FILE = 'processed_songs.log' # File to track successfully added songs

# --- Helper Functions for Logging ---
def load_processed_songs(log_file):
    """Loads successfully processed Track URIs from the log file into a set."""
    processed = set()
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                processed.add(line.strip())
        print(f"Loaded {len(processed)} previously processed song URIs from {log_file}.")
    except FileNotFoundError:
        print(f"Log file '{log_file}' not found. Starting fresh.")
    except Exception as e:
        print(f"Error loading log file '{log_file}': {e}")
    return processed

def log_processed_song(log_file, track_uri):
    """Appends a successfully processed Track URI to the log file."""
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{track_uri}\n")
    except Exception as e:
        print(f"Error writing to log file '{log_file}': {e}")

# --- Authentication (Same as before) ---
def get_authenticated_service():
    """Gets an authenticated YouTube API service object."""
    credentials = None
    if os.path.exists(TOKEN_FILE):
        credentials = google.oauth2.credentials.Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                print("Refreshing access token...")
                credentials.refresh(google.auth.transport.requests.Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                print("Need to re-authenticate.")
                flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRETS_FILE, SCOPES)
                credentials = flow.run_local_server(port=0)
        else:
            print("Need to authenticate.")
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            credentials = flow.run_local_server(port=0) # Opens browser for auth

        with open(TOKEN_FILE, 'w') as token:
            token.write(credentials.to_json())
            print(f"Credentials saved to {TOKEN_FILE}")

    try:
        return googleapiclient.discovery.build(
            API_SERVICE_NAME, API_VERSION, credentials=credentials)
    except Exception as e:
        print(f"Error building YouTube service: {e}")
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
            print(f"Deleted potentially invalid {TOKEN_FILE}. Please re-run the script.")
        return None


# --- YouTube Functions (Same as before, with Quota Check Returns) ---
def find_playlist_id(youtube, playlist_name):
    """Finds the ID of a playlist by its name."""
    print(f"Searching for your playlist named '{playlist_name}'...")
    request = youtube.playlists().list(
        part="snippet",
        mine=True,
        maxResults=50
    )
    try:
        response = request.execute()
    except googleapiclient.errors.HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred while searching for playlists: {e.content}")
        if e.resp.status == 401:
             print("Authentication error. Your access token might be invalid or expired.")
             print(f"Try deleting the '{TOKEN_FILE}' file and re-running the script to re-authenticate.")
        elif e.resp.status == 403 and 'quotaExceeded' in str(e.content):
             print("YouTube API Quota Exceeded while trying to find playlist. Cannot continue.")
             sys.exit(1) # Exit script if we can't even find the playlist due to quota
        return None
    except Exception as e:
        print(f"An unexpected error occurred while searching for playlists: {e}")
        return None

    for item in response.get("items", []):
        if item["snippet"]["title"] == playlist_name:
            playlist_id = item["id"]
            print(f"Found playlist '{playlist_name}' with ID: {playlist_id}")
            return playlist_id

    print(f"Error: Playlist '{playlist_name}' not found in your YouTube account.")
    print("Please ensure the playlist exists and the name matches exactly (case-sensitive).")
    return None


def search_youtube_video(youtube, query):
    """Searches YouTube for a video based on the query."""
    print(f"Searching YouTube for: '{query}'")
    request = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=1
    )
    try:
        response = request.execute()
        if response.get("items"):
            video_id = response["items"][0]["id"]["videoId"]
            video_title = response["items"][0]["snippet"]["title"]
            print(f"  Found video: '{video_title}' (ID: {video_id})")
            return video_id
        else:
            print(f"  No video found for query: '{query}'")
            return None
    except googleapiclient.errors.HttpError as e:
        print(f"  An HTTP error {e.resp.status} occurred during search: {e.content}")
        if e.resp.status == 403 and 'quotaExceeded' in str(e.content):
            print("  YouTube API Quota Exceeded during search.")
            return "QUOTA_EXCEEDED"
        return None
    except Exception as e:
        print(f"  An unexpected error occurred during search: {e}")
        return None


def add_video_to_playlist(youtube, playlist_id, video_id):
    """Adds a video to a specific playlist."""
    print(f"  Attempting to add video ID {video_id} to playlist ID {playlist_id}...")
    request = youtube.playlistItems().insert(
        part="snippet",
        body={
          "snippet": {
            "playlistId": playlist_id,
            "resourceId": {
              "kind": "youtube#video",
              "videoId": video_id
            }
          }
        }
    )
    try:
        response = request.execute()
        print(f"  Successfully added video '{response['snippet']['title']}' to the playlist.")
        return True # Signal success
    except googleapiclient.errors.HttpError as e:
        error_content = e.content.decode('utf-8') if hasattr(e.content, 'decode') else str(e.content)
        if 'playlistItemDuplicate' in error_content:
             print(f"  Video ID {video_id} is already in the playlist.")
             return False # Indicate failure (but not quota)
        elif e.resp.status == 403:
             if 'quotaExceeded' in error_content:
                 print("  YouTube API Quota Exceeded during add.")
                 return "QUOTA_EXCEEDED" # Signal quota exceeded
             else:
                 print(f"  Error adding video ID {video_id}: Permission denied. {error_content}")
                 return False # Indicate failure
        elif e.resp.status == 404:
             print(f"  Error adding video ID {video_id}: Playlist or Video not found? {error_content}")
             return False # Indicate failure
        else:
             print(f"  An HTTP error {e.resp.status} occurred while adding video: {error_content}")
             return False # Indicate failure
    except Exception as e:
        print(f"  An unexpected error occurred while adding video: {e}")
        return False # Indicate failure

# --- Main Execution ---
if __name__ == "__main__":
    youtube = get_authenticated_service()
    if not youtube:
        print("Exiting: Could not authenticate YouTube service.")
        sys.exit(1)

    if PLAYLIST_NAME == 'Your Target YouTube Playlist Name':
        print("Error: Please update the 'PLAYLIST_NAME' variable in the script.")
        sys.exit(1)

    target_playlist_id = find_playlist_id(youtube, PLAYLIST_NAME)
    if not target_playlist_id:
        print(f"\nExiting: Could not find playlist '{PLAYLIST_NAME}'.")
        sys.exit(1)

    # Load the set of already processed track URIs
    processed_uris = load_processed_songs(PROCESSED_LOG_FILE)
    newly_added_count = 0
    skipped_count = 0
    already_processed_count = len(processed_uris) # Count loaded from file
    not_found_count = 0
    error_count = 0
    quota_hit = False

    try:
        with open(CSV_FILE, mode='r', encoding='utf-8-sig') as infile:
            reader = csv.DictReader(infile)
            required_columns = ['Track Name', 'Artist Name(s)', 'Track URI'] # Ensure Track URI exists
            if not all(col in reader.fieldnames for col in required_columns):
                missing = [col for col in required_columns if col not in reader.fieldnames]
                print(f"Error: CSV file '{CSV_FILE}' is missing required column(s): {', '.join(missing)}")
                sys.exit(1)

            print(f"\n--- Starting processing. Skipping {already_processed_count} songs found in '{PROCESSED_LOG_FILE}'. ---")
            total_rows = 0 # Count total rows to process in this run
            rows_to_process = []
            # First pass to count rows and filter out already processed
            for row in reader:
                 total_rows += 1
                 track_uri = row.get('Track URI', '').strip()
                 if track_uri and track_uri not in processed_uris:
                     rows_to_process.append(row)
                 elif not track_uri:
                      print(f"Warning: Row {total_rows+1} missing Track URI, cannot track processing.") # +1 for header row
                      rows_to_process.append(row) # Process anyway, but won't be logged
                 # Else: track_uri is in processed_uris, skip silently here, counted above

            print(f"Found {total_rows} songs in CSV. Attempting to process {len(rows_to_process)} new songs.")

            # Second pass to actually process
            for i, row in enumerate(rows_to_process):
                current_row_num_in_file = i + already_processed_count + 1 # Approximate original row for logging
                title = row.get('Track Name', '').strip()
                artist = row.get('Artist Name(s)', '').strip()
                track_uri = row.get('Track URI', '').strip() # Get URI again

                if not title or not artist:
                    print(f"Skipping row ~{current_row_num_in_file}: Missing Track Name or Artist Name(s)")
                    skipped_count += 1
                    continue

                # --- Check if already processed THIS RUN (e.g., duplicate in CSV) ---
                # Note: The initial filter handles songs from the log file.
                # This check is less critical now but harmless.
                if track_uri and track_uri in processed_uris:
                    print(f"Skipping row ~{current_row_num_in_file} ('{title}'): URI {track_uri} processed earlier in this session or file.")
                    continue # Should ideally not happen with the pre-filter, but safe check

                # --- Process the song ---
                print(f"\nProcessing CSV Row ~{current_row_num_in_file}: '{title}' by '{artist}' (URI: {track_uri or 'N/A'})")
                search_query = f"{title} {artist} official audio" # Or refine as needed
                video_id = search_youtube_video(youtube, search_query)

                if video_id == "QUOTA_EXCEEDED":
                    print("Stopping script due to Quota Exceeded during search.")
                    quota_hit = True
                    break # Exit the processing loop

                if video_id:
                    add_result = add_video_to_playlist(youtube, target_playlist_id, video_id)

                    if add_result == "QUOTA_EXCEEDED":
                        print("Stopping script due to Quota Exceeded during add.")
                        quota_hit = True
                        break # Exit the processing loop
                    elif add_result is True:
                        newly_added_count += 1
                        # Log success only if we have a valid URI
                        if track_uri:
                            log_processed_song(PROCESSED_LOG_FILE, track_uri)
                            processed_uris.add(track_uri) # Add to in-memory set too
                        else:
                             print("  Warning: Successfully added, but couldn't log as processed due to missing Track URI.")
                        time.sleep(1.5) # Slightly longer sleep after success
                    elif add_result is False:
                        # Add failed (duplicate, permissions, not found etc.)
                        error_count += 1
                        time.sleep(2)
                else:
                    # Video not found by search
                    not_found_count +=1
                    time.sleep(1)

            print("\n--- Finished processing loop ---")
            if quota_hit:
                print("Processing stopped prematurely due to hitting YouTube API quota.")

    except FileNotFoundError:
        print(f"Error: CSV file '{CSV_FILE}' not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    # --- Summary ---
    print("\n--- Run Summary ---")
    print(f"Songs skipped (missing data):     {skipped_count}")
    print(f"Songs skipped (already processed): {already_processed_count}")
    print(f"Videos successfully added now:    {newly_added_count}")
    print(f"Videos not found on YouTube:      {not_found_count}")
    print(f"Errors during add operation:      {error_count} (Check logs)")
    print("-----------------")
    if quota_hit:
        print("NOTE: API Quota was hit. Re-run the script later to continue.")
    elif newly_added_count == 0 and error_count == 0 and not_found_count == 0 and skipped_count == 0:
         print("It seems all processable songs from the CSV were already in the log file.")
    else:
         print("Run complete.")
