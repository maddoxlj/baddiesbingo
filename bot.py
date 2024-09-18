import discord
import asyncio
import os
from discord.ext import tasks
import redis

# Define intents and create an instance of a client with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

# Discord token from environment variables
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable not set.")

# Redis configuration
redis_url = os.environ.get('REDIS_URL')
if not redis_url:
    raise ValueError("REDIS_URL environment variable not set.")

redis_client = redis.from_url(redis_url)

@tasks.loop(seconds=4)
async def process_bingo_queue():
    print("Processing queue...")
    while True:
        try:
            # Pop an item from the Redis list
            item = redis_client.lpop('bingo_queue')
            if item:
                player_name, message = item.decode('utf-8').split('|', 1)
                print(f"Processing queue item: {player_name} - {message}")
                await send_message_to_discord(player_name, message)
            else:
                # No more items to process
                await asyncio.sleep(5)  # Avoid busy-waiting
        except Exception as e:
            print(f"Error processing queue item: {e}")

async def send_message_to_discord(player_name, message):
    channel = find_channel_with_permissions()
    if channel:
        player_id = await get_member_id(channel.guild, player_name)
        if player_id:
            # Use Redis to check if player has been mentioned
            player_key = f"mentioned_player_{player_id}"
            has_been_mentioned = redis_client.get(player_key)
            if has_been_mentioned:
                mention = ""  # No mention if already mentioned
            else:
                mention = f'<@{player_id}>'
                redis_client.setex(player_key, 3600, "1")  # Set key with 1 hour expiration
            await channel.send(f'{mention} {message}')
            print(f"Message sent to channel {channel.id}: {mention} {message}")
        else:
            print(f"Player '{player_name}' not found in the server.")
    else:
        print("No suitable channel found for sending the message.")

def find_channel_with_permissions():
    for guild in client.guilds:
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

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    process_bingo_queue.start()

if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
