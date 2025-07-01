import discord
import re
import sqlite3
import csv
from datetime import datetime
from discord.ext import tasks

# Create CONFIG.py with your Discord token and channel settings
import CONFIG

intents = discord.Intents.default()
intents.message_content = True

conn = sqlite3.connect('fortunes.db')
cursor = conn.cursor()

client = discord.Client(intents=intents)

# Create fortunes table with enhanced tracking
cursor.execute('''
    CREATE TABLE IF NOT EXISTS fortunes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        global_id INTEGER,               -- Original Batune ID for global fortunes
        guild_id INTEGER,                 -- Guild-specific ID for user submissions
        forecast TEXT UNIQUE,
        used BOOLEAN DEFAULT 0,
        source TEXT NOT NULL,             -- 'global' or 'guild'
        approved BOOLEAN DEFAULT 0,       -- Only for guild submissions
        origin_guild INTEGER,              -- Guild where submission was made
        added_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')
cursor.execute('CREATE TABLE IF NOT EXISTS current_index (idx INTEGER DEFAULT 0)')
conn.commit()

# Initialize index if not exists
cursor.execute('SELECT idx FROM current_index')
if cursor.fetchone() is None:
    cursor.execute('INSERT INTO current_index (idx) VALUES (0)')
    conn.commit()

def import_fortunes():
    """Import fortunes from full_entries.csv on startup"""
    try:
        with open('full_entries.csv', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header row
            for row in reader:
                # Ensure we have at least 2 columns (id and forecast)
                if len(row) >= 2:
                    try:
                        global_id = int(row[0])
                        forecast = row[1].strip()
                        # Only add if forecast is not empty
                        if forecast:
                            try:
                                cursor.execute('''
                                    INSERT INTO fortunes (global_id, forecast, source, approved) 
                                    VALUES (?, ?, 'global', 1)
                                ''', (global_id, forecast))
                            except sqlite3.IntegrityError:
                                # Ignore duplicates
                                pass
                    except (ValueError, IndexError):
                        # Skip rows with invalid IDs
                        continue
        conn.commit()
        return True
    except Exception as e:
        print(f"Error importing fortunes: {e}")
        return False

def add_fortune(forecast, origin_guild=None):
    """Add a new fortune to the database"""
    try:
        # Determine if it's a global or guild submission
        is_global = origin_guild is None
        
        # Get next ID based on type
        if is_global:
            # Get next global ID
            cursor.execute('SELECT MAX(global_id) FROM fortunes WHERE global_id IS NOT NULL')
            max_global_id = cursor.fetchone()[0] or 0
            new_global_id = max_global_id + 1
            new_guild_id = None
        else:
            # Get next guild ID for this specific guild
            cursor.execute('SELECT MAX(guild_id) FROM fortunes WHERE origin_guild=?', (origin_guild,))
            max_guild_id = cursor.fetchone()[0] or 0
            new_guild_id = max_guild_id + 1
            new_global_id = None
        
        # Determine source and approval status
        source = 'global' if is_global else 'guild'
        approved = 1 if is_global else 0  # Global submissions auto-approved
        
        cursor.execute('''
            INSERT INTO fortunes (global_id, guild_id, forecast, source, approved, origin_guild) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (new_global_id, new_guild_id, forecast, source, approved, origin_guild))
        conn.commit()
        return cursor.lastrowid  # Return the primary key ID
    except sqlite3.IntegrityError:
        return False  # Duplicate fortune

def remove_fortune(fortune_id):
    """Remove a fortune by primary key ID (only guild fortunes)"""
    cursor.execute('DELETE FROM fortunes WHERE id=? AND source="guild"', [fortune_id])
    conn.commit()
    return cursor.rowcount > 0

def reject_fortune(fortune_id):
    """Reject a guild-submitted fortune"""
    cursor.execute('DELETE FROM fortunes WHERE id=? AND source="guild"', [fortune_id])
    conn.commit()
    return cursor.rowcount > 0

def approve_fortune(fortune_id):
    """Approve a guild-submitted fortune"""
    cursor.execute('UPDATE fortunes SET approved=1 WHERE id=? AND source="guild"', [fortune_id])
    conn.commit()
    return cursor.rowcount > 0

