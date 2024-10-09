import aiohttp, asyncio, discord, json, os, pathlib, psutil, re, subprocess, time
from discord import Webhook
from discord.ext import commands
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# LOADS THE CONFIG FILE

with open(
	str(pathlib.Path(__file__).parent.absolute()) + "/kartbot2-config.json", "r"
) as f:
	config = json.loads(f.read())
	
# LOADS THE BOT CONFIG IN THE CONFIG FILE

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=config["prefix"], intents=intents, help_command=None, case_insensitive=True)

# ROLES WITH COMMAND PERMISSIONS

def isAdmin(ctx):
	for role in ctx.author.roles:
		if role.name in config["allowedRoles"]:
			return True
	return False

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

# !RESTART COMMAND

@bot.command(checks=[isAdmin])
async def restart(ctx):
	os.system(f"pkill {config['serverExecutableName']} && tmux kill-session -t {config['tmuxName']} && bash {config['serverScriptPath']}")
	await ctx.send(f"{config['serverName']} foi reiniciado.")

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

# DISCORD -> GAME BRIDGE
# Original code by Deagahelio

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
	# If the commands channel is really a channel, not a thread, use: message.channel.id == config["botCommandsChannelID"]
	elif (isinstance(message.channel, discord.Thread) and message.channel.id == config["botCommandsChannelID"]) or (any(role.name in config["allowedRoles"] for role in message.author.roles)):
		await bot.process_commands(message)

