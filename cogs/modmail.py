# region imports
import asyncio
from functools import wraps
from io import StringIO
from textwrap import fill
from traceback import print_exception
from sys import stderr

import discord
from discord.ext import commands

from views import Confirm
# endregion


class Modmail(commands.Cog):
    # region cog/category docstring
    """Fully-featured modmail setup. DM this bot to open a modmail and speak to moderators. 

    Use `;modmail reason` and `;modmail close` in an open modmail (channel or DM) to change the modmail reason or close it.
    Once closed, users and moderators will be sent a log of the conversation.
    Attachements function as expected. 
    Moderators can use `;modmail open <user> [reason]` to open a modmail with a specific user.
    A '✅' reaction on a message means it's been successfully relayed, and messages without this reaction have not been relayed.
    A ✂️ means the message has been cut to stay within the character limit.
    If system does not function as expected, please contact LonelyPenguin#9931.
    """
    # endregion

    # region bot setup, checks, and small stuff
    def __init__(self, bot: commands.Bot):

        self.bot = bot
        self.embed_details = {'author name': 'Servername Modmail',
                              'author icon': 'https://cdn.discordapp.com/attachments/743536411369799804/854865953083228181/mail_icon.png',
                              'footer': 'Use `;`modmail close` to close this modmail, and `;modmail reason` to change its reason.'}

    def cog_check(self, ctx: commands.Context):
        """Ensures that all commands in this cog only trigger when they are meant to.

        To successfully trigger a command, user must not be blacklisted from the bot, or must be LonelyPenguin or a moderator.
        """
       # Ignore blacklisted users unless they are mods or LonelyPenguin
        return ctx.author.id not in self.bot.blacklisted_users or ctx.author.id == 305704400041803776 or ctx.author.id in self.bot.moderator_ids

    def mod_only():
        """Commands with this check will only execute for moderators."""

        def predicate(ctx: commands.Context):
            return ctx.author.id in ctx.bot.moderator_ids
        return commands.check(predicate)

    def listener_check(listener):
        """Decorator that ensures that listeners will only trigger when they are meant to (basic check).

        Listeners decorated with this function will not trigger on blacklisted users, bots, or commands.
        """

        @wraps(listener)
        async def wrapper_listener_check(*args, **kwargs):

            self, message = args[0], args[1]
            message_context = await self.bot.get_context(message)

            if message.author.bot or message_context.command or message.author.id in self.bot.blacklisted_users:
                return

            await listener(*args, **kwargs)

        return wrapper_listener_check

    # endregion

    # region open_modmail_func and relay_message
    async def open_modmail_func(self, messagectx: discord.Message, modmailuserid: int, from_user: bool, modmailreason: str = "no reason specified"):
        """Function that goes through all the necessary steps to open a modmail.

        :param messagectx: discord.Message object that is the initial message to send in the modmail.
        :param modmailuserid: ID of user to open modmail with.
        :param from_user: Whether the modmail is being opened by a user DMing the bot (otherwise, by a moderator with a cmd).
        :param modmailreason: The modmail's initial reason. Modmails opened by DMing the bot can initially only have the default reason.

        Called by the DM message listener and the `;`modmail open` command."""

        modmail_user = self.bot.get_user(modmailuserid)

        if len(messagectx.content) >= 1910:
            await messagectx.add_reaction('✂')
        message_content = messagectx.content[:1909]

        if not from_user:
            opening_modmail_message = await modmail_user.send(embed=self.bot.simple_embed('Opening a new modmail...'))

        modmail_entry = await self.bot.do_db_query(self.bot, 'SELECT * FROM activemodmails WHERE userid=?', (modmail_user.id,), "one")

        if modmail_entry:  # if a modmail is already attached to this user
            avoid_duplicate_modmail_embed = self.bot.simple_embed(
                'Error: you tried to open more than one modmail at once. The bot will handle this– no action is required on your part, and the rest of the modmail flow will continue as normal. However, the following message was probably not relayed, so you may want to send it again:')

            if from_user:  # separate rather than doing a destination if statement because modmail channel not created yet
                await messagectx.author.send(embed=avoid_duplicate_modmail_embed)
                await messagectx.author.send(message_content)
            else:
                await opening_modmail_message.delete()
                await messagectx.channel.send(embed=avoid_duplicate_modmail_embed)
                await messagectx.channel.send(message_content)
            return

        my_guild = self.bot.get_guild(self.bot.server_id)
        modmail_private_cat = my_guild.get_channel(
            self.bot.modmail_category_id)
        modmail_channel = await modmail_private_cat.create_text_channel(f'{modmail_user.name}{modmail_user.discriminator}')
        new_row = (modmail_user.id, modmail_channel.id, modmailreason)
        await self.bot.do_db_query(self.bot, 'INSERT INTO activemodmails VALUES (?,?,?)', new_row)

        if from_user:
            mod_modmail_opened_embed = discord.Embed(description=f"New modmail from {messagectx.author.mention} (see their message below). Send a message in this channel to respond.\n\nA ✅ on your message means it's been successfully relayed, and a ✂️ means it has been cut to stay within the character limit.").set_author(
                name=self.embed_details['author name'], icon_url=self.embed_details['author icon']).set_footer(text=self.embed_details['footer'])

            user_modmail_opened_embed = discord.Embed(description=f"Opened a new modmail and sent your message.\n\nAll messages sent will be relayed back and forth between you and the moderators. A ✅ on your message means it's been successfully relayed, and a ✂️ means it has been cut to stay within the character limit.").set_author(
                name=self.embed_details['author name'], icon_url=self.embed_details['author icon']).set_footer(text=self.embed_details['footer'])

            relay_first_message_to = modmail_channel

        else:
            # single quotes used despite apostrophes due to double quotes elsewhere in string
            mod_modmail_opened_embed = discord.Embed(description=f"Modmail opened by moderator {messagectx.author.mention} to talk to user {modmail_user.mention}. The reason for this modmail is `{modmailreason}`.\n\nA ✅ on your message means it's been successfully relayed.\n\n**{messagectx.author.name}'s initial message**:\n\n{message_content[:1639]}").set_author(
                name=self.embed_details['author name'], icon_url=self.embed_details['author icon']).set_footer(text=self.embed_details['footer'])

            # single quotes used despite apostrophes due to double quotes elsewhere in string
            user_modmail_opened_embed = discord.Embed(description=f"A moderator on KotLC Chats opened a new modmail to speak with you (see their message below). Send a message in this DM to respond. The reason for this modmail is `{modmailreason}`. \n\nAll messages sent will be relayed back and forth between you and the moderators. A ✅ on your message means it's been successfully relayed, and a ✂️ means it has been cut to stay within the character limit.").set_author(
                name=self.embed_details['author name'], icon_url=self.embed_details['author icon']).set_footer(text=self.embed_details['footer'])

            relay_first_message_to = modmail_user

        initial_user_msg = await modmail_user.send(embed=user_modmail_opened_embed)
        initial_mod_msg = await modmail_channel.send(embed=mod_modmail_opened_embed)

        if messagectx.attachments != []:
            discordable_files = [(await x.to_file()) for x in messagectx.attachments]
            await relay_first_message_to.send(f'**{messagectx.author.name}**: {message_content}', files=discordable_files)
        else:
            await relay_first_message_to.send(f'**{messagectx.author.name}**: {message_content}')

    async def relay_message(self, messagectx: discord.Message, row: tuple, from_user: bool):
        """Relays a message from a DMing user to moderators, or vice-versa.

        :param messagectx: discord.Message object– the message to be relayed.
        :param row: Database row associated with the modmail.
        :param from_user: Whether the message is from a DMing user (otherwise, from a moderator).
        """

        if len(messagectx.content) >= 1960:
            await messagectx.add_reaction('✂')
        message_content = messagectx.content[:1959]

        if from_user:
            destination = self.bot.get_channel(row[1])
        else:  # if in modmail channel
            destination = self.bot.get_user(row[0])

        try:
            if messagectx.attachments != []:
                discordable_files = [(await x.to_file()) for x in messagectx.attachments]
                await destination.send(f'**{messagectx.author.name}**: {message_content}', files=discordable_files)
            else:
                await destination.send(f'**{messagectx.author.name}**: {message_content}')

            await messagectx.add_reaction('✅')
        except discord.Forbidden as error:
            await messagectx.channel.send(embed=self.bot.simple_embed(f"Error: Couldn't send a message to this user; they have probably blocked the bot. Try DMing them directly. (Alternatively, bot can't add a reaction to your message.) ({error})"))
        except AttributeError as error:
            await messagectx.channel.send(embed=self.bot.simple_embed(f"Error: Bot probably doesn't have access to that user or that channel. ({error})"))
        except Exception as error:
            await messagectx.channel.send(embed=self.bot.simple_embed(f'Something went wrong: {error}'))
            # All other errors not returned come here. And we can just print the default Traceback.
            print('Ignoring exception in function relay_message:', file=stderr)
            print_exception(
                type(error), error, error.__traceback__, file=stderr)

    # endregion

    # region the listeners themselves, which call the two functions above and have catch-all error handling
    @listener_check
    @commands.Cog.listener(name='on_message')
    async def dm_modmail_listener(self, message: discord.Message):
        """Listens for DM messages and handles relaying or opening modmails from there."""

        try:

            if message.guild is None:  # if in DM

                modmail_entry = await self.bot.do_db_query(self.bot, 'SELECT * FROM activemodmails WHERE userid=?', (message.author.id,), "one")

                if modmail_entry is not None:  # if message part of an active modmail, relay message
                    try:
                        await self.relay_message(message, modmail_entry, True)
                    except discord.Forbidden as error:
                        await message.channel.send(embed=self.bot.simple_embed(f'Error: bot lacks permissions to relay your message. Please contact a moderator directly. ({error})'))

                else:  # if message not part of an active modmail, create modmail

                    if len(message.content) >= 1910:
                        await message.add_reaction('✂')
                    msg_content = message.content[:1909]

                    initiate_modmail_embed = discord.Embed(description=f'Please confirm that you would like to open a modmail and relay your message to KotLC Chats moderators.\n\n**Your message**:\n\n {msg_content}').set_author(
                        name=self.embed_details['author name'], icon_url=self.embed_details['author icon'])

                    confirm_view = Confirm(message.author)
                    confirm_view.message = await message.channel.send(embed=initiate_modmail_embed, view=confirm_view)

                    timed_out = await confirm_view.wait()

                    for child in confirm_view.children:
                        child.disabled = True
                    await confirm_view.message.edit(view=confirm_view)

                    if timed_out:
                        confirm_view = confirm_view
                        await message.channel.send(embed=self.bot.simple_embed('Timed out; process cancelled. To try again, send a new message.'))
                        return

                    if confirm_view.value is True:  # if user confirms
                        await message.channel.send(embed=self.bot.simple_embed('Okay, relaying your message to the moderators...'))
                        # open new modmail
                        await self.open_modmail_func(message, message.author.id, True)

                    else:  # if user cancels
                        await message.channel.send(embed=self.bot.simple_embed('Cancelled.'))

        except Exception as error:
            await message.channel.send(embed=self.bot.simple_embed(f'Something went wrong: {error}'))
            print('Ignoring exception in on_message listener:', file=stderr)
            print_exception(
                type(error), error, error.__traceback__, file=stderr)

    @listener_check
    @commands.Cog.listener(name='on_message')
    async def guild_modmail_listener(self, message: discord.Message):
        """Listens for messages in modmail channels and calls relay_message to relay them to the relevant user."""

        try:
            # ignore DMs (other listener) and guild messages outside modmail cat (reduce db requests)
            if message.guild is not None and message.channel.category_id == self.bot.modmail_category_id:

                modmail_entry = await self.bot.do_db_query(self.bot, 'SELECT * FROM activemodmails WHERE modmailchnlid=?', (message.channel.id, ), "one")

                # if in active modmail channel
                if modmail_entry:
                    try:
                        await self.relay_message(message, modmail_entry, False)
                    except discord.Forbidden as error:
                        await message.channel.send(embed=self.bot.simple_embed(f"Error: couldn't DM that user. ({error})"))

        except Exception as error:
            await message.channel.send(embed=self.bot.simple_embed(f'Something went wrong: {error}'))
            print('Ignoring exception in on_message listener:', file=stderr)
            print_exception(
                type(error), error, error.__traceback__, file=stderr)
    # endregion

    # region modmail commands and errors
    @commands.group()
    async def modmail(self, ctx: commands.Context):
        """Commands for managing modmails. Use `;help modmail <command>` to view each command."""
        if not ctx.invoked_subcommand:
            await ctx.send(embed=self.bot.simple_embed('Run `;help modmail` for details.'))

    @modmail.command(name='open', aliases=['start', 'initiate', 'new'])
    @mod_only()
    @commands.guild_only()
    async def mod_open_modmail(self, ctx: commands.Context, open_modmail_with_user: discord.Member, *, new_modmail_reason: str = "no reason specified"):

        """Command for moderators to open a new modmail with a designated user.
        Cannot be used by regular users. 
        Syntax: `;modmail open <user id or mention> [optional reason]`.
        Will create a new modmail and inform the user that a moderator opened it.
        Reason defaults to 'no reason specified' and can be changed later using `;modmail reason`.
        Upon use, bot will prompt for the initial message to relay to the designated user.
        Attempting to open two tickets at once with the same user will result in an error, but should be handled;
        if something goes wrong, contact LonelyPenguin#9931.
        Maximum length of reason is 72 characters."""

        modmail_entry = await self.bot.do_db_query(self.bot, 'SELECT * FROM activemodmails WHERE modmailchnlid=?', (ctx.channel.id,), "one")
        if modmail_entry:
            await ctx.send(embed=self.bot.simple_embed('Error: you are currently in a modmail. Run this command in a different channel (for privacy).'), delete_after=5.0)
            await ctx.message.delete(delay=4.75)
            return

        initialize_question_embed = discord.Embed(description=f'What message should I DM to {open_modmail_with_user.mention} to initiate this modmail?').set_author(
            name=self.embed_details['author name'], icon_url=self.embed_details['author icon']).set_footer(text='Prompt will time out after 60 seconds; to cancel, wait out this timer.')

        await ctx.send(embed=initialize_question_embed)

        def check_user(m):
            return m.author == ctx.author and m.channel == ctx.channel

        msg = await self.bot.wait_for('message', timeout=60.0, check=check_user)

        await self.open_modmail_func(msg, open_modmail_with_user.id, False, modmailreason=new_modmail_reason[:71])
        await msg.add_reaction('👍')

    @modmail.command(name='close', aliases=['shutdown', 'finish', 'end'])
    @commands.cooldown(1, 300.0, commands.cooldowns.BucketType.channel)
    async def closemodmail(self, ctx: commands.Context):
        """Closes an open modmail.
        Must be used in the channel/DM attached to the modmail.
        Can be used by moderators or the modmail user.
        Upon use, will delete the modmail channel and send a log of its contents to both the modmail logs channel and the user from the modmail.
        No arguments needed."""

        if ctx.guild is None:
            modmail_entry = await self.bot.do_db_query(self.bot, 'SELECT * FROM activemodmails WHERE userid=?', (ctx.author.id,), "one")
        else:
            modmail_entry = await self.bot.do_db_query(self.bot, 'SELECT * FROM activemodmails WHERE modmailchnlid=?', (ctx.channel.id,), "one")

        logs_channel = self.bot.get_channel(self.bot.logs_channel_id)
        modmail_channel = self.bot.get_channel(modmail_entry[1])
        modmail_user = self.bot.get_user(modmail_entry[0])
        modmail_reason = modmail_entry[2]

        await ctx.send(embed=self.bot.simple_embed('Creating logs and closing modmail...'))

        modmail_log = StringIO()

        async for message in modmail_channel.history(limit=None, oldest_first=True):

            if message.is_system():
                continue

            embeds_if_any = ''
            if message.embeds:
                embed_desc_list = [fill(
                    embed.description) for embed in message.embeds]
                embeds_if_any = '\nEmbed description(s):\n{}\n'.format(
                    ',\n\n'.join(embed_desc_list))

            attachments_if_any = ''
            if message.attachments:
                attachment_url_list = [
                    attachment.url for attachment in message.attachments]
                attachments_if_any = '\nAttachment URL(s):\n{}\n'.format(
                    ',\n'.join(attachment_url_list))

            contentstr = f'Content:\n{fill(message.content)}\n' if message.content else '[no message content]\n'

            modmail_log.write(
                f'{message.author.name}#{message.author.discriminator} ({message.author.id}) at {str(message.created_at)[:19]} UTC\n\n{contentstr}{embeds_if_any}{attachments_if_any}\n\n')

        modmail_log.seek(0)
        log_filename = f'log-{modmail_user.name}-{modmail_reason}-{str(ctx.message.created_at)[:10]}.txt'

        # send to moderators' logs:
        dpy_compatible_log = discord.File(
            fp=modmail_log, filename=log_filename)
        modmail_log.close()

        mod_modmail_closed_embed = discord.Embed(description=f'Modmail with {modmail_user.mention} closed by {ctx.author.name}. Modmail reason was `{modmail_reason}`.').set_author(
            name=self.embed_details['author name'], icon_url=self.embed_details['author icon']).set_footer(text='Use ;modmail open <user> [reason] to open another modmail.')

        await logs_channel.send(embed=mod_modmail_closed_embed)
        await logs_channel.send(file=dpy_compatible_log)

        await self.bot.do_db_query(self.bot, 'DELETE FROM activemodmails WHERE modmailchnlid=?', (modmail_entry[1],))

        # send to the user:
        dpy_compatible_log = discord.File(
            fp=modmail_log, filename=log_filename)

        # single quotes used despite apostrophes due to double quotes elsewhere in string
        user_modmail_closed_embed = discord.Embed(description=f"Modmail closed by {ctx.author.name}. At time of closure, the modmail's reason was `{modmail_reason}`.").set_author(
            name=self.embed_details['author name'], icon_url=self.embed_details['author icon']).set_footer(text='Send another message to open a new modmail.')
        await modmail_user.send(embed=user_modmail_closed_embed)

        modmail_log.close()
        await modmail_channel.delete()

    @modmail.command(name='reason', aliases=['topic', 'subject'])
    @commands.cooldown(2, 10.0, commands.cooldowns.BucketType.channel)
    async def modmailreason(self, ctx: commands.Context, *, reason: str = None):
        """View current reason or set a new reason for an open modmail.
        Must be used in the channel/DM attached to the modmail.
        Overwrites previous reasons, but reason changes are logged.
        A modmail's latest reason is given upon closure.
        Moderators can optionally set a reason for a modmail when opening one with `;modmail open`.
        Syntax: `;modmail reason [new reason]`."""

        if not reason:

            if ctx.guild is None:
                modmail_entry = await self.bot.do_db_query(self.bot, 'SELECT * FROM activemodmails WHERE userid=?', (ctx.author.id,), "one")
            else:
                modmail_entry = await self.bot.do_db_query(self.bot, 'SELECT * FROM activemodmails WHERE modmailchnlid=?', (ctx.channel.id,), "one")

            reason = modmail_entry[2]

            view_reason_embed = discord.Embed(description=f"This modmail's reason is currently `{reason}`.").set_author(
                name=self.embed_details['author name'], icon_url=self.embed_details['author icon']).set_footer(text='Use ;modmail reason <reason> to change the reason of this modmail.')

            await ctx.send(embed=view_reason_embed)
            return

        reason = reason[:71]
        update_notice_str = f'{ctx.author.name}#{ctx.author.discriminator} set the modmail topic/reason to `{reason}`'
        update_notice_embed = discord.Embed(description=update_notice_str).set_author(
            name=self.embed_details['author name'], icon_url=self.embed_details['author icon']).set_footer(text=self.embed_details['footer'])

        if ctx.guild is None:
            modmail_entry = await self.bot.do_db_query(self.bot, 'SELECT * FROM activemodmails WHERE userid=?', (ctx.author.id,), "one")
        else:
            modmail_entry = await self.bot.do_db_query(self.bot, 'SELECT * FROM activemodmails WHERE modmailchnlid=?', (ctx.channel.id,), "one")

        await self.bot.do_db_query(self.bot, 'UPDATE activemodmails SET reason=? WHERE modmailchnlid=? ', (reason, modmail_entry[1]))
        modmail_channel = self.bot.get_channel(modmail_entry[1])
        modmail_user = self.bot.get_user(modmail_entry[0])

        mod_reason_updated_msg = await modmail_channel.send(embed=update_notice_embed)
        user_reason_updated_msg = await modmail_user.send(embed=update_notice_embed)
        await mod_reason_updated_msg.pin()
        await user_reason_updated_msg.pin()

    @modmail.error
    async def modmail_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original

    @mod_open_modmail.error
    async def mod_open_modmail_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        if isinstance(error, discord.Forbidden) or isinstance(error, AttributeError):
            await ctx.send(embed=self.bot.simple_embed(f"Error: bot probably can't DM that user. ({error})"))
        elif isinstance(error, asyncio.TimeoutError):
            await ctx.send(embed=self.bot.simple_embed(f'Timed out. Use the command `;modmail open <user> [reason]` to try again. ({error})'))
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=self.bot.simple_embed(f'Error: Missing a required argument. Proper syntax: `;modmail open <user> [reason]`. ({error})'))
        elif isinstance(error, discord.HTTPException):
            if error.code == 50035:
                await ctx.send(embed=self.bot.simple_embed(f'Error: Your message or reason was too long to send. If a modmail channel is open, please use it as-is and send your message again (but shorter). Otherwise, run this command again with a shorter message. ({error})'))
            elif error.code == 50007:
                await ctx.send(embed=self.bot.simple_embed(f"Error: Haha, very funny. A bot cannot DM another bot. ({error})"))
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(embed=self.bot.simple_embed(f'Error: member not found. ({error})'))
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send(embed=self.bot.simple_embed('Error: command cannot be used in DMs.'))
        elif isinstance(error, commands.CheckFailure):
            # No need to handle the case of a blacklisted user as this is already handled by the group error.
            await ctx.send(embed=self.bot.simple_embed('You may not use this command.'))
        else:
            # All other errors not returned come here. And we can just print the default Traceback.
            await ctx.send(embed=self.bot.simple_embed(f'Something went wrong: {error}'))
            print('Ignoring exception in command {}:'.format(
                ctx.command), file=stderr)
            print_exception(
                type(error), error, error.__traceback__, file=stderr)

    @closemodmail.error
    async def closemodmail_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        if isinstance(error, TypeError):
            await ctx.send(embed=self.bot.simple_embed(f"Error: You probably aren't in a modmail. ({error})"), delete_after=5.0)
            await ctx.message.delete(delay=4.75)
        elif isinstance(error, discord.HTTPException):
            if error.code == 50035:
                await ctx.send(embed=self.bot.simple_embed(f'Error: Reason is too long– change the reason to a shorter one, then close the modmail. ({error})'))
        elif isinstance(error, discord.Forbidden):
            await ctx.send(embed=self.bot.simple_embed(f"Note: Modmail closed, but couldn't DM the user to notify them. ({error})"))
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(embed=self.bot.simple_embed(f"On cooldown: You can't use this command for another {round(error.retry_after)} seconds. This is probably because you have very recently closed a different modmail. You can ask a moderator to close this modmail for you if that's convenient."))
        elif isinstance(error, AttributeError):
            await ctx.send(embed=self.bot.simple_embed(f'Error: Modmail channel was probably already deleted. Modmail has probably still been closed, though. ({error})'))
        else:
            # All other errors not returned come here. And we can just print the default Traceback.
            await ctx.send(embed=self.bot.simple_embed(f'Something went wrong: {error}'))
            print('Ignoring exception in command {}:'.format(
                ctx.command), file=stderr)
            print_exception(
                type(error), error, error.__traceback__, file=stderr)

    @modmailreason.error
    async def modmailreason_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        if isinstance(error, TypeError):
            await ctx.send(embed=self.bot.simple_embed(f"Error: You probably aren't in a modmail. ({error})"), delete_after=5.0)
            await ctx.message.delete(delay=4.75)
        elif isinstance(error, discord.HTTPException):
            if error.code == 50035:
                await ctx.send(embed=self.bot.simple_embed(f'Error: Reason is too long– please use this command again with a shorter reason. ({error})'))
            if error.code == 30003:
                await ctx.send(embed=self.bot.simple_embed(f'Note: Pinning the reason-change notice failed for either the user or for moderators. The reason was still changed. Unpin some older messages if you want newer reasons to be pinned. ({error})'))
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=self.bot.simple_embed(f'Error: Missing a required argument. Proper syntax: `;modmail reason <reason>`. ({error})'))
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(embed=self.bot.simple_embed(f"On cooldown: You can't change this modmail's reason again for another {round(error.retry_after)} seconds."))
        elif isinstance(error, discord.Forbidden):
            if ctx.guild is None:
                await ctx.send(embed=self.bot.simple_embed(f"Note: Reason was changed, but bot probably does not have permissions to pin messages in the mod's modmail channel. Please contact a moderator. ({error})"))
            else:
                await ctx.send(embed=self.bot.simple_embed(f"Note: Changed the reason, but couldn't DM the user– they have probably blocked the bot. ({error})"))
        else:
            # All other errors not returned come here. And we can just print the default Traceback.
            await ctx.send(embed=self.bot.simple_embed(f'Something went wrong: {error}'))
            print('Ignoring exception in command {}:'.format(
                ctx.command), file=stderr)
            print_exception(
                type(error), error, error.__traceback__, file=stderr)
    # endregion


def setup(bot: commands.Bot):
    bot.add_cog(Modmail(bot))
