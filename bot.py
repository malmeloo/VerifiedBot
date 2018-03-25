import discord
from discord.ext.commands import Bot
from discord.ext import commands
import logging
import traceback
import os
from contextlib import redirect_stdout
import io
import sys
import textwrap
import asyncio
from datetime import datetime

logging.basicConfig(level=logging.INFO)

client = Bot(command_prefix='v!')
client.remove_command('help')

cache = []
ignored = []

updated = datetime.now().strftime('%x %X GMT+0')

#SETTINGS
updaterate = 24			#update roles in h
minimum = 100			#min msgs a user has to send each day

#REGULAR FUNCTIONS
async def assign_role(user_id):
	"""assign role here"""
	member = rc24.get_member(user_id)
	await member.add_roles(verified_role, reason=f'[VERIFY] Added {verified_role} role to user.')

async def remove_role(user_id):
	"""remove role here"""
	member = rc24.get_member(user_id)
	await member.add_roles(verified_role, reason=f'[UNVERIFY] Removed {verified_role} role from user.')

#OWNER COMMAND(S)
@client.command(hidden=True, name='eval')
@commands.is_owner()
async def _eval(ctx, *, body: str):
	env = {
		'client': client,
		'ctx': ctx,
		'channel': ctx.channel,
		'author': ctx.author,
		'guild': ctx.guild,
		'message': ctx.message,
		'ignored': ignored,
		'cache': cache
	}

	env.update(globals())
	stdout = io.StringIO()

	to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

	try:
		exec(to_compile, env)
	except Exception as e:
		return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

	func = env['func']
	try:
		with redirect_stdout(stdout):
			ret = await func()
	except Exception as e:
		value = stdout.getvalue()
		await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
	else:
		value = stdout.getvalue()
		try:
			await ctx.message.add_reaction('\u2705')
		except:
			pass

		if ret is None:
			if value:
				await ctx.send(f'```py\n{value}\n```')
		else:
			await ctx.send(f'```py\n{value}{ret}\n```')

#REGULAR COMMANDS
@client.command()
async def help(ctx):
	"""Guess what this is"""
	em = discord.Embed(color=discord.Color.green(), title='Commands list')
	for cmd in [x for x in client.commands if x.can_run(ctx)]:
		em.add_field(name=cmd.signature, value=cmd.description)
	em.set_footer(text="Only commands you can use are shown.")

	await ctx.send(embed=em)

@client.command(description="Check the verification status of a user.")
async def check(ctx, user : discord.Member):
	"""Check the current addition/removal status"""
	messages = [x for x in cache if x.author.id == user.id]
	eligble = len(messages) >= minimum

	embed = discord.Embed(title='Status')
	embed.add_field(name='Messages sent', value=len(messages))
	embed.add_field(name='Eligble for verification', value=eligble)

	if eligble:
		embed.color = discord.Color.green()
	else:
		embed.color = discord.Color.red()

	await ctx.send(f':white_check_mark: Stats of `{user}` since {updated}:', embed=embed)

@client.command(description="Manually verify someone.")
@commands.has_permissions(kick_members=True)
async def verify(ctx, user : discord.Member):
	"""Temporarily verify a user"""
	try:
		await assign_role(user.id)
		await ctx.send(f':white_check_mark: Temporarily verified the user `{user}`!')
	except Exception as err:
		await ctx.send(f':x: An error has occured while trying to verify the user `{user}`:\n```{err}```')

@client.command(description="Manually unverify someone.")
@commands.has_permissions(kick_members=True)
async def unverify(ctx, user : discord.Member):
	"""Temporarily unverify a user"""
	try:
		await remove_role(user.id)
		await ctx.send(f':white_check_mark: Temporarily unverified `{user}`!')
	except Exception as err:
		await ctx.send(f':x: An error has occured while trying to remove the role from `{user}`:\n```{err}```')

@client.command(description="Leave someone out of the daily verification process.")
@commands.has_permissions(kick_members=True)
async def ignore(ctx, user : discord.Member):
	"""Ignore a user in the daily process (excludes manual checks)"""
	ignored.append(user.id)
	await ctx.send(f':white_check_mark: Now ignoring the user `{user}` until the next reboot.')

@client.command(description="Make someone count in the auto-verification process again.")
@commands.has_permissions(kick_members=True)
async def unignore(ctx, user : discord.Member):
	"""Unignore a user in the daily process"""
	ignored.remove(user.id)
	await ctx.send(f':white_check_mark: Stopped ignoring the user `{user}`.')

#ERRORS
@client.event
async def on_command_error(ctx, error):
	if isinstance(error, commands.errors.BadArgument):
		await ctx.send(':x: I couldn\'t find a user with that name!')
	elif isinstance(error, (commands.MissingPermissions, commands.NotOwner)):
		await ctx.send(':x: You do not have permission to use this command!')
	elif isinstance(error, commands.MissingRequiredArgument):
		await ctx.send(f':x: {error}')
	else:
		traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

#EVENTS
@client.event
async def on_message(message):
	if message.author.bot:
		return
	if message.channel.id == 326148489828368385 and not message.content.startswith('v!'): #ignore #random
		return

	cache.append(message)

	await client.process_commands(message)

@client.event
async def on_ready():
	global rc24
	global verified_role

	rc24 = client.get_guild(206934458954153984)
	verified_role = discord.utils.get(rc24.roles, name="Active")

	print(discord.__version__)
	print('------------------')
	print('Logged in as:')
	print(client.user.name)
	print(client.user.id)
	print('------------------')

#TASKS
async def update():
	await client.wait_until_ready()

	while not client.is_closed:

		members = rc24.members

		for member in members:
			amount = len([msg for msg in cache if msg.author.id == member.id and not msg.author.id in ignored])
			eligble = amount >= minimum

			try:
				if eligble and (not verified_role in member.roles):
					await assign_role(member.id)
				elif (not eligble) and (verified_role in member.roles):
					await remove_role(member.id)
			except discord.Forbidden:
				pass
		cache = [] #reset the cache
		updated = datetime.now().strftime('%x %X GMT+0')

		await asyncio.sleep(updaterate * 3600)

client.loop.create_task(update())
client.run(os.environ['BOT_TOKEN'])
