import discord
import re
import sqlite3
import csv
import os
from datetime import datetime
from discord.ext import tasks

# Create CONFIG.py with your Discord token and channel settings
import CONFIG

intents = discord.Intents.default()
intents.message_content = True

conn = sqlite3.connect('fortunes.db')
cursor = conn.cursor()

client = discord.Client(intents=intents)

# Create fortunes table with Batune ID tracking
cursor.execute('''
    CREATE TABLE IF NOT EXISTS fortunes (
        batune_id INTEGER PRIMARY KEY,
        forecast TEXT UNIQUE,
        used BOOLEAN DEFAULT 0
    )
''')
cursor.execute('CREATE TABLE IF NOT EXISTS current_index (idx INTEGER DEFAULT 799)')  # Start at index 799
conn.commit()

# Initialize index if not exists
cursor.execute('SELECT idx FROM current_index')
if cursor.fetchone() is None:
    cursor.execute('INSERT INTO current_index (idx) VALUES (799)')
    conn.commit()

def import_fortunes():
    """Import fortunes from full_entries.csv on startup"""
    try:
        with open('full_entries.csv', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header row
            for row in reader:
                if len(row) >= 3:  # Ensure all columns exist
                    batune_id = int(row[0])
                    forecast = row[1].strip()
                    # direction = row[2]  # Not used but available
                    try:
                        cursor.execute('INSERT INTO fortunes (batune_id, forecast) VALUES (?, ?)', 
                                      (batune_id, forecast))
                    except sqlite3.IntegrityError:
                        pass  # Ignore duplicates
        conn.commit()
        return True
    except Exception as e:
        print(f"Error importing fortunes: {e}")
        return False

def add_fortune(forecast):
    """Add a new fortune to the database"""
    try:
        # Find the next available Batune ID
        cursor.execute('SELECT MAX(batune_id) FROM fortunes')
        max_id = cursor.fetchone()[0] or 0
        new_id = max_id + 1
        
        cursor.execute('INSERT INTO fortunes (batune_id, forecast) VALUES (?, ?)', 
                      (new_id, forecast))
        conn.commit()
        return new_id
    except sqlite3.IntegrityError:
        return False  # Duplicate fortune

def remove_fortune(batune_id):
    """Remove a fortune by Batune ID"""
    cursor.execute('DELETE FROM fortunes WHERE batune_id=?', [batune_id])
    conn.commit()
    return cursor.rowcount > 0

def reset_fortunes():
    """Mark all fortunes as unused and reset index to 0"""
    cursor.execute('UPDATE fortunes SET used=0')
    cursor.execute('UPDATE current_index SET idx=0')
    conn.commit()

def get_next_fortune():
    """Get the next fortune in sequence, resetting when all are used"""
    while True:
        # Get current index
        cursor.execute('SELECT idx FROM current_index')
        current_idx = cursor.fetchone()[0]
        
        # Get next unused fortune in Batune ID order
        cursor.execute('''
            SELECT batune_id, forecast FROM fortunes 
            WHERE used=0 
            ORDER BY batune_id ASC 
            LIMIT 1 OFFSET ?
        ''', [current_idx])
        result = cursor.fetchone()
        
        if result:
            batune_id, forecast = result
            # Mark as used and update index
            cursor.execute('UPDATE fortunes SET used=1 WHERE batune_id=?', [batune_id])
            cursor.execute('UPDATE current_index SET idx=?', [current_idx + 1])
            conn.commit()
            return (batune_id, forecast)
        
        # If no fortunes found at current index, reset and try again
        reset_fortunes()

async def post_fortune():
    channel = client.get_channel(CONFIG.TARGET_CHANNEL)
    try:
        batune_id, forecast = get_next_fortune()
        await channel.send(f'🌟 **Fortune #{batune_id}:**\n{forecast}')
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
        if import_fortunes():
            print("Imported fortunes from full_entries.csv")
        else:
            print("Error importing fortunes. Using empty database.")
    
    print(f'{client.user} connected at {datetime.utcnow()}')
    await scheduled_task.start()

@client.event
async def on_message(message):
    # Fortune submission command
    if message.content.lower().startswith('mika add '):
        forecast = re.sub(r'^mika add\s+', '', message.content, flags=re.IGNORECASE)
        new_id = add_fortune(forecast)
        if new_id:
            await message.channel.send(f'✨ Fortune #{new_id} added: "{forecast}"')
        else:
            await message.channel.send(f'⚠️ Fortune already exists: "{forecast}"')
    
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
        try:
            batune_id = int(re.sub(r'^mika remove\s+', '', message.content, flags=re.IGNORECASE))
            if remove_fortune(batune_id):
                await message.channel.send(f'🗑️ Removed fortune #{batune_id}')
            else:
                await message.channel.send(f'⚠️ Fortune #{batune_id} not found')
        except ValueError:
            await message.channel.send('❌ Please specify a valid Batune ID (e.g., `mika remove 42`)')
    
    # List fortunes command
    if message.content.lower() == 'mika list' and message.author.guild_permissions.administrator:
        cursor.execute('SELECT batune_id, forecast FROM fortunes ORDER BY batune_id ASC')
        fortunes = cursor.fetchall()
        
        if fortunes:
            response = "**Batune Fortunes:**\n" + "\n".join([f"{id}: {text}" for id, text in fortunes[:25]])
            if len(fortunes) > 25:
                response += f"\n...and {len(fortunes)-25} more"
            await message.channel.send(response)
        else:
            await message.channel.send("No fortunes in the database!")
    
    # Export command
    if message.content.lower() == 'mika export' and message.author.guild_permissions.administrator:
        cursor.execute('SELECT batune_id, forecast FROM fortunes ORDER BY batune_id ASC')
        fortunes = cursor.fetchall()
        
        if fortunes:
            with open('fortunes_export.csv', 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'forecast'])
                for batune_id, forecast in fortunes:
                    writer.writerow([batune_id, forecast])
            await message.channel.send('💾 Fortune database exported to `fortunes_export.csv`')
        else:
            await message.channel.send("No fortunes to export!")

client.run(CONFIG.DISCORD_TOKEN)
