import discord
from discord.ext import commands
import aiosqlite
import asyncio
import os


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

        c = await self.bot.conn.execute('SELECT * FROM activemodmails')
        full_activemodmails_table = await c.fetchall()
        await self.bot.conn.commit()

        showtable_filename = f'{ctx.message.created_at}-contents-of-activemodmails.txt'

        with open(showtable_filename, 'w') as showtable_txt_file:
            showtable_txt_file.write('userid, modmailchnlid, reason\n\n')
            for myrow in full_activemodmails_table:
                showtable_txt_file.write(f'{myrow}\n')
            showtable_filename_with_path = showtable_txt_file.name

        dpy_compatible_showtable_file = discord.File(
            showtable_filename_with_path)
        await ctx.send(content=f'Current contents of activemodmails table:', file=dpy_compatible_showtable_file)

        os.remove(showtable_filename_with_path)

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

        c = await self.bot.conn.cursor()
        await c.execute('SELECT * FROM activemodmails WHERE userid=?', (user_id,))
        my_rows = await c.fetchall()
        my_str = '```userid, modmailchnlid, reason (log not shown, use showdb)\n\n'
        for row in my_rows:
            my_str += f'({row[0]}, {row[1]}, {row[2]})\n'
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

                await c.execute('DELETE FROM activemodmails WHERE userid=?', (user_id,))
                await self.bot.conn.commit()

                await ctx.send('Done.')

            elif str(reaction) in cancel_send:  # if user cancels
                await ctx.send('Cancelled.')

        except asyncio.TimeoutError:  # if 30 seconds pass without user confirming or canceling
            await ctx.send('Timed out, process cancelled.')


def setup(bot: commands.Bot):
    """Add this cog to the bot."""
    bot.add_cog(DevCommands(bot))
