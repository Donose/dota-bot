import aiohttp
import discord
import os
import random
from collections import defaultdict

# --- Custom Exceptions ---
class RateLimitException(Exception):
    pass

class NoMatchesException(Exception):
    pass

class PlayerDataException(Exception):
    pass

def get_rank_name(p_data, rank_names_map):
    """
    Takes the full player data dictionary from OpenDota 
    and returns a readable rank string.
    """
    if isinstance(p_data, int):
        rank_tier = p_data
        leaderboard = None
    else:
        rank_tier = p_data.get('rank_tier')
        leaderboard = p_data.get('leaderboard_rank')
    
    if leaderboard:
        return f"Immortal (Rank {leaderboard})"
    
    if not rank_tier:
        return "Unranked"
    
    tier = rank_tier // 10
    stars = rank_tier % 10
    
    name = rank_names_map.get(tier, "Unknown")
    
    if tier == 8: # Immortal doesn't have stars
        return "Immortal"
        
    return f"{name} {stars}"

async def update_hero_data(hero_names, hero_image_keys, hero_lookup, hero_roles):
    """
    Fetches all hero data from the OpenDota API and updates the provided hero dictionaries.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.opendota.com/api/heroes") as r:
            if r.status == 200:
                h_data = await r.json()
                for h in h_data:
                    h_id = h['id']
                    localized = h['localized_name']
                    img_key = h['name'].replace('npc_dota_hero_', '')
                    hero_names[h_id] = localized
                    hero_image_keys[h_id] = img_key
                    hero_lookup[localized.lower()] = img_key
                    hero_lookup[img_key.lower()] = img_key
                    hero_roles[h_id] = h.get('roles', [])
                print("✅ Hero data updated successfully.")
            else:
                print("❌ Failed to update hero data.")

def get_match_analysis(player_match_data, won, team_stats, enemy_team_stats, hero_roles, messages):
    """
    Analyzes a match based on KDA, win/loss, and comparison with team stats.
    Approximates player role based on farm priority.
    """
    kills = player_match_data.get('kills', 0)
    deaths = player_match_data.get('deaths', 0)
    assists = player_match_data.get('assists', 0)
    kda = (kills + assists) / max(1, deaths)

    # Basic analysis based on old system
    if not won:
        if kda >= 2.5:
            base_status, base_color, base_msg_key = "ZOO KEEPER ALERT", 0xf1c40f, "uncarryable"
        elif kda >= 1.4:
            base_status, base_color, base_msg_key = "DID HIS BEST ALERT", 0xe67e22, "tried_hard"
        else:
            base_status, base_color, base_msg_key = "FEEDER ALERT", 0xe74c3c, "feeder"
    else:  # Won
        if kda >= 3.5:
            base_status, base_color, base_msg_key = "SMURF ALERT", 0x2ecc71, "smurf_alert"
        elif assists >= 23 and deaths <= 6:
            base_status, base_color, base_msg_key = "SUPPORT SMURF ALERT", 0x1abc9c, "super_support"
        elif kda >= 1.4:
            base_status, base_color, base_msg_key = "SOLID PERFORMANCE ALERT", 0x1abc9c, "solid_performance"
        else:
            base_status, base_color, base_msg_key = "PASSENGER ALERT", 0x3498db, "carried"

    # --- Advanced Analysis ---
    highlights = []
    
    # Role approximation based on net worth (farm priority)
    approximated_role = "Unknown"
    if team_stats.get('players'):
        try:
            team_players_sorted_by_farm = sorted(team_stats['players'], key=lambda p: (p.get('last_hits', 0), p.get('denies', 0)), reverse=True)
            player_account_id = player_match_data.get('account_id')
            
            for i, player in enumerate(team_players_sorted_by_farm):
                if str(player.get('account_id')) == str(player_account_id):
                    position = i + 1
                    if position == 1:
                        approximated_role = "Carry"
                    elif position == 2:
                        approximated_role = "Midlaner"
                    elif position == 3:
                        approximated_role = "Offlaner"
                    else: # Position 4 and 5
                        approximated_role = "Support"
                    break
        except Exception as e:
            print(f"Error during role approximation: {e}")

    # Performance highlights
    if team_stats.get('players'):
        if player_match_data.get('gold_per_min', 0) >= max(p.get('gold_per_min', 0) for p in team_stats['players']):
            highlights.append("💰 Top GPM on team")
        if player_match_data.get('hero_damage', 0) >= max(p.get('hero_damage', 0) for p in team_stats['players']):
            highlights.append("💥 Top hero damage on team")
        if player_match_data.get('tower_damage', 0) > max(p.get('tower_damage', 0) for p in team_stats['players']):
            highlights.append("🗼 Top tower damage on team")
        if player_match_data.get('kills', 0) >= max(p.get('kills', 0) for p in team_stats['players']):
            highlights.append("🔪 Most kills on team")
    
    if team_stats.get('total_kills', 0) > 0:
        kill_participation = (kills + assists) / team_stats['total_kills']
        kill_participation = min(1.0, kill_participation) # Cap at 100%
        if kill_participation > 0.65:
            highlights.append(f"⚔️ Involved in {kill_participation:.0%} of team's kills")

    return {
        "status": base_status,
        "color": base_color,
        "msg_key": base_msg_key,
        "approximated_role": approximated_role,
        "highlights": highlights
    }

def calculate_team_metrics(players):
    """Calculates aggregate and average stats for a list of players."""
    metrics = {
        'total_kills': 0, 'total_gpm': 0, 'total_lh': 0, 'total_xpm': 0,
        'total_hero_damage': 0, 'avg_gpm': 0, 'avg_lh': 0, 'avg_xpm': 0,
        'avg_hero_damage': 0, 'players': players
    }
    
    player_count = len(players)
    if not players or player_count == 0:
        return metrics

    for p in players:
        metrics['total_kills'] += p.get('kills', 0)
        metrics['total_gpm'] += p.get('gold_per_min', 0)
        metrics['total_lh'] += p.get('last_hits', 0)
        metrics['total_xpm'] += p.get('xp_per_min', 0)
        metrics['total_hero_damage'] += p.get('hero_damage', 0)
    
    metrics['avg_gpm'] = metrics['total_gpm'] / player_count
    metrics['avg_lh'] = metrics['total_lh'] / player_count
    metrics['avg_xpm'] = metrics['total_xpm'] / player_count
    metrics['avg_hero_damage'] = metrics['total_hero_damage'] / player_count
    
    return metrics

async def create_match_embed(session: aiohttp.ClientSession, steam_id: str, discord_id: str, guild: discord.Guild, last_match_cache, hero_names, hero_image_keys, hero_roles, rank_names_map, member_names_map, messages_map, last_known_match_id=None):
    """
    Fetches the latest match for a user, processes it, and creates a Discord embed.
    Raises exceptions for API errors, rate limits, or no data.
    Returns the embed, an image file (if any), and the match ID on success.
    If last_known_match_id is provided and matches the latest match, returns None for embed/image.
    """
    recent_matches_url = f"https://api.opendota.com/api/players/{steam_id}/recentMatches"
    async with session.get(recent_matches_url, timeout=10) as r_match:
        if r_match.status == 429:
            raise RateLimitException("OpenDota API rate limit reached.")
        if r_match.status != 200:
            raise PlayerDataException(f"API Error (status {r_match.status})")
        m_data = await r_match.json()
        if not m_data:
            raise NoMatchesException("No recent matches found.")
    
    m_id = m_data[0]['match_id']

    # Optimization: Skip detailed fetch if match hasn't changed
    if last_known_match_id and str(m_id) == str(last_known_match_id):
        return None, None, m_id, None, None, None, None

    player_url = f"https://api.opendota.com/api/players/{steam_id}"
    p_data = {}
    async with session.get(player_url, timeout=10) as r_player:
        if r_player.status == 200:
            p_data = await r_player.json()

    player_match_data = None
    team_stats = {}
    enemy_team_stats = {}
    player_team = None

    async with session.get(f"https://api.opendota.com/api/matches/{m_id}", timeout=10) as r_detail:
        if r_detail.status == 200:
            d_data = await r_detail.json()

            # Find the player and their team first
            for p in d_data.get('players', []):
                if p.get('account_id') is not None and str(p.get('account_id')) == str(steam_id):
                    player_match_data = p
                    player_team = 'radiant' if p['player_slot'] < 128 else 'dire'
                    break
            
            if player_team:
                radiant_players = [p for p in d_data.get('players', []) if p['player_slot'] < 128]
                dire_players = [p for p in d_data.get('players', []) if p['player_slot'] >= 128]

                my_team_players = radiant_players if player_team == 'radiant' else dire_players
                enemy_team_players = dire_players if player_team == 'radiant' else radiant_players
                
                team_stats = calculate_team_metrics(my_team_players)
                enemy_team_stats = calculate_team_metrics(enemy_team_players)

    if not player_match_data:
         raise PlayerDataException("Could not find player's match data in detailed match info.")

    player_match_data['match_id'] = m_id
    player_match_data['radiant_win'] = d_data.get('radiant_win', False)

    hero_id = player_match_data.get('hero_id')
    if hero_id not in hero_names:
        print(f"WARNING: Unknown hero_id '{hero_id}' encountered.")

    won = (player_match_data.get('player_slot', 0) < 128) == player_match_data.get('radiant_win', False)
    h_name = hero_names.get(hero_id, "Unknown Hero")
    h_key = hero_image_keys.get(hero_id, "")
    kda = f"{player_match_data.get('kills', 0)}/{player_match_data.get('deaths', 0)}/{player_match_data.get('assists', 0)}"
    rank_str = get_rank_name(p_data, rank_names_map)
    h_xpm = player_match_data.get('xp_per_min', 0)
    h_gpm = player_match_data.get('gold_per_min', 0)
    
    result_str = "WON" if won else "LOST"
    match_summary = f"Last Game: {h_name}, {result_str}, {h_gpm} GPM, {h_xpm} XPM, KDA: {kda}"
    last_match_cache[str(discord_id)] = match_summary
    
    analysis = get_match_analysis(player_match_data, won, team_stats, enemy_team_stats, hero_roles, messages_map)
    messages_list = messages_map.get(analysis['msg_key'], ["Error: No messages found for this status."])
    flavor = random.choice(messages_list)

    friendly_name = member_names_map.get(str(discord_id), "Dota Player")
    member = guild.get_member(int(discord_id))
    if not member:
        try: member = await guild.fetch_member(int(discord_id))
        except: member = None
    mention_text = member.mention if member else f"**{friendly_name}**"

    embed = discord.Embed(title=f"🚨 {analysis['status']}", color=analysis['color'])
    embed.description = f"{mention_text} just played as **{h_name}**.\n**{flavor}**"
    
    # Set Steam Avatar and Name
    try:
        steam_profile = p_data.get('profile', {})
        steam_name = steam_profile.get('personaname', friendly_name)
        avatar_url = steam_profile.get('avatarfull')
        
        if avatar_url:
            embed.set_author(name=steam_name, icon_url=avatar_url, url=steam_profile.get('profileurl', ''))
        else:
            embed.set_author(name=steam_name)
    except Exception as e:
        print(f"Error setting author in embed: {e}")
        embed.set_author(name=friendly_name)

    image_file = None
    if h_key:
        image_path = f"images/{h_key}.png"
        if os.path.exists(image_path):
            try:
                image_file = discord.File(image_path, filename=f"{h_key}.png")
                embed.set_thumbnail(url=f"attachment://{h_key}.png")
            except Exception as e:
                print(f"ERROR: Failed to create discord.File for {image_path}: {e}")
        else:
            embed.set_thumbnail(url=f"https://api.opendota.com/apps/dota2/images/dota_react/heroes/{h_key}.png")

    embed.add_field(name="Result", value="🏆 WON" if won else "💀 LOST", inline=True)
    embed.add_field(name="KDA", value=f"`{kda}`", inline=True)
    embed.add_field(name="Approximated Role", value=analysis.get('approximated_role', 'N/A'), inline=True)
    embed.add_field(name="GPM / XPM", value=f"{h_gpm} / {h_xpm}", inline=True)
    embed.add_field(name="Current Rank", value=rank_str, inline=True)
    
    if analysis['highlights']:
        embed.add_field(name="📋 Match Highlights", value="\n".join(analysis['highlights']), inline=False)

    embed.add_field(
        name="Match Details", 
        value=f"[Dotabuff](https://www.dotabuff.com/matches/{m_id}) | [OpenDota](https://www.opendota.com/matches/{m_id})",
        inline=False
    )
    
    return embed, image_file, m_id, player_match_data, analysis, team_stats, enemy_team_stats
