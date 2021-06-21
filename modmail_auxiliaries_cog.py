import discord
from discord.ext import commands
import aiosqlite
import asyncio
import os

class Modmail_auxiliaries(commands.Cog):
    "Developer commands providing common shortcuts to make the testing and development of the modmail setup easier. Currently, these commands will only respond to LonelyPenguin."

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def cog_check(self, ctx):
        return ctx.message.author.id == 305704400041803776

    @commands.command()
    async def deletemanychannels(self, ctx, *, list_of_ids: str):
        "A command that deletes all channels from IDs in a list. List must be structured as '[id, id, id]', without quotes. This command is meant for use in development, as testing of the modmail system often leaves behind orphaned modmail channels. Not designed or tested for widespread use. Only responds to LonelyPenguin."
        ids_actual_int_list = list_of_ids.split()
        for chnl_id in ids_actual_int_list:
            fated_to_die_chnl = self.bot.get_channel(int(chnl_id))
            await asyncio.sleep(1)
            await fated_to_die_chnl.delete()
        await ctx.message.add_reaction('👍')

    @commands.command()
    async def showdb(self, ctx):
        "A command that shows the current state of the activemodmails table as a file upload to the channel it is used in. Only meant for use in development, to detect duplicate modmails and the like. Logs of modmail content are contained in this table, so the command may reveal sensitive information. Not designed or tested for widespread use. Only responds to LonelyPenguin."

        c = await self.bot.conn.execute('SELECT * FROM activemodmails')
        full_activemodmails_table = await c.fetchall()
        await self.bot.conn.commit()
        

        showtable_filename = f'{ctx.message.created_at}-contents-of-activemodmails.txt'

        with open(showtable_filename, 'w') as showtable_txt_file:
            showtable_txt_file.write('userid, modmailchnlid, reason, msglog\n\n')
            for myrow in full_activemodmails_table:
                showtable_txt_file.write(f'{myrow}\n')
            showtable_filename_with_path = showtable_txt_file.name

        dpy_compatible_showtable_file = discord.File(showtable_filename_with_path)
        await ctx.send(content=f'Current contents of activemodmails table:', file=dpy_compatible_showtable_file)

        os.remove(showtable_filename_with_path)

    
    @commands.command(aliases = ['reload', 'reloadcog'])
    async def reloadext(self, ctx, cog_to_reload):
        "A command which reloads an extension (a file called by the main bot process). Extensions contain cogs, which are different categories of functionality and commands. This command provides the ability to reload an extension after making changes to its code, without relaunching the whole bot. cog_to_reload must be the file name of the extension, without file path or .py file extension. Not designed or tested for widespread use. Only responds to LonelyPenguin."
        try:
            self.bot.reload_extension(cog_to_reload)
            await ctx.send(f'Reloaded {cog_to_reload}!')
        except Exception as e:
            await ctx.send(f'Something went wrong: {e}')


def setup(bot: commands.Bot):
    bot.add_cog(Modmail_auxiliaries(bot))