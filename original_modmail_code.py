import asyncio
import discord
import logging
import aiosqlite
import json
from discord.ext import commands

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(
    filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter(
    '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

intents = discord.Intents.all()

myactivity = discord.Activity(name='DMs from you', type=discord.ActivityType.listening)
bot = commands.Bot(command_prefix=';', intents=intents, activity=myactivity)

@bot.event
async def on_ready():
    global bot

    bot.my_guild = bot.get_guild(743536411369799800) #server bot is acting as mailperson for (only one at a time)
    bot.modmail_private_cat = bot.my_guild.get_channel(852373071418359818) #category needs to be private. channels will inherit perms
    bot.logs_channel = bot.my_guild.get_channel(852396131152560129) #make sure this channel is private
    bot.modmail_emoji = bot.get_emoji(853758782344658944)

    print(f'\nOnline as {bot.user}')
    print('--------\n')
    return

#async def once_started_up():
    #await bot.wait_until_ready()
    #conn = await aiosqlite.connect('modmail.db')
    #c = await conn.cursor()
    #await c.execute('CREATE TABLE IF NOT EXISTS activemodmails (userid integer, modmailchnlid integer, reason text, msglogtext)')
    #await conn.commit()
    #await conn.close()

#bot.loop.run_until_complete(once_started_up())

async def open_modmail(messagectx, modmailuserid, modmailreason="no reason specified"):
    modmail_user = bot.get_user(modmailuserid)
    modmail_channel = await bot.modmail_private_cat.create_text_channel(f'{modmail_user.name}{modmail_user.discriminator}')
    
    first_log_entry = f"{messagectx.author.name}#{messagectx.author.discriminator} ({messagectx.author.id}) at {messagectx.created_at} UTC\n{messagectx.content}\n\n"
    new_row = (modmailuserid, modmail_channel.id, modmailreason, first_log_entry)

    conn = await aiosqlite.connect('modmail.db')
    c = await conn.cursor()
    await c.execute('INSERT INTO activemodmails VALUES (?,?,?,?)', new_row)
    await conn.commit()
    await conn.close()
    
    await modmail_channel.send(f'{bot.modmail_emoji} *Modmail opened by* {messagectx.author.mention} *to talk to* {modmail_user.mention}, *for reason* "{modmailreason}". \n*Use ;closemodmail to close this modmail, and ;modmailreason to change its reason.\nFirst message:*\n\n{messagectx.content}')
    await modmail_user.send(f'{bot.modmail_emoji} *Opened a new modmail for reason* "{modmailreason}". *All messages sent will be relayed back and forth between you and the moderators.\nUse ;closemodmail to close this modmail, and ;modmailreason to change its reason.\nFirst message:*\n\n{messagectx.content}')

async def relay_message(messagectx, row, from_user: bool):
    
    if from_user:
        destination = bot.get_channel(row[1])
    else: #if in modmail channel
        destination = bot.get_user(row[0])
    
    if messagectx.attachments != []:
        discordable_files = [(await x.to_file()) for x in messagectx.attachments]
        await destination.send(f'**{messagectx.author.name}**: {messagectx.content}', files=discordable_files)
    else:
        await destination.send(f'**{messagectx.author.name}**: {messagectx.content}')

    await messagectx.add_reaction('✅')
    log_entry = f"{messagectx.author.name}#{messagectx.author.discriminator} ({messagectx.author.id}) at {messagectx.created_at} UTC\n{messagectx.content}\nAttachments: {messagectx.attachments}\n\n"
    updated_log = row[3] + log_entry
    to_update = (updated_log, row[1])
    
    conn = await aiosqlite.connect('modmail.db')
    c = await conn.cursor()
    await c.execute('UPDATE activemodmails SET msglog=? WHERE modmailchnlid=?', to_update)
    await conn.commit()
    await conn.close()

async def close_modmail_func(messagectx, row):

    modmail_channel = bot.get_channel(row[1])
    modmail_user = bot.get_user(row[0])
    modmail_reason = row[2]
    
    log_filename = f'log-{modmail_user.name}-{modmail_reason}.txt'
    with open(log_filename, 'w') as logs_txt_file:
        logs_txt_file.write(row[3])
        log_name_with_path = logs_txt_file.name

    dpy_compatible_log = discord.File(log_name_with_path)
    await bot.logs_channel.send(content=f'{bot.modmail_emoji} *Modmail with* {modmail_user.mention} *closed by* {messagectx.author.name}. *Modmail reason was* "{modmail_reason}". *Logs attached.*', file=dpy_compatible_log)

    dpy_compatible_log = discord.File(log_name_with_path)
    await modmail_user.send(content=f'{bot.modmail_emoji} *Modmail closed by* {messagectx.author.name}. *Modmail reason was* "{modmail_reason}". *Logs attached.*', file=dpy_compatible_log)
    
    await modmail_channel.delete()

    conn = await aiosqlite.connect('modmail.db')
    c = await conn.cursor()
    await c.execute('DELETE FROM activemodmails WHERE modmailchnlid=?', (row[1], ))
    await conn.commit()
    await conn.close()


@bot.listen()
async def on_message(message):
    if message.author.id != bot.user.id:
        
        msg_channel = message.channel
        msg_channelid = message.channel.id
        msg_guild = message.guild
        msg_authorid = message.author.id
        msg_content = message.content

        def check_reaction(reaction, user):
            confirm_send = '👍'
            cancel_send = '🚫'
            return user == message.author and (str(reaction.emoji) == confirm_send or str(reaction.emoji) == cancel_send)

        if msg_guild is None and bot.my_guild.get_member(msg_authorid) is not None: #if in DM and user in guild

            conn = await aiosqlite.connect('modmail.db')
            c = await conn.cursor()
            await c.execute('SELECT * FROM activemodmails WHERE userid=?', (msg_authorid, ))
            my_row = await c.fetchone()
            await conn.commit()
            await conn.close()

            if my_row is not None: #if active modmail, relay message or close modmail

                if msg_content == ';closemodmail':
                    await close_modmail_func(message, my_row)

                elif ';modmailreason' in msg_content:
                    return #update modmail reason– handled by separate cmd

                else: #if part of convo
                    await relay_message(message, my_row, True)

            else: #if not active modmail, create modmail

                bot_msg = await msg_channel.send(f'{bot.modmail_emoji} *Initiating a new modmail. React with 👍 to send your above message to KotLC Chats. To cancel, react with 🚫 or ignore this.\nYour message:*\n\n {msg_content}')
                await bot_msg.add_reaction('👍')
                await bot_msg.add_reaction('🚫')

                try: #ask for confirmation, create new modmail, and relay message
                    reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check_reaction)
                    if str(reaction) == '👍': #if user confirms
                        await msg_channel.send(f'{bot.modmail_emoji} *Okay, opening new modmail and relaying your message...*')
                        await open_modmail(message, msg_authorid)

                    elif str(reaction) == '🚫': #if user cancels
                        await msg_channel.send(f'{bot.modmail_emoji} *Cancelled.*')

                except asyncio.TimeoutError: #if 60 seconds pass without user confirming or canceling
                    await msg_channel.send(f'{bot.modmail_emoji} *Timed out, request cancelled.*')

        else: #if not in DM
            conn = await aiosqlite.connect('modmail.db')
            c = await conn.cursor()
            await c.execute('SELECT * FROM activemodmails WHERE modmailchnlid=?', (msg_channelid, ))
            my_row = await c.fetchone()
            await conn.commit()
            await conn.close()

            if my_row is not None: #if in active modmail channel

                if message.content == ';closemodmail':
                    await close_modmail_func(message, my_row)
                
                elif ';modmailreason' in msg_content:
                    return #update modmail reason– handled by separate cmd

                else: #if part of convo, relay message
                    await relay_message(message, my_row, False)


@bot.command()
async def openmodmail(ctx, inputted_userid, *, inputted_reason="no reason specified"):
    if ctx.guild == bot.my_guild:
        try:
            await ctx.send(f'{bot.modmail_emoji} *What message should I DM to* <@{inputted_userid}> *to initiate this modmail?*')

            def check_user(m):
                return m.author == ctx.message.author and m.channel == ctx.message.channel

            msg = await bot.wait_for('message', timeout = 60.0, check=check_user)
            await open_modmail(msg, int(inputted_userid), inputted_reason)
        except discord.Forbidden:
            await ctx.send(f'{bot.modmail_emoji} *Error: Can\'t DM that user.*')

@bot.command() #REMOVE FROM BOT BEFORE USING IN KOTLC CHATS (if you do)
async def deletemanychannels(ctx, *, many_ids: str):
    id_list = json.loads(many_ids)
    for chnl_id in id_list:
        fated_to_die_chnl = bot.get_channel(chnl_id)
        await asyncio.sleep(1)
        await fated_to_die_chnl.delete()

@bot.command()
async def modmailreason(ctx, *, reason: str):
    
    update_notice = f'{bot.modmail_emoji} {ctx.message.author.name}#{ctx.message.author.discriminator} *set the modmail topic/reason to* "{reason}"'
    conn = await aiosqlite.connect('modmail.db')
    c = await conn.cursor()

    if ctx.guild is None:
        await c.execute('SELECT * FROM activemodmails WHERE userid=?', (ctx.message.author.id,))
    else:
        await c.execute('SELECT * FROM activemodmails WHERE modmailchnlid=?', (ctx.channel.id,))
    
    my_row = await c.fetchone()
    to_logs_reason_change = my_row[3] + f'{update_notice}\n\n'

    await c.execute('UPDATE activemodmails SET reason=?, msglog=? WHERE modmailchnlid=? ', (reason, to_logs_reason_change, my_row[1]))
    await conn.commit()
    await conn.close()

    modmail_channel = bot.get_channel(my_row[1])
    modmail_user = bot.get_user(my_row[0])
    to_pin_reason = await modmail_channel.send(update_notice)
    await to_pin_reason.pin()

    await modmail_user.send(update_notice)

@bot.command()
async def showdb(ctx):
    
    conn = await aiosqlite.connect('modmail.db')
    c = await conn.cursor()
    await c.execute('SELECT * FROM activemodmails')
    full_activemodmails_table = await c.fetchall()
    await conn.commit()
    await conn.close()

    showtable_filename = f'{ctx.message.created_at}-contents-of-activemodmails.txt'

    with open(showtable_filename, 'w') as showtable_txt_file:
        showtable_txt_file.write('userid, modmailchnlid, reason, msglog\n\n')
        for myrow in full_activemodmails_table:
            showtable_txt_file.write(f'{myrow}\n')
        showtable_filename_with_path = showtable_txt_file.name
    
    dpy_compatible_showtable_file = discord.File(showtable_filename_with_path)
    await ctx.send(content=f'Current contents of activemodmails table:', file=dpy_compatible_showtable_file)


bot.run('placeholder')