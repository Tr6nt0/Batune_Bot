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

# Create tables
cursor.execute('''
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        forecast TEXT UNIQUE,
        source TEXT NOT NULL,             -- 'global' or 'guild'
        status TEXT DEFAULT 'pending',    -- 'pending', 'approved', 'rejected'
        submitted_by INTEGER,             -- User ID who submitted
        submitted_guild INTEGER,          -- Guild ID where submitted
        submitted_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS fortunes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_id INTEGER,             -- Original Batune ID for global fortunes
        guild_id INTEGER,                 -- Guild-specific ID for approved submissions
        forecast TEXT UNIQUE,
        used BOOLEAN DEFAULT 0,
        source TEXT NOT NULL,             -- 'global' or 'guild'
        approved_by INTEGER,              -- Admin who approved
        approved_time DATETIME,
        added_index INTEGER               -- Position in global queue
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS global_index (
        last_index INTEGER DEFAULT 799
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS guild_index (
        guild_id INTEGER PRIMARY KEY,
        last_index INTEGER DEFAULT 0
    )
''')
conn.commit()

# Initialize global index if not exists
cursor.execute('SELECT last_index FROM global_index')
if cursor.fetchone() is None:
    cursor.execute('INSERT INTO global_index (last_index) VALUES (799)')
    conn.commit()

