import discord
from discord.ext import commands
import random
from typing import Optional
import aiohttp
import os

import opendota
from config import load_users

user_map = load_users()
HERO_NAMES = {}
HERO_IMAGE_KEYS = {}
HERO_LOOKUP = {}
HERO_ROLES = {}
DETAILED_LAST_MATCH_CACHE = {}


async def setup_random_command(bot):
    await opendota.update_hero_data(HERO_NAMES, HERO_IMAGE_KEYS, HERO_LOOKUP, HERO_ROLES)

    @bot.command(name='random_hero')
    async def random_hero(ctx, position: Optional[str] = None):
        """Suggests a random hero based on last match performance and role."""
        steam_id = user_map.get(str(ctx.author.id))
        if not steam_id:
            await ctx.send("❌ Not registered. Use `!register <steam_id>` to register.")
            return

        async with aiohttp.ClientSession() as session:
            try:
                # Fetch last match data if not in cache
                if str(ctx.author.id) not in DETAILED_LAST_MATCH_CACHE:
                    await ctx.send(f"🔍 No cached data found for {ctx.author.display_name}. Fetching last match...")
                    _, _, _, player_match_data, analysis = await opendota.create_match_embed(
                        session, steam_id, str(ctx.author.id), ctx.guild, {},
                        HERO_NAMES, HERO_IMAGE_KEYS, HERO_ROLES, {}, {}, {}
                    )
                    DETAILED_LAST_MATCH_CACHE[str(ctx.author.id)] = (player_match_data, analysis)
                
                player_match_data, analysis = DETAILED_LAST_MATCH_CACHE[str(ctx.author.id)]

                # Determine hero pool
                hero_pool = list(HERO_NAMES.keys())
                if position:
                    position = position.lower()
                    role_map = {
                        "carry": ["Carry"],
                        "mid": ["Nuker", "Disabler", "Escape"],
                        "offlane": ["Durable", "Initiator", "Disabler"],
                        "support": ["Support"]
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
                    role_transition_comment = f"Going from {last_role} to {position} is a big jump, don't fuck it up."

                # Embed
                embed = discord.Embed(title="🎲 Your Random Hero", color=0x00ff00)
                embed.description = f"I suggest you play **{h_name}**.\n\n{performance_comment}\n{role_transition_comment}"

                image_file = None
                if h_key:
                    image_path = f"images/{h_key}.png"
                    if os.path.exists(image_path):
                        image_file = discord.File(image_path, filename=f"{h_key}.png")
                        embed.set_thumbnail(url=f"attachment://{h_key}.png")

                await ctx.send(embed=embed, file=image_file)

            except opendota.NoMatchesException:
                await ctx.send(f"No recent matches found for **{ctx.author.display_name}**. Go play a game, you bum.")
            except Exception as e:
                await ctx.send(f"An unexpected error occurred: {e}")
                print(f"Exception in !random_hero: {repr(e)}")

    print("✅ Random hero command loaded.")
