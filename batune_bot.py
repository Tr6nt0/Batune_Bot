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

# Create tables
cursor.execute('''
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        forecast TEXT UNIQUE,
        source TEXT NOT NULL,             -- 'guild' or 'global'
        status TEXT DEFAULT 'pending',    -- 'pending', 'approved', 'rejected'
        submitted_by INTEGER,             -- User ID who submitted
        submitted_guild INTEGER,          -- Guild ID where submitted
        submitted_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS fortunes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batune_id INTEGER UNIQUE,         -- Original Batune ID (1-799)
        guild_id INTEGER,                 -- Guild-specific ID
        global_id INTEGER,                -- Global submission ID (800+)
        forecast TEXT UNIQUE,
        used BOOLEAN DEFAULT 0,
        source TEXT NOT NULL,             -- 'batune', 'guild', or 'global'
        approved_by INTEGER,              -- Admin who approved
        approved_time DATETIME
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS queue_state (
        batune_index INTEGER DEFAULT 0    -- Position in Batune queue
    )
''')

# Initialize queue state if not exists
cursor.execute('SELECT batune_index FROM queue_state')
if cursor.fetchone() is None:
    cursor.execute('INSERT INTO queue_state (batune_index) VALUES (0)')
    conn.commit()

def import_fortunes():
    """Import original Batune fortunes from full_entries.csv on startup"""
    try:
        with open('full_entries.csv', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header row
            for row in reader:
                if len(row) >= 2:
                    try:
                        batune_id = int(row[0])
                        forecast = row[1].strip()
                        if forecast:
                            # Add directly to fortunes as Batune fortune
                            cursor.execute('''
                                INSERT INTO fortunes 
                                (batune_id, forecast, source) 
                                VALUES (?, ?, 'batune')
                            ''', (batune_id, forecast))
                    except (ValueError, IndexError, sqlite3.IntegrityError):
                        continue
        conn.commit()
        return True
    except Exception as e:
        print(f"Error importing Batune fortunes: {e}")
        return False

def add_submission(forecast, user_id, guild_id=None):
    """Add a new fortune submission"""
    try:
        # Determine source based on context
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
        if source == 'guild':
            # Get next guild ID for this guild
            cursor.execute('''
                SELECT COALESCE(MAX(guild_id), 0) FROM fortunes 
                WHERE submitted_guild=?
            ''', (submitted_guild,))
            max_guild_id = cursor.fetchone()[0] or 0
            new_guild_id = max_guild_id + 1
            
            cursor.execute('''
                INSERT INTO fortunes 
                (guild_id, forecast, source, submitted_guild, approved_by) 
                VALUES (?, ?, 'guild', ?, ?)
            ''', (new_guild_id, forecast, submitted_guild, approver_id))
        else:
            # Global submission
            cursor.execute('''
                SELECT COALESCE(MAX(global_id), 799) FROM fortunes 
                WHERE source='global'
            ''')
            max_global_id = cursor.fetchone()[0] or 799
            new_global_id = max_global_id + 1
            
            cursor.execute('''
                INSERT INTO fortunes 
                (global_id, forecast, source, approved_by) 
                VALUES (?, ?, 'global', ?)
            ''', (new_global_id, forecast, approver_id))
        
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
    """Get the next fortune to display with proper priority"""
    # 1. First try to get an approved guild submission
    cursor.execute('''
        SELECT id, guild_id, submitted_guild, forecast 
        FROM fortunes 
        WHERE used=0 AND source='guild'
        ORDER BY approved_time ASC
        LIMIT 1
    ''')
    guild_fortune = cursor.fetchone()
    
    if guild_fortune:
        fortune_id, guild_id, submitted_guild, forecast = guild_fortune
        cursor.execute('UPDATE fortunes SET used=1 WHERE id=?', (fortune_id,))
        conn.commit()
        return {
            'id': fortune_id,
            'display_id': f"Guild-{submitted_guild}-{guild_id}",
            'forecast': forecast,
            'source': 'guild'
        }
    
    # 2. Then try to get an approved global submission
    cursor.execute('''
        SELECT id, global_id, forecast 
        FROM fortunes 
        WHERE used=0 AND source='global'
        ORDER BY approved_time ASC
        LIMIT 1
    ''')
    global_fortune = cursor.fetchone()
    
    if global_fortune:
        fortune_id, global_id, forecast = global_fortune
        cursor.execute('UPDATE fortunes SET used=1 WHERE id=?', (fortune_id,))
        conn.commit()
        return {
            'id': fortune_id,
            'display_id': f"Global-{global_id}",
            'forecast': forecast,
            'source': 'global'
        }
    
    # 3. Finally, try to get a Batune fortune
    cursor.execute('SELECT batune_index FROM queue_state')
    batune_index = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT id, batune_id, forecast 
        FROM fortunes 
        WHERE source='batune'
        ORDER BY batune_id ASC 
        LIMIT 1 OFFSET ?
    ''', (batune_index,))
    batune_fortune = cursor.fetchone()
    
    if batune_fortune:
        fortune_id, batune_id, forecast = batune_fortune
        cursor.execute('UPDATE fortunes SET used=1 WHERE id=?', (fortune_id,))
        cursor.execute('UPDATE queue_state SET batune_index=?', (batune_index + 1,))
        conn.commit()
        return {
            'id': fortune_id,
            'display_id': f"Batune-{batune_id}",
            'forecast': forecast,
            'source': 'batune'
        }
    
    # 4. If no fortunes found, reset everything and try again
    cursor.execute('UPDATE fortunes SET used=0')
    cursor.execute('UPDATE queue_state SET batune_index=0')
    conn.commit()
    return get_next_fortune()

async def post_fortune():
    channel = client.get_channel(CONFIG.TARGET_CHANNEL)
    try:
        fortune = get_next_fortune()
        if fortune['source'] == 'guild':
            parts = fortune['display_id'].split('-')
            await channel.send(f'🌟 **Fortune from Guild {parts[1]} (#{parts[2]}):**\n{fortune["forecast"]}')
        elif fortune['source'] == 'global':
            await channel.send(f'🌍 **Global Fortune #{fortune["display_id"].split("-")[-1]}:**\n{fortune["forecast"]}')
        else:
            await channel.send(f'🏛️ **Original Batune #{fortune["display_id"].split("-")[-1]}:**\n{fortune["forecast"]}')
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
    cursor.execute('SELECT COUNT(*) FROM fortunes WHERE source="batune"')
    if cursor.fetchone()[0] == 0:
        if import_fortunes():
            print("Imported Batune fortunes from full_entries.csv")
        else:
            print("Error importing Batune fortunes")
    
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
        cursor.execute('UPDATE queue_state SET batune_index=0')
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
            SELECT id, source, batune_id, global_id, guild_id, submitted_guild, forecast 
            FROM fortunes 
            ORDER BY CASE source
                WHEN 'guild' THEN 1
                WHEN 'global' THEN 2
                WHEN 'batune' THEN 3
            END ASC, approved_time DESC
            LIMIT 25
        ''')
        fortunes = cursor.fetchall()
        
        if fortunes:
            response = "🔮 **Fortune Queue (Priority Order):**\n"
            for f in fortunes:
                if f[1] == 'batune':
                    ident = f"Batune-{f[2]}"
                    emoji = "🏛️"
                elif f[1] == 'global':
                    ident = f"Global-{f[3]}"
                    emoji = "🌍"
                else:
                    ident = f"Guild-{f[5]}-{f[4]}"
                    emoji = "🌟"
                response += f"{emoji} {f[0]}: {ident} - {f[6][:50]}{'...' if len(f[6]) > 50 else ''}\n"
            await message.channel.send(response)
        else:
            await message.channel.send("No fortunes found!")

client.run(CONFIG.DISCORD_TOKEN)
