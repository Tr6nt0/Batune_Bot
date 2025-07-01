BatuneBot - Community Fortune System
BatuneBot delivers daily fortunes with community-driven submissions, prioritizing guild contributions while preserving original Batune wisdom as a fallback.

Features
Community First: Guild submissions prioritized over global and Batune

Approval System: All submissions require admin approval

Multi-Server Support: Works across unlimited Discord servers

Fair Queue: Guild > Global > Batune priority system

No ID Until Approval: Fortunes only get IDs when approved

Daily Automation: Posts at scheduled UTC time

Simple Management: All commands in Discord - no CLI needed

Setup Instructions
1. Create Discord Bot
Go to Discord Developer Portal

Create New Application → Bot → Enable "Message Content Intent"

Copy your bot token

2. Configure Environment
Create CONFIG.py with:

python
DISCORD_TOKEN = "your_bot_token_here"
TARGET_CHANNEL = 123456789012345678  # Your fortune channel ID
SCHEDULED_POST_HOUR = 14  # 24-hour UTC (e.g., 14 = 2PM UTC)
SCHEDULED_POST_MINUTE = 0
3. Prepare Batune Database
Add your Batune collection as full_entries.csv:

csv
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
Submit Fortune
mika add Your fortune text

In server channels: Creates guild submission

In DMs: Creates global submission

Example: mika add Today brings new opportunities!

For Admins
Command	Description	Example
mika approve <ID>	Approve submission	mika approve 42
mika reject <ID>	Reject submission	mika reject 42
mika submissions	View recent submissions	mika submissions
mika fortunes	View approved fortunes	mika fortunes
mika test	Test fortune posting	mika test
mika reset	Reset all fortunes	mika reset
mika say <msg>	Send custom message	mika say Hello!
Priority System
BatuneBot uses a fair priority system:

Diagram
Code
graph TD
    A[Next Fortune] --> B{Guild submissions available?}
    B -->|Yes| C[Post Guild Fortune]
    B -->|No| D{Global submissions available?}
    D -->|Yes| E[Post Global Fortune]
    D -->|No| F[Post Batune Fortune]
    F --> G{All fortunes used?}
    G -->|Yes| H[Reset All Fortunes]
🌟 Guild Fortunes (Highest Priority)

Submitted in server channels

Format: Guild-{ServerID}-{Sequence}

Example: 🌟 Fortune from Guild 123456789 (#3)

🌍 Global Fortunes (Medium Priority)

Submitted via DMs

Format: Global-{ID}

IDs start at 800

Example: 🌍 Global Fortune #802

🏛️ Batune Fortunes (Fallback) Batune fortunes are treated as a preapproved guild with 800 submitted fortunes.

Original wisdom from your CSV

Used only when no submissions available

Format: Batune-{OriginalID}

Example: 🏛️ Original Batune #42

Workflow Overview
Submitting Fortunes
User submits with mika add <fortune>

Submission goes to pending queue

Admin approves/rejects submission

Daily Operation
Bot checks for approved guild submissions first

If none, checks global submissions

If none, uses Batune fortune

When all fortunes served, automatically resets

ID Assignment
Batune: Keeps original IDs (1-799)

Global: Auto-assigned IDs starting from 800

Guild: Server-specific sequences (1, 2, 3...)

All IDs assigned ONLY when approved

Troubleshooting
"Fortune already exists": Ensure unique fortune text

Approval fails: Check submission exists and not already approved

No Batune showing: Ensure full_entries.csv is formatted correctly

Reset not working: Use mika reset to manually reset fortunes

Credits
Sacred Source: BATUNEDeveloper (batune.com)

Bot Framework: kevmuri (QOTD Bot)

Priority System: Tr6nt0
