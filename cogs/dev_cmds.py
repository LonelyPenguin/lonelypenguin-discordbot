import asyncio
from io import StringIO
from os import linesep
from sys import exit

import discord
from discord.ext import commands


class DevCommands(commands.Cog):
    """Developer commands providing common shortcuts to make the testing and development of the bot easier.

    Currently, these commands will only respond to LonelyPenguin.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def cog_check(self, ctx: commands.Context):
        """Ensure that only LonelyPenguin may use these commands."""
        return ctx.message.author.id == 305704400041803776

    @commands.command()
    async def deletemanychannels(self, ctx: commands.Context, *, list_of_ids: str):
        """A command that deletes all channels from IDs in a list.

        List must be structured as '[id, id, id]', without quotes.
        This command is meant for use in development, as testing of the modmail system often leaves behind orphaned modmail channels. Not designed or tested for widespread use. Only responds to LonelyPenguin.
        """

        ids_actual_int_list = list_of_ids.split()
        for chnl_id in ids_actual_int_list:
            fated_to_die_chnl = self.bot.get_channel(int(chnl_id))
            await asyncio.sleep(3)
            await fated_to_die_chnl.delete()
        await ctx.message.add_reaction('👍')

    @commands.command()
    async def showdb(self, ctx: commands.Context):
        """Send a .txt file containing the current state of the activemodmails table.

        Only meant for use in development, to detect duplicate modmails and the like.
        Not designed or tested for widespread use. Only responds to LonelyPenguin.
        """

        full_activemodmails_table = await self.bot.do_db_query(self.bot, 'SELECT * FROM activemodmails', None ,"all")

        paginator = commands.Paginator(prefix='```\nuserid, modmailchnlid, reason\n')

        for my_row in full_activemodmails_table:
            paginator.add_line(str(my_row))

        await ctx.send('Current contents of activemodmails:')
        for page in paginator.pages:
            await ctx.send(page)

    @commands.command(aliases=['reload', 'reloadcog'])
    async def reloadext(self, ctx: commands.Context, cog_to_reload: str):
        """Reloads an extension, specified by the filename.

        Extensions contain cogs, which are different categories of functionality and commands.
        This command provides the ability to reload an extension after making changes to its code,
        without relaunching the whole bot.
        cog_to_reload must be the file name of the extension, without file path or .py file extension.
        Assumes that the cog is in the cogs/ folder.
        Not designed or tested for widespread use. Only responds to LonelyPenguin.
        """

        try:
            self.bot.reload_extension(f'cogs.{cog_to_reload}')
            await ctx.send(f'Reloaded {cog_to_reload}!')
            print(f'\nReloaded extension {cog_to_reload}')
        except Exception as e:
            await ctx.send(f'Something went wrong: {e}')

    @commands.command()
    async def cleandb(self, ctx: commands.Context, user_id: str):
        """Delete all entries tied to the specified user from the activemodmails table.

        Does not delete the modmail channel, create logs, or notify anyone involved. Dangerous.
        Not designed or tested for widespread use. Only responds to LonelyPenguin.
        """

        user_id = int(user_id)

        rows = await self.bot.do_db_query(self.bot, 'SELECT * FROM activemodmails WHERE userid=?', (user_id,), "all")
        my_str = '```userid, modmailchnlid, reason\n\n'
        my_str += '\n'.join([str(row) for row in rows])
        my_str += '```'

        confirm_message = await ctx.send(f'Are you sure you want to delete these entries (tied to <@{user_id}>) from the database? **This will not create logs or notify anyone involved.** It also will not delete the channel. Be certain. \n\n{my_str}')

        confirm_send = ['👍', '✅', '☑️', '✔️', '🆗', '👌']
        cancel_send = ['🚫', '❌', '👎']

        def check_reaction(reaction, user):
            return user == ctx.author and reaction.message.id == confirm_message.id and (str(reaction.emoji) in confirm_send or str(reaction.emoji) in cancel_send)

        try:  # ask for confirmation, create new modmail, and relay message
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check_reaction)

            if str(reaction) in confirm_send:  # if user confirms
                await ctx.send(f'Okay, removing the database entries tied to <@{user_id}>.')

                await self.bot.do_db_query(self.bot, 'DELETE FROM activemodmails WHERE userid=?', (user_id,))

                await ctx.send('Done.')

            elif str(reaction) in cancel_send:  # if user cancels
                await ctx.send('Cancelled.')

        except asyncio.TimeoutError:  # if 30 seconds pass without user confirming or canceling
            await ctx.send('Timed out, process cancelled.')

    @commands.command(name="quit")
    async def quit_bot(self, ctx: commands.Context):
        await ctx.send("Quitting.")
        exit()


def setup(bot: commands.Bot):
    """Add this cog to the bot."""
    bot.add_cog(DevCommands(bot))
