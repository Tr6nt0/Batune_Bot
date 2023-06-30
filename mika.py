import discord
import re
import sqlite3
import sys
from datetime import datetime

from discord.ext import tasks

import CONFIG

intents = discord.Intents.default()
intents.message_content = True

conn = sqlite3.connect('questions.db')
cursor = conn.cursor()

client = discord.Client(intents=intents)

if len(sys.argv) > 1:
    if sys.argv[1] == '--rq':
        cursor.execute('DROP table IF EXISTS questions_table')
        cursor.execute('CREATE table questions_table (questions TEXT)')
        conn.commit()
        print('Question Table Reset Successfully.')
        exit()

cursor.execute('CREATE table IF NOT EXISTS questions_table (questions TEXT)')
conn.commit()


def add_question(question):
    cursor.execute('INSERT INTO questions_table (questions) VALUES (?)', [question])
    conn.commit()


def remove_question(question):
    cursor.execute('DELETE FROM questions_table WHERE questions=?', [question])
    conn.commit()


async def post_question():
    channel = client.get_channel(CONFIG.TARGET_CHANNEL)

    cursor.execute('SELECT questions FROM questions_table ORDER BY random() LIMIT 1')
    try:
        qotd = cursor.fetchone()[0]
        await channel.send('QOTD: ' + qotd)
        remove_question(qotd)
    except:
        await channel.send('No questions left. Everyone submit one!')
    print(f'{client.user} has posted!')


@tasks.loop(seconds=60)
async def task():
    if datetime.now().hour is CONFIG.SCHEDULED_POST_HOUR and datetime.now().minute is CONFIG.SCHEDULED_POST_MINUTE:
        await post_question()


@client.event
async def on_ready():
    channel = client.get_channel(CONFIG.TARGET_CHANNEL)
    print(f'{client.user} has connected to Discord! It is ' + str(datetime.utcnow()))
    await task.start()


@client.event
async def on_message(message):
    channel = client.get_channel(CONFIG.TARGET_CHANNEL)

    if message.content.lower().startswith('mika add '):
        question = re.sub('mika add ', '', message.content, flags=re.IGNORECASE)
        await channel.send('QOTD ADDED: ' + question)
        add_question(question)

    if message.content.lower().startswith('mika test') and message.author.guild_permissions.kick_members:
        await post_question()

    if message.content.lower().startswith('mika say') and message.author.guild_permissions.kick_members:
        my_message = re.sub('mika say ', '', message.content, flags=re.IGNORECASE)
        await channel.send(my_message)

client.run(CONFIG.DISCORD_TOKEN)