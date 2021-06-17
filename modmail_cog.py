import discord
from discord.ext import commands
import aiosqlite
import asyncio
from config.server_vars import logs_channel_id, server_id, modmail_category_id, moderator_role_ids


class Modmail(commands.Cog):
    "Fully-featured modmail setup. DM this bot to open a modmail and speak to moderators. Use ;modmailreason and ;closemodmail in an open modmail (channel or DM) to change the modmail reason or close it. Once closed, users and moderators will be sent a log of the conversation. Attachements function as expected. Moderators can use ;openmodmail <userid> [reason] to open a modmail with a specific user. A \'✅\' reaction on a message means it\'s been successfully relayed, and messages without this reaction have not been relayed. If system does not function as expected, please contact LonelyPenguin#9931."
    
    def __init__(self, bot: commands.Bot):
        
        self.bot = bot
        self.embed_details = {'author name': 'Servername Modmail', 'author icon': 'https://cdn.discordapp.com/attachments/743536411369799804/854865953083228181/mail_icon.png', 'footer': 'Use ;closemodmail to close this modmail, and ;modmailreason to change its reason.'}
        self.dont_trigger_onmessage = [';closemodmail', ';modmailreason', ';openmodmail', ';reloadext', ';showdb', ';deletemanychannels']
        print('\nReloaded cog\n----')
    

#functions for less repeated code

    async def open_modmail_func(self, messagectx, modmailuserid, from_user: bool, modmailreason="no reason specified"):
        
        modmail_user = self.bot.get_user(modmailuserid)
        
        opening_modmail_embed = discord.Embed(description = 'Opening a new modmail...')
        opening_modmail_message = await modmail_user.send(embed = opening_modmail_embed)

        c = await self.bot.conn.cursor()
        await c.execute('SELECT * FROM activemodmails WHERE userid=?', (modmail_user.id,))
        if await c.fetchone() is None:

            my_guild = self.bot.get_guild(server_id)
            modmail_private_cat = my_guild.get_channel(modmail_category_id)
            modmail_channel = await modmail_private_cat.create_text_channel(f'{modmail_user.name}{modmail_user.discriminator}')

            first_log_entry = f"{messagectx.author.name}#{messagectx.author.discriminator} ({messagectx.author.id}) at {messagectx.created_at} UTC\n{messagectx.content}\nAttachment(s): {[attachment.url for attachment in messagectx.attachments]}\n\n"
        
            new_row = (modmail_user.id, modmail_channel.id, modmailreason, first_log_entry)

        
            c = await self.bot.conn.cursor()
            await c.execute('INSERT INTO activemodmails VALUES (?,?,?,?)', new_row)
            await self.bot.conn.commit()
        
            if from_user:
                mod_modmail_opened_embed = discord.Embed(description = f'New modmail from {messagectx.author.mention} (see their message below). Send a message in this channel to respond.\n\nA \'✅\' on your message means it\'s been successfully relayed.').set_author(name = self.embed_details['author name'], icon_url = self.embed_details['author icon']).set_footer(text = self.embed_details['footer'])

                user_modmail_opened_embed = discord.Embed(description = f'Opened a new modmail and sent your message.\n\nAll messages sent will be relayed back and forth between you and the moderators. A \'✅\' on your message means it\'s been successfully relayed.').set_author(name = self.embed_details['author name'], icon_url = self.embed_details['author icon']).set_footer(text = self.embed_details['footer'])

                relay_first_message_to = modmail_channel
        
            else:
                mod_modmail_opened_embed = discord.Embed(description = f'Modmail opened by moderator {messagectx.author.mention} to talk to user {modmail_user.mention}. The reason for this modmail is "{modmailreason}".\n\nA \'✅\' on your message means it\'s been successfully relayed.\n\n**{messagectx.author.name}\'s initial message**e:\n\n{messagectx.content}').set_author(name = self.embed_details['author name'], icon_url = self.embed_details['author icon']).set_footer(text = self.embed_details['footer'])
        
                user_modmail_opened_embed = discord.Embed(description = f'A moderator on KotLC Chats opened a new modmail to speak with you (see their message below). Send a message in this DM to respond. The reason for this modmail is "{modmailreason}." \n\nAll messages sent will be relayed back and forth between you and the moderators. A \'✅\' on your message means it\'s been successfully relayed.').set_author(name = self.embed_details['author name'], icon_url = self.embed_details['author icon']).set_footer(text = self.embed_details['footer'])

                relay_first_message_to = modmail_user
            
            initial_user_msg = await modmail_user.send(embed = user_modmail_opened_embed)
            initial_mod_msg = await modmail_channel.send(embed = mod_modmail_opened_embed)
            
            if messagectx.attachments != []:
                discordable_files = [(await x.to_file()) for x in messagectx.attachments]
                await relay_first_message_to.send(f'**{messagectx.author.name}**: {messagectx.content}', files=discordable_files)
            else:
                await relay_first_message_to.send(f'**{messagectx.author.name}**: {messagectx.content}')

            await initial_user_msg.pin()
            await initial_mod_msg.pin()
        
        else:
            avoid_duplicate_modmail_embed = discord.Embed(description = f'Error: you tried to open more than one modmail at once. The bot will handle this– no action is required on your part, and the rest of the modmail flow will continue as normal. However, the following message was *not* relayed, so you may want to send it again:\n\n{messagectx.content}')
            
            if from_user:
                await messagectx.author.send(embed = avoid_duplicate_modmail_embed)
            else:
                await opening_modmail_message.delete()
                await messagectx.channel.send(embed = avoid_duplicate_modmail_embed)
        

    async def relay_message(self, messagectx, row, from_user: bool):

        if from_user:
            destination = self.bot.get_channel(row[1])
        else: #if in modmail channel
            destination = self.bot.get_user(row[0])

        try:
            if messagectx.attachments != []:
                discordable_files = [(await x.to_file()) for x in messagectx.attachments]
                await destination.send(f'**{messagectx.author.name}**: {messagectx.content}', files=discordable_files)
            else:
                await destination.send(f'**{messagectx.author.name}**: {messagectx.content}')

            await messagectx.add_reaction('✅')
        except discord.Forbidden:
            await messagectx.channel.send('Couldn\'t send a message to this user; they have probably blocked the bot. Try DMing them directly. (Alternatively, you have blocked this bot and it can\'t add a reaction to your message.)')

        log_entry = f"{messagectx.author.name}#{messagectx.author.discriminator} ({messagectx.author.id}) at {messagectx.created_at} UTC\n{messagectx.content}\nAttachment(s): {[attachment.url for attachment in messagectx.attachments]}\n\n"
        updated_log = row[3] + log_entry
        to_update = (updated_log, row[1])

        
        c = await self.bot.conn.cursor()
        await c.execute('UPDATE activemodmails SET msglog=? WHERE modmailchnlid=?', to_update)
        await self.bot.conn.commit()

