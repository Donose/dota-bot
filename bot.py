import discord
from discord.ext import commands, tasks
import aiohttp
import json
import os
import asyncio
import random
import re
from typing import Optional
import sys

import config
import opendota

# --- Validate Configuration ---
if not config.validate():
    sys.exit(1)

# --- Load Data from Config ---
user_map = config.load_users()
MESSAGES = config.load_messages()
ROASTS = config.load_roasts()
SLANGS = config.load_slangs()

# --- Global Bot State ---
LAST_MATCH_CACHE = {}
CHAT_HISTORY = {}
DETAILED_LAST_MATCH_CACHE = {}
last_seen_matches = {}
HERO_NAMES = {}
HERO_IMAGE_KEYS = {}
HERO_LOOKUP = {}
from datetime import datetime, timedelta

# --- Global Bot State ---
LAST_MATCH_CACHE = {}
CHAT_HISTORY = {}
DETAILED_LAST_MATCH_CACHE = {}
last_seen_matches = {}
HERO_NAMES = {}
HERO_IMAGE_KEYS = {}
HERO_LOOKUP = {}
HERO_ROLES = {}
channel_message_counts = {}
channel_last_help_post_time = {}

# --- Bot Initialization ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')


@bot.command(name='help')
async def help_command(ctx):
    """Shows this help message."""
    embed = discord.Embed(
        title="Dota Bot Commands",
        description="Here are the available commands:",
        color=discord.Color.green()
    )
    embed.add_field(name="!help", value="Shows this message.", inline=False)
    embed.add_field(name="!register <steam_id>", value="Registers your Steam ID.", inline=False)
    embed.add_field(name="!last [mention]", value="Shows the last match of the registered user.", inline=False)
    embed.add_field(name="!check", value="Forces a scan for new matches for all registered users.", inline=False)
    embed.add_field(name="!random [position]", value="Suggests a random hero to play.", inline=False)
    embed.add_field(name="!status [mention]", value="Shows detailed stats for the last match.", inline=False)
    embed.add_field(name="!toxic [mention] [message]", value="Roasts the user using the toxic-dota model.", inline=False)
    embed.add_field(name="!vocal [sound_name]", value="Joins voice chat and plays a sound.", inline=False)
    embed.add_field(name="!sounds", value="Lists all available sound files.", inline=False)
    embed.add_field(name="Unknown Command", value="Insults you.", inline=False)

    await ctx.send(embed=embed)


@bot.command(name='sounds')
async def list_sounds(ctx):
    """Lists all available sound files."""
    sound_dir = "sounds"
    if not os.path.exists(sound_dir):
        await ctx.send("No sound directory found.")
        return

    files = [f.replace(".mp3", "") for f in os.listdir(sound_dir) if f != ".gitkeep"]
    if not files:
        await ctx.send("No sounds available.")
        return

    files.sort()
    sound_list = "\n".join(files)
    
    if len(sound_list) > 4000:
        sound_list = sound_list[:3997] + "..."

    embed = discord.Embed(
        title="🎵 Available Sounds",
        description=f"Use `!vocal <sound_name>` to play.\n\n{sound_list}",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)


@tasks.loop(hours=4)
async def send_reminder():
    """Sends a reminder message to the channel."""
    channel = bot.get_channel(config.CHANNEL_ID)
    if not channel:
        return
    await channel.send("Sometimes valve fucks up some shit service and OpenDota doesn't get the fucking game stats, chill, will come later. So wait for OpenDota to update, when a new match is there, i will see it and post it. Stop blaming me for this shit. Also if i restart i lose memory of last match so even though you just finished a game i will not treat it as a new game(you can still see it using !last) use !help for help...trash dog")

