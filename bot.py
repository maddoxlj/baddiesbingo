import discord
import os
import asyncio
import redis
from discord.ext import commands, tasks

# Define intents and create an instance of a client with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='==', intents=intents)

# Discord token and Redis configuration from environment variables
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable not set.")

redis_url = os.environ.get('REDIS_URL')
if not redis_url:
    raise ValueError("REDIS_URL environment variable not set.")

redis_client = redis.from_url(redis_url)
mentioned_players_key = 'mentioned_players'

@tasks.loop(seconds=4)
async def process_bingo_queue():
    print("Processing queue...")
    while True:
        try:
            item = redis_client.lpop('bingo_queue')
            if item:
                player_name, message = item.decode('utf-8').split('|', 1)
                print(f"Processing queue item: {player_name} - {message}")
                await send_message_to_discord(player_name, message)
            else:
                await asyncio.sleep(5)
        except Exception as e:
            print(f"Error processing queue item: {e}")

async def send_message_to_discord(player_name, message):
    channel = find_channel_with_permissions()
    if channel:
        player_id = await get_member_id(channel.guild, player_name)
        if player_id:
            mention = f'<@{player_id}>'
            if redis_client.sismember(mentioned_players_key, player_id):
                print(f"Player '{player_name}' has already been mentioned. Skipping message.")
                return
            else:
                redis_client.sadd(mentioned_players_key, player_id)
            await channel.send(f'{mention} {message}')
            print(f"Message sent to channel {channel.id}: {mention} {message}")
        else:
            print(f"Player '{player_name}' not found in the server.")
    else:
        print("No suitable channel found for sending the message.")

def find_channel_with_permissions():
    for guild in bot.guilds:
        for channel in guild.text_channels:
            permissions = channel.permissions_for(guild.me)
            if permissions.send_messages:
                return channel
    return None

async def get_member_id(guild, player_name):
    for member in guild.members:
        if player_name and (player_name.lower() == member.name.lower() or player_name.lower() == member.display_name.lower()):
            return member.id
    return None

@tasks.loop(minutes=1)
async def reset_mentioned_players():
    print("Resetting mentioned players list...")
    redis_client.delete(mentioned_players_key)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    process_bingo_queue.start()
    reset_mentioned_players.start()

@bot.command()
async def upload_bingo_items(ctx):
    """Command to upload bingo items from a .txt file."""
    if len(ctx.message.attachments) == 0:
        await ctx.send("Please attach a .txt file with bingo items.")
        return

    attachment = ctx.message.attachments[0]
    if not attachment.filename.endswith('.txt'):
        await ctx.send("Please attach a .txt file.")
        return

    file_content = await attachment.read()
    with open('bingo_items.txt', 'wb') as file:
        file.write(file_content)
    
    await ctx.send("Bingo items have been updated.")

bot.run(DISCORD_TOKEN)
