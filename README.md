# YouTube Playlist CSV Uploader Script Instructions

This is the source code for a **local Python script** intended for **personal use only**. It allows a user to populate their own YouTube playlist from a CSV file containing song information.

**❗ It is NOT a publicly hosted application or website. ❗**

This script must be downloaded and run locally by the user *after* they obtain their own Google Cloud credentials (`client_secrets.json`).

> **🚨 IMPORTANT SECURITY NOTE:**
> You **MUST** generate your own Google Cloud credentials (`client_secrets.json`). **DO NOT** use anyone else's file, and **NEVER** share your own `client_secrets.json` or the `token.json` file that the script creates (as it contains your specific authorization).

---

## Prerequisites

Before you begin, ensure you have the following:

1.  **Install Python:**
    *   Make sure you have Python 3 installed on your system.
    *   Download from [python.org](https://www.python.org/).
    *   **Crucial:** During installation, make sure to check the box similar to **"Add Python to PATH"** or **"Add python.exe to Path"**.

2.  **Verify Pip:**
    *   Open Command Prompt (`cmd`) or PowerShell.
    *   Type `pip --version` and press Enter.
    *   Pip usually comes with Python. If you get an error like `'pip' is not recognized...`, you might need to manually ensure Python's `Scripts` directory is in your system's `PATH` environment variable (Search Windows for "Edit the system environment variables" to check/add this).

3.  **Install Required Libraries:**
    *   Open Command Prompt or PowerShell.
    *   Run the following command:
      ```bash
      pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
      ```

---

## Setup Steps

Follow these steps carefully to configure the script:

1.  ### Google Cloud Project & API Setup
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/) and log in with your Google account.
    *   Create a **New Project** or select an existing one using the dropdown at the top.
    *   Navigate to **APIs & Services > Library**.
    *   Search for `YouTube Data API v3`.
    *   Select it and click **Enable**.

2.  ### Configure OAuth Consent Screen
    *   In the Google Cloud Console, go to **APIs & Services > OAuth consent screen**.
    *   Select User Type: **External**. Click **Create**.
    *   Fill in the required fields:
        *   **App name:** (e.g., "My YouTube Playlist Uploader") - This is what you'll see during authorization.
        *   **User support email:** Your email address.
        *   **Developer contact information:** Your email address again.
    *   Click **Save and Continue** through the Scopes and Test Users sections (defaults are usually fine for personal use).
    *   Review the summary and go **Back to Dashboard**.

3.  ### Generate Your Credentials (`client_secrets.json`)
    *   Go to **APIs & Services > Credentials**.
    *   Click **+ CREATE CREDENTIALS** at the top and select **OAuth client ID**.
    *   Select Application type: **Desktop app**.
    *   Give it a name (e.g., "Playlist Script Credentials").
    *   Click **CREATE**.
    *   A pop-up will appear. Click the **DOWNLOAD JSON** button (looks like ⇩).
    *   **Important:** Rename the downloaded file to exactly `client_secrets.json`.

4.  ### Prepare Project Folder & Files
    *   Create a dedicated folder on your computer for this project (e.g., `YouTubeUploader`).
    *   Place the Python script file (e.g., `youtube_uploader.py`) inside this folder.
    *   Place the `client_secrets.json` file (that you downloaded and renamed) into the **SAME** folder.
    *   Prepare your CSV data file (e.g., `all.csv`). It **MUST** contain columns named exactly:
        *   `Track Name`
        *   `Artist Name(s)`
        *   `Track URI` (Used for tracking processed songs to save quota)
    *   Place this CSV file in the **SAME** folder as the script and `client_secrets.json`.

5.  ### Edit the Script Configuration
    *   Open the Python script file (`.py`) in a text editor (like Notepad++, VS Code, Sublime Text, etc.).
    *   Find the line that looks like this:
      ```python
      PLAYLIST_NAME = 'Your Target YouTube Playlist Name'
      ```
    *   **Change** the text `'Your Target YouTube Playlist Name'` to the **exact, case-sensitive name** of the YouTube playlist you want to add songs to.
    *   Save the changes to the script file.

6.  ### Create YouTube Playlist
    *   Make sure the playlist name you entered in the script exists in *your* YouTube account. Create it manually if it doesn't exist.

---

## Running the Script

1.  **Open Terminal:** Open Command Prompt or PowerShell on your computer.
2.  **Navigate to Folder:** Use the `cd` (change directory) command to navigate to the folder containing your script, `client_secrets.json`, and CSV file.
    *   Example: `cd C:\Users\YourUsername\Documents\YouTubeUploader`
3.  **Run Script:** Execute the script using Python:
    *   Type `python your_script_name.py` (replace `your_script_name.py` with the actual name of the Python file) and press Enter.
4.  **Authorization (First Run Only):**
    *   Your default web browser should open automatically, prompting you to log in to Google.
    *   **Log in** using the Google Account that owns the target YouTube playlist.
    *   Google will display a consent screen asking for permission for the script (using the "App name" you set earlier) to manage your YouTube account. Review the permissions and click **"Allow"**.
    *   **Verification Warning:** You might see a screen saying "Google hasn't verified this app". This is normal for personal scripts. Click **"Advanced"** and then choose **"Go to [Your App Name] (unsafe)"**.
    *   After authorization, you might see a confirmation message in the browser tab (e.g., "Authentication successful"). You can close this browser tab.
    *   The script will create a `token.json` file in your project folder. **Do not delete or share this file.** It stores your authorization so you don't have to log in via the browser every time you run the script.
5.  **Processing:**
    *   The script will now start running in your terminal window.
    *   It will read the CSV file, check the `processed_songs.log` (which it creates if it doesn't exist) to skip already added songs, search YouTube for matches, and attempt to add them to your playlist.
    *   Watch the terminal output for progress messages and any potential errors.
6.  **Quota Limits & Resuming:**
    *   The YouTube Data API has daily usage limits (quotas). If you have a large CSV file, the script will likely hit this limit before processing all songs.
    *   The script is designed to detect quota errors, stop processing, and inform you.
    *   **To continue:** Simply run the script again the next day (quotas usually reset around midnight Pacific Time). Thanks to the `processed_songs.log` file, it will automatically skip the songs already added and continue where it left off.