@bot.event
async def on_ready():
    """Called when the bot is ready and connected."""
    print(f'✅ Bot is online with Tips and AI Roasts.')
    await opendota.update_hero_data(HERO_NAMES, HERO_IMAGE_KEYS, HERO_LOOKUP, HERO_ROLES)
    check_for_new_matches.start()
    send_reminder.start()

    # Join specific voice channel
    try:
        voice_channel = bot.get_channel(1457514629281616058)
        if voice_channel:
            if not voice_channel.guild.voice_client:
                await voice_channel.connect()
                print(f"Joined voice channel: {voice_channel.name}")
            else:
                 # If already connected somewhere, maybe move? or just stay if it's the right one.
                 # For now, if connected, assume it's okay or handled elsewhere.
                 print("Already connected to a voice channel.")
        else:
            print("Voice channel 1457514629281616058 not found.")
    except Exception as e:
        print(f"Failed to join voice channel on ready: {e}")

@bot.event
async def on_message(message):
    """Called when a message is sent in a channel the bot can see."""
    if message.author == bot.user:
        return

    channel_id = message.channel.id
    
    # Initialize counters if not present
    if channel_id not in channel_message_counts:
        channel_message_counts[channel_id] = 0
    if channel_id not in channel_last_help_post_time:
        channel_last_help_post_time[channel_id] = None

    channel_message_counts[channel_id] += 1

    if channel_message_counts[channel_id] >= 50:
        now = datetime.utcnow()
        last_post_time = channel_last_help_post_time[channel_id]

        if last_post_time is None or (now - last_post_time) > timedelta(hours=1):
            # Reset counter and post help message
            channel_message_counts[channel_id] = 0
            channel_last_help_post_time[channel_id] = now
            
            ctx = await bot.get_context(message)
            await help_command(ctx)

    await bot.process_commands(message)


@tasks.loop(seconds=300)
async def check_for_new_matches():
    """Periodically checks for new matches for all registered users."""
    channel = bot.get_channel(config.CHANNEL_ID)
    if not channel: 
        return
    
    guild = channel.guild
    
    async with aiohttp.ClientSession() as session:
        for discord_id, steam_id in user_map.items():
            try:
                embed, image_file, m_id, player_match_data, analysis, _, _ = await opendota.create_match_embed(
                    session, steam_id, discord_id, guild, LAST_MATCH_CACHE,
                    HERO_NAMES, HERO_IMAGE_KEYS, HERO_ROLES, config.RANK_NAMES, 
                    config.MEMBER_NAMES, MESSAGES
                )
                
                if embed and m_id and last_seen_matches.get(steam_id) != m_id:
                    DETAILED_LAST_MATCH_CACHE[discord_id] = (player_match_data, analysis)
                    if steam_id not in last_seen_matches:
                        last_seen_matches[steam_id] = m_id
                        continue
                    
                    last_seen_matches[steam_id] = m_id
                    await channel.send(embed=embed, file=image_file)

            except opendota.RateLimitException:
                print("Rate limit reached during background check. Will try again later.")
                break 
            except (opendota.NoMatchesException, opendota.PlayerDataException) as e:
                print(f"Skipping user {steam_id} in background check: {e}")
                continue
            except Exception as e:
                print(f"Error in check_for_new_matches loop for {steam_id}: {e}")
                continue

# --- COMMANDS ---

@bot.command(name="check")
async def force_check(ctx):
    """Forces an immediate scan and posts the latest match for everyone."""
    await ctx.send("🔍 Checking for the latest matches for all players...")
    await ctx.send("I see so much feeding happening...")
    
    async with aiohttp.ClientSession() as session:
        for discord_id, steam_id in user_map.items():
            friendly_name = config.MEMBER_NAMES.get(str(discord_id), steam_id)
            try:
                embed, image_file, m_id, player_match_data, analysis, _, _ = await opendota.create_match_embed(
                    session, steam_id, discord_id, ctx.guild, LAST_MATCH_CACHE,
                    HERO_NAMES, HERO_IMAGE_KEYS, HERO_ROLES, config.RANK_NAMES, 
                    config.MEMBER_NAMES, MESSAGES
                )
                if embed:
                    DETAILED_LAST_MATCH_CACHE[discord_id] = (player_match_data, analysis)
                    await ctx.send(embed=embed, file=image_file)
            except opendota.RateLimitException:
                await ctx.send("🐌 OpenDota API rate limit reached. Go next.")
                break 
            except opendota.NoMatchesException:
                await ctx.send(f"No recent matches found for **{friendly_name}**, probably banned for to much feed.")
            except opendota.PlayerDataException as e:
                await ctx.send(f"Could not retrieve match data for **{friendly_name}**: {e}. Most likely feeding.")
            except Exception as e:
                await ctx.send(f"An unexpected error occurred for **{friendly_name}**. Probably feeding.")
                print(f"Error in !check for {steam_id}: {e}")

    await ctx.send("✅ Check complete.")

