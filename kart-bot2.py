import aiohttp, asyncio, discord, json, os, pathlib, psutil, re, subprocess, time
from discord import Webhook
from discord.ext import commands
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# LOADS THE CONFIG FILE

with open(
	str(pathlib.Path(__file__).parent.absolute()) + "/kart-bot2-config.json", "r"
) as f:
	config = json.loads(f.read())

# LOADS THE BOT SETTINGS IN THE CONFIG FILE

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=config["prefix"], intents=intents, help_command=None, case_insensitive=True)

# ROLES WITH ADMIN PERMISSIONS

def isAdmin(ctx):
	for role in ctx.author.roles:
		if role.name in config["allowedRoles"]:
			return True
	return False

# !IP COMMAND

@bot.command()
async def ip(ctx):
	embed = discord.Embed(title=":ringracers: IPs dos servidores",
		description="Confira os endereços IP de servidores Ring Racers da nossa equipe e de parceiros da comunidade.",
		colour=0x000099E1)
	embed.add_field(name="SRBR Interlagos",
		value="```i.srb2kbr.com```",
		inline=False)
	embed.add_field(name="The Meowers (@milothepower)",
		value="```168.138.124.10```",
		inline=False)
	embed.set_thumbnail(url="https://wiki.srb2.org/w/images/c/c8/Sonic%26TailsPortrait.png")
	
	await ctx.send(embed=embed)

# !COMMAND COMMAND

@bot.command(checks=[isAdmin])
async def command(ctx, *, cmd):
	path = config["serverFolderPath"] + f"tmp/tmp{ctx.message.id}.cfg"
	with open(path, "w") as f:
		f.write(cmd)
	os.system(
		f"tmux send-keys -t {config['tmuxName']} \"exec tmp/tmp{ctx.message.id}.cfg\" ENTER"
	)
	await ctx.send(f"O comando foi executado em {config['serverName']}.")

# GAME TO DISCORD BRIDGE
# Made with help from Goulart, Matt and Uotlaf

actualMap = ''
pastDate = 0

class logChangesDetect(FileSystemEventHandler):
	def on_modified(self, event):
		global pastDate

		nowDate = round(time.time())
		if nowDate - pastDate > 1:
			pastDate = nowDate
			if event.is_directory:
				return
			elif event.event_type == 'modified':
				asyncio.run_coroutine_threadsafe(chatBridge(), bot.loop)
		else:
			time.sleep(1)
			self.on_modified(event)

lastLogLine = 0
playerData = []

async def chatBridge():
	global actualMap
	global lastLogLine
	global playerData
	
	if lastLogLine != 0:
		with open(f"{config['serverFolderPath']}{config['logFile']}", 'r') as file:
			for _ in range(lastLogLine - 1):
				next(file)
			for line in file:
				line = line.strip()
				# Detect player messages, except from ~SERVER
				if re.search(r'<(?!~SERVER)(.*?)>\s(.*)', line):
					match = re.search(r'<(?!~SERVER)(.*?)>\s(.*)', line)
					playerName = match.group(1)
					playerMessage = match.group(2)
					async with aiohttp.ClientSession() as session:
						await Webhook.from_url(f"{config['webhookURL']}", session=session).send(
							content=playerMessage,
							username=playerName,
							avatar_url=f"{config['webhookAvatarURL']}default.png"
						)
				lastLogLine += 1
				print(lastLogLine)
	else:
		with open(f"{config['serverFolderPath']}{config['logFile']}", 'rb') as f:
			lastLogLine = sum(1 for _ in f)
			await asyncio.sleep(1)
			await chatBridge()

# DISCORD TO GAME BRIDGE
# Made by Deagahelio

@bot.event
async def on_message(message):
	if not message.content.startswith(config["prefix"]):
		if message.channel.id == config["chatBridgeChannelID"]:
			if not message.author.bot:
				text = (
					message.clean_content.replace('"', "")
					.replace("ç", "c")
					.replace("á", "a")
					.replace("ã", "a")
					.replace("â", "a")
					.replace("à", "a")
					.replace("é", "e")
					.replace("ê", "e")
					.replace("í", "i")
					.replace("ó", "o")
					.replace("õ", "o")
					.replace("ô", "o")
					.replace("ú", "u")
					.replace("^", "")
					.replace("\n", "")
					.replace(";", "")
				)
				path = config["serverFolderPath"] + f"tmp/tmp{message.id}.cfg"
				with open(path, "w") as f:
					f.write(f"say [D] {message.author.name}: {text}")
				os.system(
					f"tmux send-keys -t {config['tmuxName']} \"exec tmp/tmp{message.id}.cfg\" ENTER"
				)
	# If the commands channel is in fact a channel, not a thread, use: elif message.channel.id == config["botCommandsChannelID"] or [...]:
	elif (isinstance(message.channel, discord.Thread) and message.channel.id == config["botCommandsChannelID"]) or (any(role.name in config["allowedRoles"] for role in message.author.roles)):
		await bot.process_commands(message)

# DELETE TEMPORARY FILES
# Made by Deagahelio

async def deleteTemp():
	while True:
		files = [
			config["serverFolderPath"] + "tmp/" + f
			for f in os.listdir(config["serverFolderPath"] + "tmp")
		]
		files.sort(key=os.path.getctime)
		for f in files[:-3]:
			os.system("rm " + f)
		await asyncio.sleep(10)

# DISCORD BOT CALL FUNCTION

@bot.event
async def on_ready():
	await bot.change_presence(activity=discord.Game(name="como um anel!"))
	# START CHAT BRIDGE
	bot.loop.create_task(deleteTemp())
	event_handler = logChangesDetect()
	observer = Observer()
	observer.schedule(event_handler, f"{config['serverFolderPath']}logs", recursive=False)
	observer.start()

# START DISCORD BOT

bot.run(config["token"])