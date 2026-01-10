# 🛡️ Herald Bot - Dota 2 Automatic Match Tracker & Soundboard

Herald Bot is a specialized Dota 2 companion designed to bridge your in-game matches with Discord. It automatically tracks your performance, suggests heroes with "roast-aware" logic, and features a vocal soundboard to liven up your voice channel.

---

## 🚀 Key Features

### 📡 Automatic Monitoring
- **Polling:** Automatically checks the OpenDota API every **5 minutes** for new matches for every registered user.
- **Match Alerts:** Automatically posts a summary when a game finishes, provided the data is available on OpenDota.
- **Performance Labels:** Assigns dynamic titles based on in-game stats, such as **Smurf**, **Feeder**, **Passenger**, or **Support God**.
- **Role Detection:** Approximates player roles (1-5) based on farm priority (last hits).

### 🎲 Smart Randomizer (`!random`)
- **Hero Suggestions:** Generates a random hero based on a requested role (e.g., `!random carry`, `!random offlane`, `!random mid`, or `!random support`).
- **Contextual Roasts:** The bot tracks your previous match. If you played support last game and suddenly ask for a `carry` hero, the bot will notice your "identity crisis" and roast you before providing a suggestion.

### 🔊 Vocal Soundboard (`!vocal` & `!sounds`)
- **Play Sound:** `!vocal [filename]` joins your voice channel and plays an `.mp3` from the `/sounds` folder (e.g., `!vocal haha` plays `/sounds/haha.mp3`).
- **Random Play:** If no filename is provided, it selects a random sound from the folder.
- **Library List:** `!sounds` displays a full list of all available files in the `/sounds` folder so you know exactly what sounds you can use.

### 🎮 Dota Commands
- `!register <SteamID3>`: Links your Discord account to your SteamID3.
- `!status`: Advanced match summary featuring averages, impact stats, and deeper information than `!last`.
- `!last`: A quick snapshot of your most recent match data.
- `!check`: Manually forces a check for new matches across all registered users.
- `!help`: Displays this command list.

### 🇷🇴 Romanian insults
- **Unknown Commands:** Any unrecognized command will trigger a random, aggressive **Romanian insult**.

---

## 🛠 Project Structure & Setup

### 📂 Folder Layout
```text
.
├── bot.py              # Main script
├── token.json          # (Manual) Discord Token
├── users.json          # (Manual) User database
├── channel_id.txt      # (Manual) Notification Channel ID
├── sounds/             # (Manual) Your .mp3 files go here
└── images/             # (Included) Hero portrait assets

### 🛠️ Manual Configuration (Required)
The following files are **not included** in the repository for privacy and must be created manually in the root folder:

* **`token.json`**: Store your Discord Bot Token here.
    * *Format:* `{"token": "YOUR_TOKEN"}`
* **`users.json`**: Initialize as an empty file or `{}`. This stores the Steam-Discord links.
* **`channel_id.txt`**: Paste the ID of the Discord channel where automatic match alerts should be posted.
* **`sounds/`**: Create this folder and fill it with your own `.mp3` sound files.

### 🖼️ 2. Assets Included
* **`images/`**: This folder contains the hero portraits used for match alerts. **Do not move or delete this folder.**

### 🤖 3. Discord Bot Setup
1.  Create a bot in the [Discord Developer Portal](https://discord.com/developers/applications).
2.  **Enable Intents:** You **MUST** enable **Message Content Intent** and **Voice State Intent** in the "Bot" tab.
3.  Copy the Token into your `token.json`.

### ⚠️ Important Limitations
* **`!toxic` Command:** This command is hard-coded to a private, locally-hosted LLM server (Home Server). It will not work for anyone else as it points to a specific internal IP address.
* **Dependencies:** Requires **FFmpeg** installed on the host OS or container for vocal sounds to function.
* **Library Requirements:** Ensure `discord.py[voice]`, `pynacl`, `aiohttp`, and `ollama` are installed.

### 🤝 Credits
* Match data provided by the [OpenDota API](https://www.opendota.com/).
* Developed using **Python** and **discord.py**.

