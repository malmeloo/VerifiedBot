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

msgcount = {}
ignored = []

updated = datetime.now().strftime('%x %X GMT+0')

#SETTINGS
minimum = 100			#min msgs a user has to send each day

#REGULAR FUNCTIONS
async def assign_role(user_id):
	"""assign role here"""
	member = rc24.get_member(user_id)

	if not verified_role in member.roles:
		await member.add_roles(verified_role, reason=f'[VERIFY] Added {verified_role} role to user.')
		print(f"Added role to {member}")

async def remove_role(user_id):
	"""remove role here"""
	member = rc24.get_member(user_id)

	if verified_role in member.roles:
		await member.remove_roles(verified_role, reason=f'[UNVERIFY] Removed {verified_role} role from user.')
		print(f"Removed role from {member}")

#OWNER COMMAND(S)
@client.command(hidden=True, name='eval', description="Eval some code.")
@commands.is_owner()
async def _eval(ctx, *, body: str):
	env = {
		'client': client,
		'ctx': ctx,
		'channel': ctx.channel,
		'author': ctx.author,
		'guild': ctx.guild,
		'message': ctx.message
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
@client.command(description="What do you think this is..?")
async def help(ctx):
	"""Guess what this is"""
	em = discord.Embed(color=discord.Color.green(), title='Commands list')
	for cmd in client.commands:
		try:
			if await cmd.can_run(ctx):
				em.add_field(name=cmd.signature, value=cmd.description)
		except commands.CommandError:
			pass
	em.set_footer(text="Only commands you can use are shown.")

	await ctx.send(embed=em)

@client.group(description="Check a user's current verification status.", invoke_without_command=True)
async def check(ctx, user : discord.Member = None):
	"""Check the current addition/removal status"""
	if not user:
		user = ctx.author

	if user.id in msgcount.keys():
		amount = msgcount[user.id]
	else:
		amount = 0

	embed = discord.Embed(title='Status')
	embed.add_field(name='Messages sent', value=amount)
	embed.add_field(name='Eligible for verification', value=msgcount[user.id] >= minimum)
	embed.add_field(inline=True, name='Currently verified', value=verified_role in user.roles)

	embed.set_footer(text="Next daily check:")
	now = datetime.now()
	embed.timestamp = datetime(now.year, now.month, now.day, hour=23, minute=59, second=59)

	embed.set_thumbnail(url=user.avatar_url)
	embed.color = discord.Color.green() if msgcount[user.id] >= minimum else discord.Color.red()

	await ctx.send(f':white_check_mark: Stats of `{user}`:', embed=embed)

@check.command(description="Check all users for verification.")
@commands.has_permissions(kick_members=True)
async def all(ctx):
	eligible_users = [str(ctx.guild.get_member(x)) for x in msgcount.keys() if msgcount[x] >= minimum]

	embed = discord.Embed(title="Server status overview")
	embed.add_field(name='Total registered users', value=len(msgcount.keys()))
	embed.add_field(name='Users eligible for verification', value='- ' + '\n - '.join(eligible_users) if eligible_users else "None")

	embed.set_footer(text="Next daily check:")
	now = datetime.now()
	embed.timestamp = datetime(now.year, now.month, now.day, hour=23, minute=59, second=59)

	embed.color = discord.Color.green()
	embed.set_thumbnail(url=ctx.guild.icon_url)

	await ctx.send(":white_check_mark: Fetched global server verification stats!", embed=embed)

@client.command(description="Manually verify a user.")
@commands.has_permissions(kick_members=True)
async def verify(ctx, user : discord.Member = None):
	"""Temporarily verify a user"""
	if not user:
		user = ctx.author

	try:
		await assign_role(user.id)
		await ctx.send(f':white_check_mark: Temporarily verified the user `{user}`!')
	except Exception as err:
		await ctx.send(f':x: An error has occured while trying to verify the user `{user}`:\n```{err}```')

@client.command(description="Manually unverify a user.")
@commands.has_permissions(kick_members=True)
async def unverify(ctx, user : discord.Member = None):
	"""Temporarily unverify a user"""
	if not user:
		user = ctx.author

	try:
		await remove_role(user.id)
		await ctx.send(f':white_check_mark: Temporarily unverified `{user}`!')
	except Exception as err:
		await ctx.send(f':x: An error has occured while trying to remove the role from `{user}`:\n```{err}```')

@client.command(description="Leave someone out of the daily verification process.")
@commands.has_permissions(kick_members=True)
async def ignore(ctx, user : discord.Member = None):
	"""Ignore a user in the daily process (excludes manual checks)"""
	if not user:
		user = ctx.author

	ignored.append(user.id)
	await ctx.send(f':white_check_mark: Now ignoring the user `{user}` until the next reboot.')

@client.command(description="Make the bot automatically check this user again.")
@commands.has_permissions(kick_members=True)
async def unignore(ctx, user : discord.Member = None):
	"""Unignore a user in the daily process"""
	if not user:
		user = ctx.author

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
	elif isinstance(error, commands.CommandNotFound):
		await ctx.message.add_reaction("\U00002753")
	else:
		traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

#EVENTS
@client.event
async def on_message(message):
	if message.author.bot:
		return
	if message.channel.id == 326148489828368385 and not message.content.startswith('v!'): #ignore #random
		return

	if message.author.id in msgcount.keys():
		msgcount[message.author.id] += 1
	else:
		msgcount[message.author.id] = 1

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
	global msgcount
	global updated

	await client.wait_until_ready()
	await asyncio.sleep(10) #wait until it's _really_ ready
	while not client.is_closed():

		print("Verification process started")
		for i in [x for x in rc24.members if not x.id in ignored]:
			if i.id in msgcount.keys() and msgcount[i.id] >= minimum:
				await assign_role(i.id)
			else:
				await remove_role(i.id)
		print("Verification process ended")

		msgcount = {} #reset stats for the day

		now = datetime.now()
		updated = now.strftime('%x %X GMT+0')
		delta = datetime(now.year, now.month, now.day, hour=0, minute=20, second=0) - now

		await asyncio.sleep(delta.seconds)

client.loop.create_task(update())
client.run(os.environ['BOT_TOKEN'])