def reset_fortunes():
    """Mark all fortunes as unused and reset index to 0"""
    cursor.execute('UPDATE fortunes SET used=0')
    cursor.execute('UPDATE current_index SET idx=0')
    conn.commit()

def get_next_fortune():
    """Get the next fortune in sequence with priority to approved guild submissions"""
    # Get current index
    cursor.execute('SELECT idx FROM current_index')
    current_idx = cursor.fetchone()[0]
    
    # First try to get approved guild-submitted fortunes
    cursor.execute('''
        SELECT id, forecast, source, global_id, guild_id 
        FROM fortunes 
        WHERE used=0 AND approved=1 AND source='guild'
        ORDER BY added_time ASC
        LIMIT 1
    ''')
    guild_fortune = cursor.fetchone()
    
    if guild_fortune:
        # Return guild-submitted fortune immediately
        fortune_id, forecast, source, global_id, guild_id = guild_fortune
        cursor.execute('UPDATE fortunes SET used=1 WHERE id=?', [fortune_id])
        conn.commit()
        return (fortune_id, forecast, source, global_id, guild_id)
    
    # If no guild submissions, get the next global fortune
    cursor.execute('''
        SELECT id, forecast, source, global_id, guild_id 
        FROM fortunes 
        WHERE used=0 AND source='global'
        ORDER BY global_id ASC 
        LIMIT 1 OFFSET ?
    ''', [current_idx])
    global_fortune = cursor.fetchone()
    
    if global_fortune:
        fortune_id, forecast, source, global_id, guild_id = global_fortune
        # Mark as used and update index
        cursor.execute('UPDATE fortunes SET used=1 WHERE id=?', [fortune_id])
        cursor.execute('UPDATE current_index SET idx=?', [current_idx + 1])
        conn.commit()
        return (fortune_id, forecast, source, global_id, guild_id)
    
    # If no fortunes left, reset and get the first one
    reset_fortunes()
    return get_next_fortune()  # Recursive call to get first fortune

