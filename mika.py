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
    except Exception as post_error:
        print(post_error)
        await channel.send('No questions left. Everyone submit one!')
    print(f'{client.user} has posted!')


@tasks.loop(seconds=60)
async def task():
    if datetime.now().hour is CONFIG.SCHEDULED_POST_HOUR and datetime.now().minute is CONFIG.SCHEDULED_POST_MINUTE:
        await post_question()


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord! It is ' + str(datetime.utcnow()))
    await task.start()


@client.event
async def on_message(message):
    channel = client.get_channel(CONFIG.TARGET_CHANNEL)

    if message.content.lower().startswith('mika add '):
        question = re.sub('mika add ', '', message.content, flags=re.IGNORECASE)
        await message.channel.send('QOTD ADDED: ' + question)
        add_question(question)

    if message.content.lower().startswith('mika test') and message.author.guild_permissions.kick_members:
        await post_question()

    if message.content.lower().startswith('mika say') and message.author.guild_permissions.kick_members:
        my_message = re.sub('mika say ', '', message.content, flags=re.IGNORECASE)
        await channel.send(my_message)


if len(sys.argv) > 1:
    if sys.argv[1] == '--reset':
        cursor.execute('DROP table IF EXISTS questions_table')
        cursor.execute('CREATE table questions_table (questions TEXT)')
        conn.commit()
        print('Question Table Reset Successfully.')
        exit()

    if sys.argv[1] == '--import':
        try:
            file = open(sys.argv[2], 'r')
            lines = file.readlines()
            for line in lines:
                add_question(line)
            file.close()
        except Exception as import_error:
            print(import_error)
        exit()

    if sys.argv[1] == '--export':
        try:
            file = open(sys.argv[2], 'w')
            cursor.execute('SELECT questions FROM questions_table')
            for line in cursor.fetchall():
                file.writelines(line)
            file.close()
        except Exception as export_error:
            print(export_error)
        exit()

client.run(CONFIG.DISCORD_TOKEN)
