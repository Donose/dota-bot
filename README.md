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

### 🇷🇴 Romanian "Security"
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