@bot.command()
async def last(ctx, member: discord.Member = None):
    """Show the most recent match and current rank for a registered user."""
    target = member if member else ctx.author
    steam_id = user_map.get(str(target.id))
    
    if not steam_id:
        await ctx.send("❌ Not registered. Use `!register <steam_id>` to register.")
        return

    await ctx.send(f"🔍 Looking up the last match for {target.display_name}...")

    async with aiohttp.ClientSession() as session:
        try:
            embed, image_file, _, player_match_data, analysis, _, _ = await opendota.create_match_embed(
                session, steam_id, str(target.id), ctx.guild, LAST_MATCH_CACHE,
                HERO_NAMES, HERO_IMAGE_KEYS, HERO_ROLES, config.RANK_NAMES, 
                config.MEMBER_NAMES, MESSAGES
            )
            if embed:
                DETAILED_LAST_MATCH_CACHE[str(target.id)] = (player_match_data, analysis)
                await ctx.send(embed=embed, file=image_file)
        except opendota.RateLimitException:
            await ctx.send("Even i have a limit. Go next, try again later. When you come back from feeding.")
        except opendota.NoMatchesException:
            await ctx.send(f"No recent matches found for **{target.display_name}**. But even if they were found, they probably fed.")
        except opendota.PlayerDataException as e:
            await ctx.send(f"Could not retrieve match data for **{target.display_name}**: {e} or probably feeding.")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred: {e} UNEXPECTED FEEDING.")
            print(f"Exception in !last: {repr(e)}")

@bot.command()
async def register(ctx, steam_id: str):
    """Register your Steam/OpenDota numeric id for automatic tracking."""
    user_map[str(ctx.author.id)] = steam_id
    try:
        with open(config.DATABASE_FILE, 'w') as f:
            json.dump(user_map, f, indent=2)
        await ctx.send(f"✅ Registered Feeder <@{ctx.author.id}> -> `{steam_id}`")
    except Exception as e:
        await ctx.send("Failed to write database.")
        print("Error writing users.json:", e)


ROASTS = config.load_roasts()
SLANGS = config.load_slangs()

def generate_roast(hero_name, player_match_data, analysis):
    """Generates a personalized roast based on the player's last match."""
    hero_roasts = ROASTS.get("hero_roasts", {})
    performance_roasts = ROASTS.get("performance_roasts", {})
    generic_roasts = ROASTS.get("generic_roasts", [])

    # Try to find a hero-specific roast
    if hero_name.lower() in hero_roasts:
        return random.choice(hero_roasts[hero_name.lower()])

    # Try to find a performance-based roast
    if player_match_data and analysis:
        kills = player_match_data.get('kills', 0)
        deaths = player_match_data.get('deaths', 0)
        gpm = player_match_data.get('gold_per_min', 0)

        if deaths > kills and deaths > 8:
            return random.choice(performance_roasts.get("feeder", generic_roasts))
        if gpm < 300:
            return random.choice(performance_roasts.get("low_gpm", generic_roasts))

    # Fallback to a generic roast
    return random.choice(generic_roasts).format(hero_name=f"**{hero_name}**")

