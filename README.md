# robo-mika
Question of the Day Discord Bot. Free to use, but credit to kevmuri would be nice. Simply selects a question randomly and posts it at a scheduled time.

Create a bot in the Discord Developer Portal with message content intent toggled ON.

Using your favorite text editor, create CONFIG.py in the repo directory with the following content.
```
DISCORD_TOKEN = <bot token>
TARGET_CHANNEL = <ID of desired channel>
SCHEDULED_POST_HOUR = <Hour QOTD is to be posted in UTC>
SCHEDULED_POST_MINUTE = <Minute QOTD is to be posted>
```

And assuming pip is installed, run `pip install -r requirements.txt` in the repository.

Run R. Mika with `python3 mika.py`.

To add a question simply send a discord message beginning with `mika add <QUESTION>` in any channel the bot resides in. 
It will randomly select a question and post it at the scheduled time.

To force a question, someone with guild kick permissions simply needs to send a discord message with the content of `mika test`.

R. Mika can also send a message of any kind of content. With guild kick permissions, begin a message with `mika say` and it will be posted in the target channel.

R. Mika includes a few CLI utilities. 
- `python3 mika.py --reset` will clear all questions and reinitialize the database.
- `python3 mika.py --import <questions_to_import.txt>` Will import questions to the application database line by line.
- `python3 mika.py --export <questions_to_export.txt>` Will export questions from the database to a specified file.

To prepopulate the questions database with sample questions, simply run `python3 mika.py --reset` to create the database, and
then run `python3 mika.py --import questions.txt`. NOTE: The database will initialize the first time `python3 mika.py` runs if it has not been initialized yet.