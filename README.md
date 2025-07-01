# BatuneBot - Fortune of the Day Discord Bot

BatuneBot posts daily fortunes with priority to approved guild submissions, cycling through all fortunes automatically. Free to use, but credit to BATUNEDeveloper (batune.com) and kevmuri would be appreciated.

## Features
- **Automated Daily Fortunes**: Posts at scheduled UTC time
- **Dual ID System**: Preserves original Batune IDs + guild-specific IDs
- **Submission Workflow**: Guild submissions require approval, global auto-approved
- **Priority Queue**: Approved guild fortunes get posted first
- **Complete In-Discord Management**: All operations through Discord commands
- **Multi-Guild Support**: Guild-specific ID sequences and submissions
- **Fortune Cycling**: Automatically resets after all fortunes are used
- **Backup System**: Export database to CSV with `mika export`

## Setup Instructions

### 1. Create Discord Bot
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a New Application
3. Navigate to Bot → Privileged Gateway Intents → Enable "Message Content Intent"
4. Copy your bot token

### 2. Configure Environment
Create `CONFIG.py` in the bot directory with:
```python
DISCORD_TOKEN = "your_bot_token_here"
TARGET_CHANNEL = 123456789012345678  # Replace with your channel ID
SCHEDULED_POST_HOUR = 14  # 24-hour UTC format (e.g., 14 = 2PM UTC)
SCHEDULED_POST_MINUTE = 0
3. Prepare Fortune Database
Place your Batune collection CSV as full_entries.csv with columns:

text
id,forecast,direction
1,You will have a great day!,positive
2,Good fortune is coming your way,positive
...
4. Install & Run
bash
pip install discord.py
python batunebot.py
Using BatuneBot
For Everyone
Add a fortune
mika add Your fortune text here
In DMs: Creates global fortune (auto-approved)
In guild channel: Creates guild submission (needs approval)
Example: mika add You will discover something wonderful today

For Admins
Test fortune posting
mika test - Immediately posts today's fortune

Approve guild submissions
mika approve 42 - Approves fortune #42

Reject guild submissions
mika reject 42 - Rejects and removes fortune #42

List pending approvals
mika pending - Shows submissions needing approval

Reset all fortunes
mika reset - Marks all fortunes as unused

Remove guild fortune
mika remove 42 - Deletes guild fortune #42

List all fortunes
mika list - Shows fortunes with status indicators:

Global #ID: Original Batune fortunes and those added by users

Guild #ID ⏳: Pending submission

Guild #ID ✅: Approved submission

Export database
mika export - Creates fortunes_export.csv backup

Send custom message
mika say Your announcement here

How It Works
First Run
Creates database with new schema

Imports fortunes from full_entries.csv as global fortunes

Starts posting from index 0 (first fortune)

Daily Operation
Priority to Approved Guild Fortunes:

Checks for approved guild submissions first

Posts oldest approved submission

Global Fortunes:

If no guild submissions, posts next global fortune in ID order

Maintains position between restarts

Reset Mechanism:

When all fortunes are used, marks all as unused

Resets to first fortune in sequence

Adding Fortunes
Global Submissions (DMs):

Auto-approved

Get next global ID (continues from highest Batune ID)

Added to global fortune queue

Guild Submissions (Server Channels):

Require admin approval

Get guild-specific ID (unique within guild)

Added to pending queue until approved

ID System Explained
ID Type	Format	Scope	Example
Management ID	Single number	All fortunes	42 (used in commands)
Global ID	Global #ID	Batune/original	Global #815
Guild ID	Guild #ID	Guild-specific	Guild #7
Credits
Original concept: kevmuri (QOTD Bot)

Fortune system: BATUNEDeveloper (batune.com)

Bot adaptation: Tr6nt0

Troubleshooting
Duplicate fortune error: Fortune text must be unique

Global fortune protection: Admins can't remove global fortunes

Index starts at 0: First fortune is position 0

Export format: CSV with management ID, global ID, guild ID, and source
