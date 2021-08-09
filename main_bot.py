import asyncio
import discord
import logging
import aiosqlite
from discord.ext import commands
from config.private import token

logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(
    filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter(
    "%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)


async def startup():

    intents = discord.Intents(guilds=True, members=True, emojis=True, messages=True, reactions=True)

    myactivity = discord.Activity(
        name='DMs from you', type=discord.ActivityType.listening)

    bot = commands.Bot(
        command_prefix=commands.when_mentioned_or(';'),
        intents=intents, activity=myactivity,
        help_command=commands.MinimalHelpCommand()
        )

    async with aiosqlite.connect('modmail.db') as conn:

        bot.conn = conn
        c = await conn.cursor()
        await c.execute('CREATE TABLE IF NOT EXISTS activemodmails (userid integer, modmailchnlid integer, reason text)')
        await c.execute('CREATE TABLE IF NOT EXISTS blacklist (timestamp text, userid integer, username text)')
        await bot.conn.commit()
        await c.execute('SELECT * FROM blacklist')
        bot.blacklisted_users = await c.fetchall()

        all_extensions = ['modmail_cog', 'dev_commands_cog', 'spaghetti_slash_commands']

        for extension in all_extensions:
            bot.load_extension(extension)
            print(f'\nLoaded extension {extension}')

        print(f'\nStarting bot up \n----')

        await bot.start(token)

asyncio.run(startup())