# GAME -> DISCORD BRIDGE
# Made with help from Goulart, Matt and Uotlaf

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
	
	if lastLogLine !=0:
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
						# Looks for the message owner's data
						for player in playerData:
							# Check if message owner is in the dictionary AND has a character set
							if player["playerName"] == playerName and "playerCharacter" in player:
								playerCharacter = player["playerCharacter"]
								playerColor = player["playerColor"]
								# Send message on the bridge
								await Webhook.from_url(f"{config['webhookURL']}", session=session).send(
									content=playerMessage,
									username=playerName,
									avatar_url=f"{config['webhookAvatarURL']}{playerSkin}_{playerColor}.png"
								)
								break
							# If the message owner's not on dictionary/has a character set, send message without avatar
							else:
								await Webhook.from_url(f"{config['webhookURL']}", session=session).send(
									content=playerMessage,
									username=playerName,
									avatar_url=f"{config['webhookAvatarURL']}default.png"
								)
				# Detect "Sonic has finished the race." message
				elif re.search(r'(.*)\s+has\s+finished\s+the\s+race.', line):
					match = re.search(r'(.*)\s+has\s+finished\s+the\s+race.', line)
					playerName = match.group(1)
					# Send message on the bridge
					await bot.get_channel(config["chatBridgeChannelID"]).send(
						f"***{playerName}** terminou a corrida*"
					)
				# Detect "The round has ended." message
				elif line == "The round has ended.":
					await bot.get_channel(config["chatBridgeChannelID"]).send(
						"*A partida terminou*"
					)
				# Detect 'Map is now "RR_EXAMPLE: Example Zone"' message
				elif re.search(r'Map is now "(.*): ([^"]+)"', line):
					match = re.search(r'Map is now "(.*): ([^"]+)"', line)
					mapID = match.group(1)
					mapName = match.group(2)
					# Send message on the bridge
					embed = discord.Embed(title="Acelerando para a próxima partida!", description=f"Fase: **{mapName}**\nID: **{mapID}**", colour=0x000099E1)
					embed.set_image(url=f"{config['mapImagesURL']}{mapID}.png")
					await bot.get_channel(config["chatBridgeChannelID"]).send(
						embed=embed
					)
					# Update the actual map value for !info command
					actualMap = f"{mapName};{mapID}"
				# Detect "Fulano entered the game" message
				elif re.search(r'\*(.*)\s+entered\s+the\s+game', line):
					match = re.search(r'\*(.*)\s+entered\s+the\s+game', line)
					playerName = match.group(1)
					# Send message on the bridge
					await bot.get_channel(config["chatBridgeChannelID"]).send(
						f"***{playerName}** se juntou ao jogo*"
					)
					# Looks for the message owner's data
					for player in playerData:
						if player["playerName"] == playerName:
							player["isSpectator"] = False
							break
				# Detect "Player left the game" message
				elif re.search(r'\*(.*)\s+left', line):
					match = re.search(r'\*(.*)\s+left', line)
					playerName = match.group(1)
					await bot.get_channel(config["chatBridgeChannelID"]).send(
						f"***{playerName}** saiu do servidor*"
					)
					# Delete the entire player data, rewriting the dictionary without the player that left
					playerInfo = [
						player for player in playerInfo 
						if player["playerName"] != f"{playerName}"
					]
				# Detect "Player joined the game" message
				elif re.search(r'\*(.*)\s+has\s+joined', line):
					match = re.search(r'\*(.*)\s+has\s+joined', line)
					playerName = match.group(1)
					await bot.get_channel(config["chatBridgeChannelID"]).send(
						f"***{playerName}** entrou no servidor*"
					)
					playerInfo.append(
						{
							"playerName": f"{playerName}",
							"isSpectator": True
						}
					)
				# Detect "Player renamed to AnotherPlayer" message
				elif re.search(r'\*(.*)\s+renamed\s+to\s+(.*)', line):
					match = re.search(r'\*(.*)\s+renamed\s+to\s+(.*)', line)
					oldPlayerName = match.group(1)
					newPlayerName = match.group(2)
					await bot.get_channel(config["chatBridgeChannelID"]).send(
						f"***{oldPlayerName}** mudou seu próprio nome para **{newPlayerName}***"
					)
					# Looks for the message owner's data
					for player in playerData:
						if player["playerName"] == oldPlayerName:
							player["playerName"] = newPlayerName
							break
				# Detect character and/or color changes
				elif re.search(r'\[CHAR\] \[CHAR_COLOR\] (.*) \[CHAR_SKIN\] (.*) \[NUMBER\] \d+ \[NAME\] (.*)', line):
					match = re.search(r'\[CHAR\] \[CHAR_COLOR\] (.*) \[CHAR_SKIN\] (.*) \[NUMBER\] \d+ \[NAME\] (.*)', line)
					charColor = match.group(1)
					charSkin = match.group(2)
					playerName = match.group(3)
					# Looks for the message owner's data
					for player in playerData:
						if player["playerName"] == PlayerName:
							player["playerCharacter"] = charSkin
							player["playerColor"] = charColor
							break
				# Detect "Player became a spectator" message
				elif re.search(r'\*(.*)\s+became\s+a\s+spectator', line):
					match = re.search(r'\*(.*)\s+became\s+a\s+spectator', line)
					playerName = match.group(1)
					await bot.get_channel(config["chatBridgeChannelID"]).send(
						f"***{playerName}** se tornou um espectador*"
					)
					# Looks for the message owner's data
					for player in playerData:
						if player["playerName"] == PlayerName:
							player["isSpectator"] = True
							break
				lastLogLine += 1
	else:
		with open(f"{config['serverFolderPath']}{config['logFile']}", 'rb') as f:
			lastLogLine = sum(1 for _ in f)
			await asyncio.sleep(1)
			await chatBridge()

# DELETE TEMP FILES
# Original code by Deagahelio

async def delete_tmp():
	while True:
		files = [
			config["serverFolderPath"] + "tmp/" + f
			for f in os.listdir(config["serverFolderPath"] + "tmp")
		]
		files.sort(key=os.path.getctime)
		for f in files[:-3]:
			os.system("rm " + f)
		await asyncio.sleep(10)

# SET DISCORD BOT FUNCTION

@bot.event
async def on_ready():
	await bot.change_presence(activity=discord.Game(name="como um anel!"))
	# START CHAT BRIDGE
	bot.loop.create_task(delete_tmp())
	event_handler = logChangesDetect()
	observer = Observer()
	observer.schedule(event_handler, f"{config['serverFolderPath']}logs", recursive=False)
	observer.start()

# START BOT

bot.run(config["token"])