@bot.command(name='random')
async def random_command(ctx, position: Optional[str] = None):
    """Suggests a random hero to play, with an optional position filter."""
    steam_id = user_map.get(str(ctx.author.id))
    if not steam_id:
        await ctx.send("❌ Not registered. Use `!register <steam_id>` to register.")
        return

    # Determine hero pool first
    hero_pool = list(HERO_NAMES.keys())
    if position:
        position = position.lower()
        role_map = {
            "carry": ["Carry"], "mid": ["Nuker", "Disabler", "Escape"],
            "offlane": ["Durable", "Initiator", "Disabler"], "support": ["Support"]
        }
        target_roles = role_map.get(position)
        if target_roles:
            filtered_pool = [hid for hid, roles in HERO_ROLES.items() if any(r in roles for r in target_roles)]
            if filtered_pool:
                hero_pool = filtered_pool
            else:
                await ctx.send(f"Couldn't find any heroes for position '{position}'. Just pick whatever and lose.")
                return
        else:
            await ctx.send("dumb motherfucker, use !random [position] dota 2 position not some wierd kink you might have.")
            return

    chosen_id = random.choice(hero_pool)
    h_name = HERO_NAMES.get(chosen_id, "Unknown Hero")
    h_key = HERO_IMAGE_KEYS.get(chosen_id, "")

    description = f"I suggest you play **{h_name}**."
    
    player_match_data, analysis = None, None
    # Try to get last match data for personalized message
    try:
        if str(ctx.author.id) in DETAILED_LAST_MATCH_CACHE:
            player_match_data, analysis = DETAILED_LAST_MATCH_CACHE[str(ctx.author.id)]
        else:
            async with aiohttp.ClientSession() as session:
                embed, image_file, m_id, player_match_data, analysis, _, _ = await opendota.create_match_embed(
                    session, steam_id, str(ctx.author.id), ctx.guild, LAST_MATCH_CACHE,
                    HERO_NAMES, HERO_IMAGE_KEYS, HERO_ROLES, config.RANK_NAMES,
                    config.MEMBER_NAMES, MESSAGES
                )
                DETAILED_LAST_MATCH_CACHE[str(ctx.author.id)] = (player_match_data, analysis)
        
        # Personalized message
        kills = player_match_data.get('kills', 0)
        deaths = player_match_data.get('deaths', 0)
        last_role = analysis.get('approximated_role', 'Unknown')

        performance_comment = ""
        if deaths > kills and deaths > 8:
            performance_comment = f"Since you fed your ass off last game as {last_role} ({kills}/{deaths}), maybe try not to feed with this one."
        elif kills > deaths and kills > 10:
            performance_comment = f"You popped off last game as {last_role} ({kills}/{deaths}), so let's see if you can do it again."
        else:
            performance_comment = f"Your last game as {last_role} was whatever ({kills}/{deaths}). Let's see what you can do."

        role_transition_comment = ""
        if position and last_role != "Unknown" and position.capitalize() not in last_role:
            role_transition_comment = random.choice(ROASTS["role_transition_comments"]).format(last_role=last_role, position=position)
        
        description += f"\n\n{performance_comment}\n{role_transition_comment}"

    except opendota.NoMatchesException:
        description += "\n\nI couldn't find any recent matches for you, so I can't flame you properly. Just try not to feed."
    except Exception as e:
        print(f"Exception in !random_command (data fetch): {repr(e)}")
        description += "\n\nI couldn't fetch your last match data, probably because you're a coward."

    # Add a random roast
    roast = generate_roast(h_name, player_match_data, analysis)
    description += f"\n\n{roast}"

    # Embed
    embed = discord.Embed(title="🎲 Your Random Hero", color=0x00ff00)
    embed.description = description

    image_file = None
    if h_key:
        image_path = f"images/{h_key}.png"
        if os.path.exists(image_path):
            image_file = discord.File(image_path, filename=f"{h_key}.png")
            embed.set_thumbnail(url=f"attachment://{h_key}.png")

    await ctx.send(embed=embed, file=image_file)