def import_fortunes():
    """Import fortunes from full_entries.csv on startup"""
    try:
        with open('full_entries.csv', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header row
            for row in reader:
                if len(row) >= 2:
                    try:
                        original_id = int(row[0])
                        forecast = row[1].strip()
                        if forecast:
                            # Add directly to fortunes as pre-approved global
                            cursor.execute('''
                                INSERT INTO fortunes 
                                (original_id, forecast, source, added_index) 
                                VALUES (?, ?, 'global', ?)
                            ''', (original_id, forecast, original_id))
                    except (ValueError, IndexError, sqlite3.IntegrityError):
                        continue
        conn.commit()
        return True
    except Exception as e:
        print(f"Error importing fortunes: {e}")
        return False

def add_submission(forecast, user_id, guild_id=None):
    """Add a new fortune submission"""
    try:
        source = 'guild' if guild_id else 'global'
        cursor.execute('''
            INSERT INTO submissions 
            (forecast, source, submitted_by, submitted_guild) 
            VALUES (?, ?, ?, ?)
        ''', (forecast, source, user_id, guild_id))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None  # Duplicate fortune

def approve_submission(submission_id, approver_id):
    """Approve a submission and add to fortune queue"""
    try:
        # Get submission
        cursor.execute('''
            SELECT forecast, source, submitted_guild 
            FROM submissions 
            WHERE id=?
        ''', (submission_id,))
        submission = cursor.fetchone()
        
        if not submission:
            return False
            
        forecast, source, submitted_guild = submission
        
        # Add to fortunes with appropriate ID
        if source == 'global':
            # Get next global index
            cursor.execute('SELECT last_index FROM global_index')
            current_index = cursor.fetchone()[0]
            new_index = current_index + 1
            
            cursor.execute('''
                INSERT INTO fortunes 
                (forecast, source, approved_by, added_index) 
                VALUES (?, 'global', ?, ?)
            ''', (forecast, approver_id, new_index))
            
            # Update global index
            cursor.execute('UPDATE global_index SET last_index=?', (new_index,))
        else:
            # Guild submission
            # Get next guild ID for this guild
            cursor.execute('''
                SELECT last_index FROM guild_index 
                WHERE guild_id=?
            ''', (submitted_guild,))
            result = cursor.fetchone()
            guild_index = result[0] if result else 0
            new_guild_id = guild_index + 1
            
            cursor.execute('''
                INSERT INTO fortunes 
                (forecast, source, guild_id, approved_by, submitted_guild) 
                VALUES (?, 'guild', ?, ?, ?)
            ''', (forecast, new_guild_id, approver_id, submitted_guild))
            
            # Update guild index
            if result:
                cursor.execute('''
                    UPDATE guild_index 
                    SET last_index=? 
                    WHERE guild_id=?
                ''', (new_guild_id, submitted_guild))
            else:
                cursor.execute('''
                    INSERT INTO guild_index 
                    (guild_id, last_index) 
                    VALUES (?, ?)
                ''', (submitted_guild, new_guild_id))
        
        # Update submission status
        cursor.execute('''
            UPDATE submissions 
            SET status='approved' 
            WHERE id=?
        ''', (submission_id,))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Approval error: {e}")
        return False

def reject_submission(submission_id):
    """Reject a submission"""
    cursor.execute('''
        UPDATE submissions 
        SET status='rejected' 
        WHERE id=?
    ''', (submission_id,))
    conn.commit()
    return cursor.rowcount > 0

def get_next_fortune():
    """Get the next fortune to display"""
    # First check for approved guild submissions
    cursor.execute('''
        SELECT id, forecast, source, guild_id, submitted_guild 
        FROM fortunes 
        WHERE used=0 AND source='guild'
        ORDER BY approved_time ASC
        LIMIT 1
    ''')
    guild_fortune = cursor.fetchone()
    
    if guild_fortune:
        fortune_id, forecast, source, guild_id, submitted_guild = guild_fortune
        cursor.execute('UPDATE fortunes SET used=1 WHERE id=?', (fortune_id,))
        conn.commit()
        return {
            'id': fortune_id,
            'display_id': f"Guild-{submitted_guild}-{guild_id}",
            'forecast': forecast,
            'source': source
        }
    
    # Then check global fortunes
    cursor.execute('''
        SELECT id, forecast, added_index 
        FROM fortunes 
        WHERE used=0 AND source='global'
        ORDER BY added_index ASC
        LIMIT 1
    ''')
    global_fortune = cursor.fetchone()
    
    if global_fortune:
        fortune_id, forecast, added_index = global_fortune
        cursor.execute('UPDATE fortunes SET used=1 WHERE id=?', (fortune_id,))
        conn.commit()
        return {
            'id': fortune_id,
            'display_id': f"Global-{added_index}",
            'forecast': forecast,
            'source': 'global'
        }
    
    # If no fortunes, reset and try again
    cursor.execute('UPDATE fortunes SET used=0')
    conn.commit()
    return get_next_fortune()

async def post_fortune():
    channel = client.get_channel(CONFIG.TARGET_CHANNEL)
    try:
        fortune = get_next_fortune()
        if fortune['source'] == 'global':
            await channel.send(f'🌍 **Global Fortune #{fortune["display_id"].split("-")[-1]}:**\n{fortune["forecast"]}')
        else:
            parts = fortune['display_id'].split('-')
            await channel.send(f'🌟 **Fortune from Guild {parts[1]} (#{parts[2]}):**\n{fortune["forecast"]}')
    except Exception as e:
        print(f"Error posting fortune: {e}")
        await channel.send('Error posting fortune. Please try again.')

@tasks.loop(seconds=60)
async def scheduled_task():
    now = datetime.utcnow()
    if now.hour == CONFIG.SCHEDULED_POST_HOUR and now.minute == CONFIG.SCHEDULED_POST_MINUTE:
        await post_fortune()

@client.event
async def on_ready():
    # Initialize database on first run
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
    if message.author == client.user:
        return
        
    # Fortune submission command
    if message.content.lower().startswith('mika add '):
        forecast = re.sub(r'^mika add\s+', '', message.content, flags=re.IGNORECASE).strip()
        if not forecast:
            await message.channel.send('❌ Please provide a fortune to add!')
            return
            
        # Determine context
        guild_id = message.guild.id if message.guild else None
        submission_id = add_submission(forecast, message.author.id, guild_id)
        
        if submission_id:
            response = '✨ Fortune submitted for approval!'
            if guild_id:
                response += f'\nGuild ID: {guild_id}'
            await message.channel.send(response)
        else:
            await message.channel.send('⚠️ This fortune already exists or is invalid!')
    
    # Admin approval command
    if message.content.lower().startswith('mika approve ') and message.author.guild_permissions.administrator:
        try:
            submission_id = int(re.sub(r'^mika approve\s+', '', message.content, flags=re.IGNORECASE))
            if approve_submission(submission_id, message.author.id):
                await message.channel.send(f'✅ Approved submission #{submission_id}')
            else:
                await message.channel.send('⚠️ Approval failed. Submission may not exist.')
        except ValueError:
            await message.channel.send('❌ Please specify a valid submission ID')
    
    # Rejection command
    if message.content.lower().startswith('mika reject ') and message.author.guild_permissions.administrator:
        try:
            submission_id = int(re.sub(r'^mika reject\s+', '', message.content, flags=re.IGNORECASE))
            if reject_submission(submission_id):
                await message.channel.send(f'❌ Rejected submission #{submission_id}')
            else:
                await message.channel.send('⚠️ Rejection failed. Submission may not exist.')
        except ValueError:
            await message.channel.send('❌ Please specify a valid submission ID')
    
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
        cursor.execute('UPDATE fortunes SET used=0')
        conn.commit()
        await message.channel.send('🔄 All fortunes have been reset!')
    
    # List submissions command
    if message.content.lower() == 'mika submissions' and message.author.guild_permissions.administrator:
        cursor.execute('''
            SELECT id, forecast, status, source, submitted_guild 
            FROM submissions 
            ORDER BY submitted_time DESC
            LIMIT 25
        ''')
        submissions = cursor.fetchall()
        
        if submissions:
            response = "📝 **Recent Submissions:**\n"
            for sub in submissions:
                status_emoji = "⏳" if sub[2] == 'pending' else "✅" if sub[2] == 'approved' else "❌"
                guild_info = f" (Guild: {sub[4]})" if sub[4] else ""
                response += f"{sub[0]}: {status_emoji} [{sub[3]}{guild_info}] {sub[1][:50]}{'...' if len(sub[1]) > 50 else ''}\n"
            await message.channel.send(response)
        else:
            await message.channel.send("No submissions found!")
    
    # List fortunes command
    if message.content.lower() == 'mika fortunes' and message.author.guild_permissions.administrator:
        cursor.execute('''
            SELECT id, source, added_index, guild_id, submitted_guild, forecast 
            FROM fortunes 
            ORDER BY approved_time DESC
            LIMIT 25
        ''')
        fortunes = cursor.fetchall()
        
        if fortunes:
            response = "🔮 **Recent Fortunes:**\n"
            for f in fortunes:
                if f[1] == 'global':
                    ident = f"Global-{f[2]}"
                else:
                    ident = f"Guild-{f[4]}-{f[3]}"
                response += f"{f[0]}: {ident} - {f[5][:50]}{'...' if len(f[5]) > 50 else ''}\n"
            await message.channel.send(response)
        else:
            await message.channel.send("No fortunes found!")

client.run(CONFIG.DISCORD_TOKEN)
