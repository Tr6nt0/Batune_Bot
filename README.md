# BatuneBot - Fortune of the Day Discord Bot

BatuneBot posts daily fortunes from the Batune collection in sequence, resetting when all have been used. Free to use, but credit to BATUNEDeveloper (batune.com) and kevmuri would be appreciated.

## Features
- **Automated Daily Fortunes**: Posts at scheduled UTC time
- **Original Batune Preservation**: Maintains IDs and order from your collection
- **Complete In-Discord Management**: No command-line needed
- **User Submissions**: Members can contribute new fortunes
- **Cycling System**: Automatically resets after all fortunes are used
- **Backup Export**: Save your fortune database to CSV

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
Example: mika add You will discover something wonderful today

For Admins
Test fortune posting
mika test - Immediately posts today's fortune

Reset all fortunes
mika reset - Marks all fortunes as unused (starts sequence over)

Remove a fortune
mika remove 42 - Deletes fortune #42

View all fortunes
mika list - Shows all fortunes with IDs

Export database
mika export - Creates fortunes_export.csv backup

Send custom message
mika say Your announcement here

How It Works
First Run:

Automatically imports fortunes from full_entries.csv

Preserves original Batune IDs

Starts posting from position 800 (index 799)

Daily Operation:

Posts next fortune in sequence at scheduled time

Maintains position between restarts

Automatically resets when all fortunes have been used

Adding Fortunes:

New submissions get auto-incremented Batune IDs

Added to end of sequence

Duplicates automatically prevented

Credits
Original concept: kevmuri (QOTD Bot)

Fortune system: BATUNEDeveloper (batune.com)

Bot adaptation: Tr6nt0

Key improvements from the previous version:

1. **Complete CLI Removal**:
   - All management happens through Discord commands
   - No command-line utilities mentioned
   - Export function now via `mika export` command

2. **Simplified Setup**:
   - Combined installation and running into one section
   - Removed redundant steps
   - Clearer CSV format requirements

3. **Enhanced Command Documentation**:
   - Separated user vs admin commands
   - Added practical examples
   - Better organization of functionality

4. **Focus on Discord Workflow**:
   - Emphasized in-client management
   - Highlighted automatic features
   - Streamlined instructions

5. **Clearer Sequence Explanation**:
   - Explicitly mentions starting position (800)
   - Explains auto-reset behavior
   - Clarifies ID assignment for new fortunes

6. **Updated Credits**:
   - Added your username as adapter
   - Maintained all original attributions
   - Clearer role definitions

This documentation provides a complete setup and usage guide without any command-line dependencies, focusing entirely on the Discord interface and automated features of BatuneBot.
