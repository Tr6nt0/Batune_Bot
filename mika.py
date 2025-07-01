import discord
import re
import sqlite3
import csv
from datetime import datetime
from discord.ext import tasks

import CONFIG

intents = discord.Intents.default()
intents.message_content = True

conn = sqlite3.connect('fortunes.db')
cursor = conn.cursor()

client = discord.Client(intents=intents)

# Create fortunes table with index tracking
cursor.execute('''
    CREATE TABLE IF NOT EXISTS fortunes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fortune TEXT UNIQUE,
        used BOOLEAN DEFAULT 0
    )
''')
cursor.execute('CREATE TABLE IF NOT EXISTS current_index (idx INTEGER DEFAULT 0)')
conn.commit()

# Initialize index if not exists
cursor.execute('SELECT idx FROM current_index')
if not cursor.fetchone():
    cursor.execute('INSERT INTO current_index (idx) VALUES (0)')
    conn.commit()

def add_fortune(fortune):
    try:
        cursor.execute('INSERT INTO fortunes (fortune) VALUES (?)', [fortune])
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Duplicate fortune

def remove_fortune(fortune):
    cursor.execute('DELETE FROM fortunes WHERE fortune=?', [fortune])
    conn.commit()
    return cursor.rowcount > 0

def reset_fortunes():
    cursor.execute('UPDATE fortunes SET used=0')
    cursor.execute('UPDATE current_index SET idx=0')
    conn.commit()

def get_next_fortune():
    # Get current index
    cursor.execute('SELECT idx FROM current_index')
    current_idx = cursor.fetchone()[0]
    
    # Get next unused fortune
    cursor.execute('''
        SELECT id, fortune FROM fortunes 
        WHERE used=0 
        ORDER BY id ASC 
        LIMIT 1 OFFSET ?
    ''', [current_idx])
    result = cursor.fetchone()
    
    if result:
        fortune_id, fortune = result
        # Mark as used and update index
        cursor.execute('UPDATE fortunes SET used=1 WHERE id=?', [fortune_id])
        cursor.execute('UPDATE current_index SET idx=?', [current_idx + 1])
        conn.commit()
        return fortune
    
    # If no fortunes left, reset and start over
    reset_fortunes()
    return get_next_fortune()  # Recursive call to get first fortune

async def post_fortune():
    channel = client.get_channel(CONFIG.TARGET_CHANNEL)
    try:
        fotd = get_next_fortune()
        await channel.send('🌟 **Fortune of the Day:**\n' + fotd)
    except Exception as e:
        print(f"Error posting fortune: {e}")
        await channel.send('No fortunes available! Add some with `mika add <fortune>`')

@tasks.loop(seconds=60)
async def scheduled_task():
    now = datetime.utcnow()
    if now.hour == CONFIG.SCHEDULED_POST_HOUR and now.minute == CONFIG.SCHEDULED_POST_MINUTE:
        await post_fortune()

@client.event
async def on_ready():
    # Import fortunes from CSV on first run
    cursor.execute('SELECT COUNT(*) FROM fortunes')
    if cursor.fetchone()[0] == 0:
        try:
            with open('full_entries.csv', 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row:  # Skip empty lines
                        add_fortune(row[0].strip())
            print("Imported fortunes from full_entries.csv")
        except Exception as e:
            print(f"Error importing fortunes: {e}")
    
    print(f'{client.user} connected at {datetime.utcnow()}')
    await scheduled_task.start()

@client.event
async def on_message(message):
    # Fortune submission command
    if message.content.lower().startswith('mika add '):
        fortune = re.sub(r'^mika add\s+', '', message.content, flags=re.IGNORECASE)
        if add_fortune(fortune):
            await message.channel.send(f'✨ Fortune added: "{fortune}"')
        else:
            await message.channel.send(f'⚠️ Fortune already exists: "{fortune}"')
    
    # Test command
    if message.content.lower() == 'mika test' and message.author.guild_permissions.administrator:
        await post_fortune()
    
    # Admin say command
    if message.content.lower().startswith('mika say ') and message.author.guild_permissions.administrator:
        channel = client.get_channel(CONFIG.TARGET_CHANNEL)
        content = re.sub(r'^mika say\s+', '', message.content, flags=re.IGNORECASE)
        await channel.send(content)
    
    # Reset fortunes command
    if message.content.lower() == 'mika reset' and message.author.guild_permissions.administrator:
        reset_fortunes()
        await message.channel.send('🔄 All fortunes have been reset and will be reused!')
    
    # Remove fortune command
    if message.content.lower().startswith('mika remove ') and message.author.guild_permissions.administrator:
        fortune = re.sub(r'^mika remove\s+', '', message.content, flags=re.IGNORECASE)
        if remove_fortune(fortune):
            await message.channel.send(f'🗑️ Removed fortune: "{fortune}"')
        else:
            await message.channel.send(f'⚠️ Fortune not found: "{fortune}"')

client.run(CONFIG.DISCORD_TOKEN)
