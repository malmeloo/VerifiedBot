import discord
import pickle
import datetime
import os
import asyncio

client = discord.Client()

file = open("dict.pickle","rb")
data = pickle.load(file)

"""BEGIN OF SETTINGS"""
msgminimum = 100					#average minimum of messages a user has to send in  a day. Default is 100.
updaterate = 60						#the rate data should get updated in minutes. Default is every hour (60).
prunerate = 24						#the rate members should get their roles pruned in hours. Default is every day (24).
"""END OF SETTINGS"""

deletequery = []
assignquery = []

def calc_days_to_now(date):
	delta = get_current_date() - date
	return delta.days
	
def get_current_date():
	now = datetime.datetime.now()
	parsed = datetime.date(now.year, now.month, now.day)
	return parsed

async def data_update():
	await client.wait_until_ready()
	while not client.is_closed:
		deletequery = []
		assignquery = []
		print()
		print("Starting role calculation...")
		print("-" * 30)
		for member in data.keys():
			if int(data[member]["msgs"] / calc_days_to_now(data[member]["talkingsince"]) >= msgminimum:
				if "Verified" in client.get_user_info(member).roles:
					pass
				else:
					assignquery.append(member)
			else:
				if "Verified" in client.get_user_info(member).roles:
					deletequery.append(member)
				else:
					pass
		print("{} members for deletion of role: ".format(str(len(deletequery))) + str(deletequery))
		print("{} members for addition of role: ".format(str(len(assignquery))) + str(assignquery))
		
		# update file with new dict so it will survive reboots
		file = open("dict.pickle","wb")
		pickle.dump(data, file)
		file.close()
		await asyncio.sleep(updaterate * 60)
		
async def role_update():
	await client.wait_until_ready()
	while not client.is_closed:
		print()
		print("-" * 30)
		print("Starting role updating...")
		for prunemember in deletequery:
			"""<REMOVE ROLE>"""
			pass #for now
		for addmember in assignquery:
			"""<ASSIGN ROLE>"""
			pass #for now
		print("Done! Updated a total of {} members.".format(str(len(assignquery)+len(deletequery))))
		await asyncio.sleep(prunerate * 3600)
		
		
@client.event()
async def on_ready():
	print("Ready as {0}! (ID: {1})".format(client.user.name, client.user.id))

@client.event()
async def on_message(message):
	if message.channel.id == '' or message.channel.name == 'random':
		return
	if not message.user.id in data.keys():
		data[message.user.id] = {"talkingsince":get_current_date(), "msgs":1}
	else:
		data[message.user.id]["msgs"] += 1

client.loop.create_task(data_update())
client.loop.create_task(role_update())

client.run(os.environ['BOT_TOKEN'])