@bot.command()
async def status(ctx, member: discord.Member = None):
    """Shows detailed stats for the last match."""
    target = member if member else ctx.author
    steam_id = user_map.get(str(target.id))

    if not steam_id:
        await ctx.send("❌ Not registered. Use `!register <steam_id>` to register.")
        return

    await ctx.send(f"🔍 Looking up the last match for {target.display_name}...")

    async with aiohttp.ClientSession() as session:
        try:
            _, image_file, _, player_match_data, analysis, team_stats, enemy_team_stats = await opendota.create_match_embed(
                session, steam_id, str(target.id), ctx.guild, LAST_MATCH_CACHE,
                HERO_NAMES, HERO_IMAGE_KEYS, HERO_ROLES, config.RANK_NAMES,
                config.MEMBER_NAMES, MESSAGES
            )

            hero_id = player_match_data.get('hero_id')
            h_name = HERO_NAMES.get(hero_id, "Unknown Hero")
            h_key = HERO_IMAGE_KEYS.get(hero_id, "")
            won = (player_match_data.get('player_slot', 0) < 128) == player_match_data.get('radiant_win', False)
            
            embed = discord.Embed(
                title=f"📊 Match Status for {target.display_name} as {h_name}",
                color=discord.Color.blue()
            )

            # Re-create image file for this embed since we can't reuse the one from create_match_embed easily 
            # if we are discarding the original embed (which might have closed the file handle or we want to be safe)
            # Actually, create_match_embed returns a fresh file object we haven't used yet, so we can use it.
            # But we need to set the thumbnail url to attachment://...
            
            if h_key:
                image_path = f"images/{h_key}.png"
                if os.path.exists(image_path):
                     # If create_match_embed returned a file, we can use it, but we need to match the filename
                     # Let's just trust create_match_embed returned a valid file or None
                     if image_file:
                         embed.set_thumbnail(url=f"attachment://{image_file.filename}")
                else:
                    embed.set_thumbnail(url=f"https://api.opendota.com/apps/dota2/images/dota_react/heroes/{h_key}.png")

            kda = f"{player_match_data.get('kills', 0)}/{player_match_data.get('deaths', 0)}/{player_match_data.get('assists', 0)}"
            gpm = player_match_data.get('gold_per_min', 0)
            xpm = player_match_data.get('xp_per_min', 0)
            lh = player_match_data.get('last_hits', 0)
            hd = player_match_data.get('hero_damage', 0)
            td = player_match_data.get('tower_damage', 0)

            embed.add_field(name="Result", value="🏆 WON" if won else "💀 LOST", inline=True)
            embed.add_field(name="KDA", value=f"`{kda}`", inline=True)
            embed.add_field(name="Approximated Role", value=analysis.get('approximated_role', 'N/A'), inline=True)

            # Comparative Analysis
            if team_stats and enemy_team_stats and team_stats.get('players') and enemy_team_stats.get('players'):
                all_players = team_stats['players'] + enemy_team_stats['players']
                
                def get_rank_and_top(key, reverse=True):
                    # Sort players by the key (descending for most stats)
                    sorted_players = sorted(all_players, key=lambda x: x.get(key, 0), reverse=reverse)
                    
                    # Find user's rank
                    rank = -1
                    user_val = player_match_data.get(key, 0)
                    for i, p in enumerate(sorted_players):
                        if p.get('player_slot') == player_match_data.get('player_slot'):
                            rank = i + 1
                            break
                    
                    # Find top player details
                    top_player = sorted_players[0]
                    top_val = top_player.get(key, 0)
                    top_hero_id = top_player.get('hero_id')
                    top_hero_name = HERO_NAMES.get(top_hero_id, "Unknown")
                    
                    return rank, top_val, top_hero_name

                # Calculate Ranks
                gpm_rank, top_gpm, top_gpm_hero = get_rank_and_top('gold_per_min')
                xpm_rank, top_xpm, top_xpm_hero = get_rank_and_top('xp_per_min')
                hd_rank, top_hd, top_hd_hero = get_rank_and_top('hero_damage')
                td_rank, top_td, top_td_hero = get_rank_and_top('tower_damage')
                lh_rank, top_lh, top_lh_hero = get_rank_and_top('last_hits')
                assists_rank, top_assists, top_assists_hero = get_rank_and_top('assists')
                # For deaths, lower is better, so reverse=False
                deaths_rank, top_deaths, top_deaths_hero = get_rank_and_top('deaths', reverse=False)
                
                # Calculate Grade based on Role
                role = analysis.get('approximated_role', 'Unknown')
                
                if role in ["Carry", "Midlaner"]:
                    ranks_to_avg = [gpm_rank, xpm_rank, hd_rank, td_rank, lh_rank]
                elif role == "Offlaner":
                    # Offlaners care about impact (HD, TD, Assists) and farm (XPM, GPM)
                    ranks_to_avg = [xpm_rank, hd_rank, td_rank, gpm_rank, assists_rank]
                elif role == "Support":
                    # Supports care about Assists, Survival (Deaths), Impact (HD), and Level (XPM)
                    # We ignore GPM/LH/TD as they are not primary support jobs
                    ranks_to_avg = [assists_rank, deaths_rank, hd_rank, xpm_rank]
                else:
                    # Default / Unknown
                    ranks_to_avg = [gpm_rank, xpm_rank, hd_rank, td_rank, lh_rank]

                avg_rank = sum(ranks_to_avg) / len(ranks_to_avg)
                
                grade = "F"
                if avg_rank <= 2.0: grade = "S+"
                elif avg_rank <= 3.0: grade = "S"
                elif avg_rank <= 4.0: grade = "A"
                elif avg_rank <= 5.5: grade = "B"
                elif avg_rank <= 7.0: grade = "C"
                elif avg_rank <= 8.5: grade = "D"
                
                embed.add_field(name="🏆 Match Grade", value=f"**{grade}** (Avg Rank: #{avg_rank:.1f}/10)", inline=False)

                def format_stat(val, rank, top_val, top_hero):
                    if rank == 1:
                        return f"**{val}**\n🥇 Match Leader!"
                    return f"**{val}**\nRank #{rank}\n(Top: {top_val} by {top_hero})"

                embed.add_field(name="GPM", value=format_stat(gpm, gpm_rank, top_gpm, top_gpm_hero), inline=True)
                embed.add_field(name="XPM", value=format_stat(xpm, xpm_rank, top_xpm, top_xpm_hero), inline=True)
                embed.add_field(name="Hero Damage", value=format_stat(hd, hd_rank, top_hd, top_hd_hero), inline=True)
                embed.add_field(name="Tower Damage", value=format_stat(td, td_rank, top_td, top_td_hero), inline=True)
                embed.add_field(name="Last Hits", value=format_stat(lh, lh_rank, top_lh, top_lh_hero), inline=True)
                embed.add_field(name="\u200b", value="\u200b", inline=True) # Spacer for alignment

            else:
                # Fallback if detailed stats fail
                embed.add_field(
                    name="Performance",
                    value=f"**GPM:** {gpm}\n"
                          f"**XPM:** {xpm}\n"
                          f"**Last Hits:** {lh}\n"
                          f"**Hero Damage:** {hd}\n"
                          f"**Tower Damage:** {td}",
                    inline=False
                )

            if analysis['highlights']:
                embed.add_field(name="📋 Match Highlights", value="\n".join(analysis['highlights']), inline=False)

            await ctx.send(embed=embed, file=image_file)

        except opendota.NoMatchesException:
            await ctx.send(f"No recent matches found for **{target.display_name}**.")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred: {e}")
            print(f"Exception in !status: {repr(e)}")

