import discord
import re
import sqlite3
import sys
from datetime import datetime

from discord.ext import tasks

import CONFIG

client = discord.Client()
channel = client.get_channel(CONFIG.TARGET_CHANNEL)

conn = sqlite3.connect('questions.db')
cursor = conn.cursor()

if __name__ == '__main__':
    if sys.argv[1] == '--reset-questions':
        cursor.execute('DROP table IF EXISTS questions')
        cursor.execute('CREATE table QUESTIONS (QUESTION TEXT)')
        conn.commit()
        conn.close()
        print('Question Table Reset Successfully.')
        exit()

    cursor.execute('CREATE table IF NOT EXISTS QUESTIONS (QUESTION TEXT)')
    conn.commit()
    conn.close()

    client.run(CONFIG.DISCORD_TOKEN)


def add_question(question):
    cursor.execute('INSERT INTO QUESTIONS VALUES (?)', question)
    conn.commit()
    conn.close()


def remove_question(question):
    cursor.execute('DELETE FROM QUESTION VALUES (?)', question)
    conn.commit()
    conn.close()


async def post_question():
    cursor.execute('SELECT QUESTION FROM QUESTIONS ORDER BY RAND() LIMIT 1')
    qotd = cursor.fetchone()
    if qotd:
        await channel.send('QOTD: ' + qotd)
    else:
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
    if message.content.lower().startswith('mika add '):
        question = re.sub('mika add ', '', message.content, flags=re.IGNORECASE)
        await channel.send('QOTD ADDED: ' + question)
        add_question(question)

    if message.content.lower().startswith('mika test') and message.author.guild_permissions.kick_members:
        await post_question()

    if message.content.lower().startswith('mika say') and message.author.guild_permissions.kick_members:
        my_message = re.sub('mika say ', '', message.content, flags=re.IGNORECASE)
        await channel.send(my_message)