async def post_fortune():
    channel = client.get_channel(CONFIG.TARGET_CHANNEL)
    try:
        fortune_id, forecast, source, global_id, guild_id = get_next_fortune()
        display_id = global_id if source == 'global' else guild_id
        source_tag = "🌟 Guild Fortune" if source == 'guild' else "🔮 Global Fortune"
        await channel.send(f'**{source_tag} #{display_id}:**\n{forecast}')
    except TypeError:
        await channel.send('No fortunes available! Add some with `mika add <fortune>`')
    except Exception as e:
        print(f"Error posting fortune: {e}")
        await channel.send('An error occurred while posting the fortune.')

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
    # Ignore messages from the bot itself
    if message.author == client.user:
        return
        
    # Fortune submission command
    if message.content.lower().startswith('mika add '):
        forecast = re.sub(r'^mika add\s+', '', message.content, flags=re.IGNORECASE).strip()
        if not forecast:
            await message.channel.send('❌ Please provide a fortune to add!')
            return
            
        # Determine if submission is global or guild-specific
        origin_guild = message.guild.id if message.guild else None
        fortune_id = add_fortune(forecast, origin_guild)
        
        if fortune_id:
            # Get the added fortune to determine its type
            cursor.execute('SELECT source, global_id, guild_id FROM fortunes WHERE id=?', (fortune_id,))
            result = cursor.fetchone()
            
            if result:
                source, global_id, guild_id = result
                display_id = global_id if source == 'global' else guild_id
                
                if source == 'global':
                    response = f'✨ Global Fortune #{display_id} added: "{forecast}"'
                else:
                    response = f'✨ Guild Fortune #{display_id} submitted for approval: "{forecast}"'
            else:
                response = f'✨ Fortune submitted: "{forecast}"'
            
            await message.channel.send(response)
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
    
    # Remove fortune command (only for guild fortunes)
    if message.content.lower().startswith('mika remove ') and message.author.guild_permissions.administrator:
        try:
            fortune_id = int(re.sub(r'^mika remove\s+', '', message.content, flags=re.IGNORECASE))
            if remove_fortune(fortune_id):
                await message.channel.send(f'🗑️ Removed fortune #{fortune_id}')
            else:
                await message.channel.send(f'⚠️ Fortune #{fortune_id} not found or is global')
        except ValueError:
            await message.channel.send('❌ Please specify a valid Fortune ID (e.g., `mika remove 42`)')
    
    # Approve fortune command
    if message.content.lower().startswith('mika approve ') and message.author.guild_permissions.administrator:
        try:
            fortune_id = int(re.sub(r'^mika approve\s+', '', message.content, flags=re.IGNORECASE))
            if approve_fortune(fortune_id):
                await message.channel.send(f'✅ Approved fortune #{fortune_id}')
            else:
                await message.channel.send(f'⚠️ Fortune #{fortune_id} not found, already approved, or is global')
        except ValueError:
            await message.channel.send('❌ Please specify a valid Fortune ID (e.g., `mika approve 42`)')
    
    # Reject fortune command
    if message.content.lower().startswith('mika reject ') and message.author.guild_permissions.administrator:
        try:
            fortune_id = int(re.sub(r'^mika reject\s+', '', message.content, flags=re.IGNORECASE))
            if reject_fortune(fortune_id):
                await message.channel.send(f'❌ Rejected fortune #{fortune_id}')
            else:
                await message.channel.send(f'⚠️ Fortune #{fortune_id} not found, already approved, or is global')
        except ValueError:
            await message.channel.send('❌ Please specify a valid Fortune ID (e.g., `mika reject 42`)')
    
    # List fortunes command
    if message.content.lower() == 'mika list' and message.author.guild_permissions.administrator:
        cursor.execute('''
            SELECT id, forecast, source, approved, global_id, guild_id 
            FROM fortunes 
            ORDER BY COALESCE(global_id, guild_id) ASC
        ''')
        fortunes = cursor.fetchall()
        
        if fortunes:
            # Format list with status indicators
            fortune_list = []
            for id, text, source, approved, global_id, guild_id in fortunes:
                display_id = global_id if source == 'global' else guild_id
                status = ""
                if source == 'guild':
                    status = " ✅" if approved else " ⏳"
                fortune_list.append(f"{id}: {'Global' if source == 'global' else 'Guild'} #{display_id} - {text}{status}")
            
            # Split into chunks to avoid Discord message limit
            chunks = [fortune_list[i:i + 10] for i in range(0, len(fortune_list), 10)]
            for i, chunk in enumerate(chunks):
                response = f"**Batune Fortunes (Part {i+1}):**\n" + "\n".join(chunk)
                await message.channel.send(response)
        else:
            await message.channel.send("No fortunes in the database!")
    
    # Pending approvals command
    if message.content.lower() == 'mika pending' and message.author.guild_permissions.administrator:
        cursor.execute('''
            SELECT id, forecast, guild_id 
            FROM fortunes 
            WHERE source='guild' AND approved=0
            ORDER BY added_time ASC
        ''')
        pending = cursor.fetchall()
        
        if pending:
            response = "⏳ **Pending Approvals:**\n" + "\n".join(
                [f"{id}: Guild #{guild_id} - {text}" for id, text, guild_id in pending]
            )
            await message.channel.send(response)
        else:
            await message.channel.send("No pending fortunes to approve!")
    
    # Export command
    if message.content.lower() == 'mika export' and message.author.guild_permissions.administrator:
        cursor.execute('''
            SELECT id, global_id, guild_id, forecast, source, approved, origin_guild 
            FROM fortunes 
            ORDER BY COALESCE(global_id, guild_id) ASC
        ''')
        fortunes = cursor.fetchall()
        
        if fortunes:
            with open('fortunes_export.csv', 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['management_id', 'global_id', 'guild_id', 'forecast', 'source', 'approved', 'origin_guild'])
                for row in fortunes:
                    writer.writerow(row)
            await message.channel.send('💾 Fortune database exported to `fortunes_export.csv`')
        else:
            await message.channel.send("No fortunes to export!")

client.run(CONFIG.DISCORD_TOKEN)