@bot.command()
async def toxic(ctx, member: Optional[discord.Member] = None, *, message: str = ""):
    """Roasts the user using the toxic-dota model."""
    async with ctx.typing():
        url = "http://host.docker.internal:11434/api/generate"
        target = member or (ctx.message.mentions[0] if ctx.message.mentions else ctx.author)
        user_id = str(target.id)
        stats = LAST_MATCH_CACHE.get(user_id, "Player is a coward with no data")

        channel_id = str(ctx.channel.id)
        if channel_id not in CHAT_HISTORY:
            CHAT_HISTORY[channel_id] = []
        history_text = "\n".join(CHAT_HISTORY[channel_id])
      
        rich_prompt = (f"Context: {stats}\nHistory: {history_text}\nPlayer said: {message}\nInsult:")
        payload = {
            "model": "toxic-dota", "prompt": rich_prompt, "stream": False,
            "options": {
                "num_predict": 60, "temperature": 1.5, "repeat_penalty": 1.4,
                "num_ctx": 2048, "stop": ["MESSAGE:", "RECENT_HISTORY:", "User:", "FLAME:", "TARGET_STATS:"]
            }
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        raw_roast = data['response'].strip()
                        clean_roast = raw_roast.split('\n')[0] 
                        sentences = re.split(r'(?<=[.!?]) +', clean_roast)
                        final_roast = " ".join(sentences[:2]).strip()
                        final_roast = re.sub(r'\(.*\)', '', final_roast) 
                        await ctx.send(f"{target.mention} {final_roast}")
                    else:
                        await ctx.send("Server diff, I'm lagging pizdec.")
            except Exception as e:
                print(f"Error: {e}")
                await ctx.send("Ollama is offline. Go next game raki.")

@bot.command()
async def vocal(ctx, *, sound_name: Optional[str] = None):
    """Joins voice chat and plays a sound from the sound server."""
    if not ctx.author.voice:
        await ctx.send("You are not in a voice channel, dumbass.")
        return

    channel = ctx.author.voice.channel
    
    sound_dir = "sounds"
    if not os.path.exists(sound_dir):
        await ctx.send("No sound server found.")
        return
        
    files = [f for f in os.listdir(sound_dir) if f != ".gitkeep"]
    if not files:
        await ctx.send("The sound server is empty. Upload some sounds.")
        return

    selected_file = None
    if sound_name:
        search = sound_name.lower()
        matches = [f for f in files if search in f.lower()]
        
        if matches:
            # Prioritize exact match (ignoring extension)
            exact_matches = [f for f in matches if os.path.splitext(f)[0].lower() == search]
            if exact_matches:
                selected_file = exact_matches[0]
            else:
                selected_file = matches[0]
        else:
            await ctx.send(f"Couldn't find sound '{sound_name}'.")
            return
    else:
        selected_file = random.choice(files)

    file_path = os.path.join(sound_dir, selected_file)

    try:
        voice_client = ctx.voice_client
        if not voice_client:
             if ctx.author.voice:
                 voice_client = await channel.connect()
             else:
                 await ctx.send("Neither you nor I are in a voice channel.")
                 return
        elif voice_client.channel != channel:
             await voice_client.move_to(channel)

        if voice_client.is_playing():
            voice_client.stop()

        # using ffmpeg filter to lower volume
        source = discord.FFmpegPCMAudio(file_path, options='-filter:a "volume=0.4"')
        voice_client.play(source)
        await ctx.send(f"🔊 Playing `{selected_file.replace('.mp3', '')}`")
        
    except Exception as e:
        await ctx.send(f"Failed to play sound: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    """
    Event listener that triggers when a member's voice state changes.
    Plays a random greeting when a user joins the bot's channel.
    """
    if member.bot:
        return

    # Check if user joined a channel or moved to a new one
    if after.channel is not None and before.channel != after.channel:
        voice_client = member.guild.voice_client
        
        # If bot is connected and the user joined the bot's channel
        if voice_client and voice_client.channel == after.channel:
            greetings_dir = "greetings"
            if os.path.exists(greetings_dir):
                # Get all files, ignoring hidden ones
                files = [f for f in os.listdir(greetings_dir) 
                        if os.path.isfile(os.path.join(greetings_dir, f)) and not f.startswith('.')]
                
                print(f"DEBUG: Found greeting files: {files}")

                if files:
                    selected_file = random.SystemRandom().choice(files)
                    file_path = os.path.join(greetings_dir, selected_file)
                    
                    try:
                        # Wait 1 second before playing greeting
                        await asyncio.sleep(1)

                        if voice_client.is_playing():
                            voice_client.stop()
                            
                        # using ffmpeg filter to lower volume
                        source = discord.FFmpegPCMAudio(file_path, options='-filter:a "volume=0.5"')
                        voice_client.play(source)
                        print(f"Played greeting {selected_file} for {member.display_name}")
                    except Exception as e:
                        print(f"Failed to play greeting: {e}")

@bot.event
async def on_command_error(ctx, error):
    """Handles errors, specifically for unregistered commands."""
    if isinstance(error, commands.CommandNotFound):
        if SLANGS:
            await ctx.send(random.choice(SLANGS))
    else:
        print(f"An unhandled error occurred: {error}")

# --- Run Bot ---
if __name__ == "__main__":
    bot.run(config.TOKEN)
