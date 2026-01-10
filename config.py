import os
import json

def _read_file_str(path):
    """Reads a file and returns the stripped content."""
    try:
        with open(path, 'r') as f:
            return f.read().strip()
    except Exception:
        return None

# --- SECURE CONFIGURATION LOADING ---
TOKEN = _read_file_str('token.txt') or os.environ.get('DISCORD_TOKEN')
_channel_raw = _read_file_str('channel_id.txt') or os.environ.get('DISCORD_CHANNEL_ID')
try:
    CHANNEL_ID = int(_channel_raw) if _channel_raw else None
except Exception:
    CHANNEL_ID = None

# --- DATA FILE LOADING ---
def load_users():
    if os.path.exists('users.json'):
        with open('users.json', 'r') as f:
            return json.load(f)
    return {}

def load_messages():
    if os.path.exists('messages.json'):
        with open('messages.json', 'r') as f:
            return json.load(f)
    print("WARNING: messages.json not found. Using default messages.")
    return {
        "uncarryable": ["Team was too heavy."],
        "feeder": ["Literally a creep."],
        "smurf_alert": ["Reported for smurfing."],
        "solid_performance": ["Good game, well played."],
        "carried": ["Got carried like a dog."]
    }

def load_roasts():
    if os.path.exists('roasts.json'):
        with open('roasts.json', 'r') as f:
            return json.load(f)
    print("WARNING: roasts.json not found. Using default roasts.")
    return {
        "generic_roasts": ["I couldn't find any roasts, just like you can't find any wins with {hero_name}."]
    }

def load_slangs():
    if os.path.exists('slangs.json'):
        with open('slangs.json', 'r') as f:
            return json.load(f)
    print("WARNING: slangs.json not found. Using default slang.")
    return ["Silence, fool."]

# --- STATIC MAPPINGS ---
MEMBER_NAMES = {
    "334023137777680385": "nhearyus",
    "404957674631987205": "denisciaus",
    "334748830098784256": "deny44",
    "334028472471257088": "aliku23",
    "153126890494754816": "Claudiu"
}

RANK_NAMES = {
    1: "Herald",
    2: "Guardian",
    3: "Crusader",
    4: "Archon",
    5: "Legend",
    6: "Ancient",
    7: "Divine",
    8: "Immortal",
}

DATABASE_FILE = 'users.json'

def validate():
    """Checks if essential configuration is loaded."""
    if not TOKEN:
        print("ERROR: No bot token found. Create token.txt or set DISCORD_TOKEN.")
        return False
    if not CHANNEL_ID:
        print("ERROR: No CHANNEL_ID found. Create channel_id.txt with numeric ID or set DISCORD_CHANNEL_ID.")
        return False
    return True