#the listener itself, which is the main beef of the operation

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.id != self.bot.user.id and all([not message.content.startswith(x) for x in self.dont_trigger_onmessage]): #if message not sent by the bot and doesn't start with a command

            msg_channel = message.channel
            msg_channelid = message.channel.id
            msg_guild = message.guild
            msg_authorid = message.author.id
            msg_content = message.content


            my_guild = self.bot.get_guild(server_id)
            member_of_my_guild = my_guild.get_member(msg_authorid)
            
            if msg_guild is None and member_of_my_guild is not None: #if in DM and user in guild

                
                c = await self.bot.conn.cursor()
                await c.execute('SELECT * FROM activemodmails WHERE userid=?', (msg_authorid, ))
                my_row = await c.fetchone()
                await self.bot.conn.commit()
                

                if my_row is not None: #if message in DM and part of an active modmail, relay message
                    await self.relay_message(message, my_row, True)

                else: #if message in DM and not part of an active modmail, create modmail

                    initiate_modmail_embed = discord.Embed(description = f'Initiating a new modmail. React with 👍 to send this message to KotLC Chats moderators. To cancel, react with 🚫.\n\n**Your message**:\n\n {msg_content}').set_author(name = self.embed_details['author name'], icon_url = self.embed_details['author icon'])
                    bot_msg = await msg_channel.send(embed = initiate_modmail_embed)
                    
                    await bot_msg.add_reaction('👍')
                    await bot_msg.add_reaction('🚫')

                    def check_reaction(reaction, user):
                        confirm_send = '👍'
                        cancel_send = '🚫'
                        return user == message.author and reaction.message.id == bot_msg.id and (str(reaction.emoji) == confirm_send or str(reaction.emoji) == cancel_send)
                        
                    try: #ask for confirmation, create new modmail, and relay message
                        reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check_reaction)
                        if str(reaction) == '👍': #if user confirms
                            
                            opening_modmail_embed = discord.Embed(description = 'Okay, relaying your message to the moderators...')
                            await msg_channel.send(embed = opening_modmail_embed)

                            await self.open_modmail_func(message, msg_authorid, True) #open new modmail

                        elif str(reaction) == '🚫': #if user cancels
                            
                            cancel_embed = discord.Embed(description = 'Cancelled.')
                            await msg_channel.send(embed = cancel_embed)

                    except asyncio.TimeoutError: #if 60 seconds pass without user confirming or canceling
                        timed_out_embed = discord.Embed(description = 'Timed out, process cancelled. To try again, send a new message.')
                        await msg_channel.send(embed = timed_out_embed)

            else: #if not in DM
                
                c = await self.bot.conn.cursor()
                await c.execute('SELECT * FROM activemodmails WHERE modmailchnlid=?', (msg_channelid, ))
                my_row = await c.fetchone()
                await self.bot.conn.commit()
                

                if my_row is not None: #if in active modmail channel
                    await self.relay_message(message, my_row, False)

