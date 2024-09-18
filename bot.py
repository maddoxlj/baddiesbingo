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
DISCORD_TOKEN = 'MTI4NDkxNjUyNjg0NzM2NTIxMA.GGC4xx.F28StS9LOCxnd0GkwteVhNX_6HOTlALBb25ERA'#os.environ.get('DISCORD_TOKEN')
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable not set.")

# Redis configuration
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

@tasks.loop(seconds=10)
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
            mention = f'<@{player_id}>'
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