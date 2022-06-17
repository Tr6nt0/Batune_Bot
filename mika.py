# mika.py

import os, discord, random, re
from discord.ext import tasks
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client()

#ID of channel where questions are posted
target = #fill in

#Hour QOTD is to be posted
posttime = #fill in

questionsfile = Path(__file__).with_name('questions.txt')
tempfile = Path(__file__).with_name('temp.txt')

#Adds a question to the text file when called.
def question_add(question):
    with open(questionsfile, 'a') as questions:
        questions.write('\n' + question)

def remove_question(qotd):
    with open (questionsfile, "r") as input:
        with open (tempfile, "w") as output:
            for line in input:
                if line.strip("\n") != qotd:
                    output.write(line)
    os.replace(tempfile, questionsfile)

#Posts question of the day when called.
async def question_post(channel):
    with open(questionsfile, 'r') as questions:
        qlines = questions.read().splitlines()
        try:
            qotd = random.choice(qlines)
            await channel.send('QOTD: '+ qotd)
            remove_question(qotd)
        except:
            await channel.send("No questions left. Everyone submit one!")
    print(f'{client.user} has posted a qotd!')

#Scheduled to call question of the day.
@tasks.loop(minutes=60)
async def task():
    if datetime.now().hour == posttime:
        channel = client.get_channel(target)
        await question_post(channel)

#Make sure bot is online.
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord! It is '+ str(datetime.utcnow()))
    await task.start()

#Reads for commands, which includes adding questions and testing
@client.event
async def on_message(message):
    if message.content.lower().startswith('mika add '):
        question = re.sub('mika add ', '', message.content, flags=re.IGNORECASE)
        await message.channel.send('QOTD ADDED: '+ question)
        question_add(question)
    if message.content.startswith('mika test') and message.author.guild_permissions.kick_members == True:
        channel = client.get_channel(target)
        await question_post(channel)
    if message.content.startswith('mika say') and message.author.guild_permissions.kick_members == True:
        puppetmessage = re.sub('mika say ', '', message.content, flags=re.IGNORECASE)
        await message.channel.send(puppetmessage)

client.run(TOKEN)