#commands to manage modmails

    @commands.command(aliases = ['openticket', 'newmodmail', 'newticket'])
    async def openmodmail(self, ctx, open_modmail_with_user: discord.Member, *, new_modmail_reason="no reason specified"):
        "Command for moderators to open a new modmail with a designated user. Cannot be used by regular users. Syntax: ;openmodmail <user id or mention> [optional reason]. Will create a new modmail and inform the user that a moderator opened it. Reason defaults to 'no reason specified' and can be changed later using ;modmailreason. Upon use, bot will prompt for the initial message to relay to the designated user. Attempting to open two tickets at once with the same user will result in an error, but should be handled; if something goes wrong, contact LonelyPenguin#9931."
        if ctx.guild == self.bot.get_guild(server_id) and ctx.author.top_role.id in moderator_role_ids:
            try:
                initialize_question_embed = discord.Embed(description = f'What message should I DM to {open_modmail_with_user.mention} to initiate this modmail?').set_author(name = self.embed_details['author name'], icon_url = self.embed_details['author icon']).set_footer(text = 'Prompt will time out after 60 seconds; to cancel, wait out this timer.')
                await ctx.send(embed = initialize_question_embed)

                def check_user(m):
                    return m.author == ctx.author and m.channel == ctx.channel

                msg = await self.bot.wait_for('message', timeout = 60.0, check=check_user)
                await self.open_modmail_func(msg, int(open_modmail_with_user.id), False, modmailreason = new_modmail_reason)
            except discord.Forbidden:
                cant_dm_user_embed = discord.Embed(description = 'Error: Can\'t DM that user.')
                await ctx.send(embed = cant_dm_user_embed)
            except AttributeError:
                cant_dm_user_embed = discord.Embed(description = 'Error: Can\'t DM that user.')
                await ctx.send(embed = cant_dm_user_embed)
            except asyncio.TimeoutError:
                mod_timed_out_embed = discord.Embed(description = 'Timed out. Use the command ;openmodmail <userid> [reason] to try again.')
                await ctx.send(embed = mod_timed_out_embed)

    @commands.command(aliases = ['closeticket', 'close', 'modmailclose', 'ticketclose'])
    async def closemodmail(self, ctx):
        "Closes an open modmail. Must be used in the channel/DM attached to the modmail. Can be used by moderators or the modmail user. Upon use, will delete the modmail channel and send a log of its contents to both the modmail logs channel and the user from the modmail. No arguments needed."
        c = await self.bot.conn.cursor()

        if ctx.guild is None:
            await c.execute('SELECT * FROM activemodmails WHERE userid=?', (ctx.author.id,))
        else:
            await c.execute('SELECT * FROM activemodmails WHERE modmailchnlid=?', (ctx.channel.id,))

        my_row = await c.fetchone()
        
        try:
            modmail_channel = self.bot.get_channel(my_row[1])
            modmail_user = self.bot.get_user(my_row[0])
            modmail_reason = my_row[2]
        

            log_filename = f'log-{modmail_user.name}-{modmail_reason}.txt'
            with open(log_filename, 'w') as logs_txt_file:
                logs_txt_file.write(my_row[3])
                log_name_with_path = logs_txt_file.name
        
            logs_channel = self.bot.get_channel(logs_channel_id)
            #send to moderators' logs:
            dpy_compatible_log = discord.File(log_name_with_path)
            mod_modmail_closed_embed = discord.Embed(description = f'Modmail with {modmail_user.mention} closed by {ctx.author. name}. Modmail reason was "{modmail_reason}".').set_author(name = self.embed_details['author name'], icon_url = self.embed_details['author icon']).set_footer(text = 'Use ;openmodmail <userid> [reason] to open another modmail.')

            await logs_channel.send(embed = mod_modmail_closed_embed)
            await logs_channel.send(content = 'Logs:', file=dpy_compatible_log)

            await modmail_channel.delete()

            await c.execute('DELETE FROM activemodmails WHERE modmailchnlid=?', (my_row[1], ))
            await self.bot.conn.commit()

            #send to the user:
            dpy_compatible_log = discord.File(log_name_with_path)
            user_modmail_closed_embed = discord.Embed(description = f'Modmail closed by {ctx.author.name}. At time of closure, the modmail\'s reason was "{modmail_reason}".').set_author(name = self.embed_details['author name'], icon_url = self.embed_details['author icon']).set_footer(text = 'Send another message to open a new modmail.')

            await modmail_user.send(embed=user_modmail_closed_embed)
            await modmail_user.send(content = 'Logs:', file=dpy_compatible_log)

        except TypeError:
            await ctx.send(content = 'Error: You probably aren\'t in a modmail.', delete_after = 5.0)
            await ctx.message.delete(delay = 4.75)
        except discord.Forbidden:
            await ctx.send('Modmail closed, but couldn\'t DM the user to notify them.')

    @commands.command(aliases = ['reason', 'ticketreason', 'newreason'])
    async def modmailreason(self, ctx, *, reason: str):
        "Set a new reason for an open modmail. Can be used in either an open modmail channel or a DM with an active modmail attached. Overwrites previous reasons, but reason changes are logged. A modmail's latest reason is given upon closure. Moderators can optionally set a reason for a modmail when opening one with ;openmodmail. Syntax: ;modmailreason <new reason>."

        update_notice_str = f'{ctx.author.name}#{ctx.author.discriminator} set the modmail topic/reason to "{reason}"'
        update_notice_embed = discord.Embed(description = update_notice_str).set_author(name = self.embed_details['author name'],   icon_url = self.embed_details['author icon']).set_footer(text = self.embed_details['footer'])
        
        c = await self.bot.conn.cursor()

        if ctx.guild is None:
            await c.execute('SELECT * FROM activemodmails WHERE userid=?', (ctx.author.id,))
        else:
            await c.execute('SELECT * FROM activemodmails WHERE modmailchnlid=?', (ctx.channel.id,))

        try:
            my_row = await c.fetchone()
            to_logs_reason_change = my_row[3] + f'{update_notice_str}\n\n'

            await c.execute('UPDATE activemodmails SET reason=?, msglog=? WHERE modmailchnlid=? ', (reason, to_logs_reason_change, my_row   [1]))
            await self.bot.conn.commit()


            modmail_channel = self.bot.get_channel(my_row[1])
            modmail_user = self.bot.get_user(my_row[0])
            
            mod_reason_updated_msg = await modmail_channel.send(embed = update_notice_embed)
            await mod_reason_updated_msg.pin()

            user_reason_updated_msg = await modmail_user.send(embed = update_notice_embed)
            await user_reason_updated_msg.pin()
        except TypeError:
            await ctx.send(content = 'Error: You probably aren\'t in a modmail.', delete_after = 5.0)
            await ctx.message.delete(delay = 4.75)
        except discord.MissingRequiredArgument:
            await ctx.send(content = 'Missing a required argument. Proper syntax: `;modmailreason [reason]`.', delete_after = 5.0)
            await ctx.message.delete(delay = 4.75)



def setup(bot: commands.Bot):
    bot.add_cog(Modmail(bot))