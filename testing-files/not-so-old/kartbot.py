import aiohttp, asyncio, datetime, discord, json, os, pathlib, psutil, re, subprocess, time
from discord import Webhook
from discord.ext import commands
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# CARREGA O ARQUIVO DE CONFIGURAÇÃO

with open(
	str(pathlib.Path(__file__).parent.absolute()) + "/kartbot_config.json", "r"
) as f:
	config = json.loads(f.read())

# CARREGA AS DEFINIÇÕES DO BOT NO ARQUIVO DE CONFIGURAÇÃO

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=config["prefix"], intents=intents, help_command=None, case_insensitive=True)

# CARGOS COM PERMISSÃO DE COMANDOS

def is_admin(ctx):
	for role in ctx.author.roles:
		if role.name in config["allowed_roles"]:
			return True
	return False

# COMANDO !IP

@bot.command()
async def ip(ctx):
	embed = discord.Embed(title=":ringracers: IPs dos servidores",
		description="Confira os endereços IP de servidores Ring Racers da nossa equipe e de parceiros da comunidade.",
		colour=0x000099E1)
	embed.add_field(name="SRB2KBR Interlagos",
		value="```i.srb2kbr.com```",
		inline=False)
	embed.add_field(name="The Meowers (@milothepower)",
		value="```168.138.124.10```",
		inline=False)
	embed.set_thumbnail(url="https://wiki.srb2.org/w/images/c/c8/Sonic%26TailsPortrait.png")
	
	await ctx.send(embed=embed)

# COMANDO !INFO
# Trecho original por Deagahelio, Goulart e Fafabis

jogadoresOnline = []
faseAtual = ""

def listarJogadores(jogadoresOnline):
    listaJogadores = ''
    for jogador in jogadoresOnline:
        if jogadoresOnline[jogador][isSpectator]:
            listaJogadores = listaJogadores + "*" + jogador + "*\n"
        else:
            listaJogadores = listaJOgadores + jogador + "\n"
    return listaJogadores

@bot.command()
async def info(ctx):
	try:
		# Existem múltiplos processos do jogo, essa linha obtém o processo mais antigo a partir do PID menor
		pidProcessoJogo = min(list(map(int, subprocess.check_output(['pidof', config['server_executable_name']).decode().strip().split())))
		statusServidor = "✅ ON"
	except subprocess.CalledProcessError:
		statusServidor = "❌ OFF"
	usoCPU = psutil.cpu_percent()
	usoRAM = psutil.virtual_memory().percent
	if statusServidor == "✅ ON":
		tempoAtivo = datetime.timedelta(seconds=psutil.time.time() - psutil.Process(pidProcessoJogo).create_time())
		if config["display_gamemode"]:
			if subprocess.check_output(['pgrep', '-f', 'KL_bp'):
				modoDeJogo = "Batalha"
			else:
				modoDeJogo = "Corrida"
        os.system(
            f"tmux send-keys -t {config['tmux_name']} \"gametype\" ENTER"
        )
		with open("/home/ubuntu/.ringracers/latest-log.txt", 'r') as file:
            # Move o ponteiro até o fim do arquivo
            file.seek(0, 2)
            tamanhoArquivo = file.tell()
            # Começa do fim do arquivo
            posicao = tamanhoArquivo - 1
            linha = ""
            while posicao >= 0:
                file.seek(posicao)
                # Lê o caractere atual
                caractereAtual = file.read(1)
                # Move o ponteiro pro caractere anterior
                posicao -= 1
                # Se o caractere atual é um \n, chegou ao fim da linha
                if caractereAtual == '\n':
                    # Checa se a linha é "Current gametype is ..."
                    if re.match(r'Current\s+gametype\s+is\s+(.*)', linha):
						match = re.match(r'Current\s+gametype\s+is\s+(.*)', linha)
                        modoJogo = match.group(1)
                        break
                    # Move pra linha anterior, limpando a variavel
                    linha = ""
                else:
                    # Adiciona o caractere atual a linha
                    linha = caractereAtual + linha
        embed = discord.Embed(colour=0x00ff00)
        embed.add_field(name="Estado",
                value=statusServidor,
                inline=True)
        embed.add_field(name="Tempo ativo",
                value=tempoAtivo,
                inline=True)
        embed.add_field(name="",
                value="",
                inline=False)
        embed.add_field(name="CPU",
                value=usoCPU,
                inline=True)
        embed.add_field(name="RAM",
                value=usoRAM,
                inline=True)
        embed.add_field(name="Modo de jogo",
                value=modoJogo,
                inline=False)
        embed.add_field(name=f"Jogadores ({len(jogadoresOnline)}/{config['server_max_players']})",
                value="",
                inline=False)
        await bot.get_channel(config["chat_bridge_channel_id"]).send(
            embed=embed
        )

# COMANDO !COMMAND

@bot.command(checks=[is_admin])
async def command(ctx, *, cmd):
	path = config["server_folder_path"] + f"tmp/tmp{ctx.message.id}.cfg"
	with open(path, "w") as f:
		f.write(cmd)
	os.system(
		f"tmux send-keys -t {config['tmux_name']} \"exec tmp/tmp{ctx.message.id}.cfg\" ENTER"
	)
	await ctx.send(f"O comando foi executado em {config['server_name']}.")

# COMANDO !RESTART

@bot.command(checks=[is_admin])
async def restart(ctx):
	os.system(f"pkill {config['server_executable_name']} && tmux kill-session -t {config['tmux_name']} && bash {config['server_script_path']}")
	await ctx.send(f"{config['server_name']} foi reiniciado.")

# PONTE SRB2KART -> DISCORD
# Feito com a ajuda de Goulart, Matt e Uotlaf

dataAnterior = 0

class logChangesDetect(FileSystemEventHandler):
	def on_modified(self, event):
		global dataAnterior

		dataAtual = round(time.time())
		if dataAtual - dataAnterior > 1:
			dataAnterior = dataAtual
			if event.is_directory:
				return
			elif event.event_type == 'modified':
				asyncio.run_coroutine_threadsafe(chatBridge(), bot.loop)
		else:
			time.sleep(1)
			self.on_modified(event)

dadosJogadores = {}
lastLogLine = 0

async def chatBridge():
	global dadosJogadores
    global faseAtual
    global jogadoresOnline
	global lastLogLine
	
	if lastLogLine !=0:
		with open(f"{config['server_folder_path']}{config['log_file']}", 'r') as file:
			for _ in range(lastLogLine - 1):
				next(file)
			for line in file:
				line = line.strip()
				# Detectar mensagem do jogador, exceto ~SERVER
				if re.search(r'<(?!~SERVER)(.*?)>\s(.*)', line):
					match = re.search(r'<(?!~SERVER)(.*?)>\s(.*)', line)
					playerName = match.group(1)
					playerMessage = match.group(2)
					async with aiohttp.ClientSession() as session:
						if playerName in dadosJogadores:
							await Webhook.from_url(f"{config['webhook_url']}", session=session).send(
								content=playerMessage,
								username=playerName,
								avatar_url=f"{config['webhook_base_avatar_url']}{dadosJogadores[playerName]['characterSkin']}_{dadosJogadores[playerName]['characterColor']}.png"
							)
						else:
							await Webhook.from_url(f"{config['webhook_url']}", session=session).send(
								content=playerMessage,
								username=playerName,
								avatar_url=f"{config['webhook_base_avatar_url']}default.png"
							)
				# Detectar mensagem "Fulano has finished the race."
				elif re.search(r'(.*)\s+has\s+finished\s+the\s+race.', line):
					match = re.search(r'(.*)\s+has\s+finished\s+the\s+race.', line)
					playerName = match.group(1)
					await bot.get_channel(config["chat_bridge_channel_id"]).send(
						f"***{playerName}** terminou a corrida*"
					)
				# Detectar mensagem "The round has ended."
				elif line == "The round has ended.":
					await bot.get_channel(config["chat_bridge_channel_id"]).send(
						"*A partida terminou*"
					)
				# Detectar mensagem 'Map is now "RR_EXAMPLE: Example Zone"'
				elif re.search(r'Map is now "(.*): ([^"]+)"', line):
					match = re.search(r'Map is now "(.*): ([^"]+)"', line)
					trackID = match.group(1)
					trackName = match.group(2)
                    faseAtual = f"{trackName};{trackID}"
					embed = discord.Embed(title="Acelerando para a próxima partida!", description=f"Fase: **{trackName}**\nID: **{trackID}**", colour=0x000099E1)
					embed.set_image(url=f"https://srb2kbr.com/static/images/{trackID}-kart.png")
					await bot.get_channel(config["chat_bridge_channel_id"]).send(
						embed=embed
					)
				# Detectar mensagem "Fulano entered the game"
				elif re.search(r'\*(.*)\s+entered\s+the\s+game', line):
					match = re.search(r'\*(.*)\s+entered\s+the\s+game', line)
					playerName = match.group(1)
					await bot.get_channel(config["chat_bridge_channel_id"]).send(
						f"***{playerName}** se juntou ao jogo*"
					)
                    jogadoresOnline[playerName] = {
                        'isSpectator': False,
                    }
				# Detectar mensagem "Player left the game"
				elif re.search(r'\*(.*)\s+left', line):
					match = re.search(r'\*(.*)\s+left', line)
					playerName = match.group(1)
					await bot.get_channel(config["chat_bridge_channel_id"]).send(
						f"***{playerName}** saiu do servidor*"
					)
					if playerName in dadosJogadores:
						del dadosJogadores[playerName]
                    del jogadoresOnline[playerName]
				# Detectar mensagem "Player joined the game"
				elif re.search(r'\*(.*)\s+has\s+joined', line):
					match = re.search(r'\*(.*)\s+has\s+joined', line)
					playerName = match.group(1)
					await bot.get_channel(config["chat_bridge_channel_id"]).send(
						f"***{playerName}** entrou no servidor*"
					)
                    jogadoresOnline.append(
                        Nome: playerName,
                        Espectador: True
                    )
				# Detectar mensagem "Fulano renamed to Beltrano"
				elif re.search(r'\*(.*)\s+renamed\s+to\s+(.*)', line):
					match = re.search(r'\*(.*)\s+renamed\s+to\s+(.*)', line)
					oldPlayerName = match.group(1)
					newPlayerName = match.group(2)
					await bot.get_channel(config["chat_bridge_channel_id"]).send(
						f"***{oldPlayerName}** mudou seu próprio nome para **{newPlayerName}***"
					)
					if oldPlayerName in dadosJogadores:
						dadosJogadores[newPlayerName] = dadosJogadores.pop(oldPlayerName)
                    jogadoresOnline[newPlayerName] = jogadoresOnline.pop(oldPlayerName)
				# Detectar mudança de personagem e/ou cor
				elif re.search(r'\[CHAR\] \[CHAR_COLOR\] (.*) \[CHAR_SKIN\] (.*) \[NUMBER\] \d+ \[NAME\] (.*)', line):
					match = re.search(r'\[CHAR\] \[CHAR_COLOR\] (.*) \[CHAR_SKIN\] (.*) \[NUMBER\] \d+ \[NAME\] (.*)', line)
					charColor = match.group(1)
					charSkin = match.group(2)
					playerName = match.group(3)
					dadosJogadores[playerName] = {
						'characterColor': charColor,
						'characterSkin': charSkin
					}
				# Detectar mensagem "Fulano became a spectator"
				elif re.search(r'\*(.*)\s+became\s+a\s+spectator', line):
					match = re.search(r'\*(.*)\s+became\s+a\s+spectator', line)
					playerName = match.group(1)
					await bot.get_channel(config["chat_bridge_channel_id"]).send(
						f"***{playerName}** se tornou um espectador*"
					)
                    jogadoresOnline[playerName] = {
                        'isSpectator': True,
                    }
				lastLogLine += 1
	else:
		with open(f"{config['server_folder_path']}{config['log_file']}", 'rb') as f:
			lastLogLine = sum(1 for _ in f)
			await asyncio.sleep(1)
			await chatBridge()

# PONTE DISCORD -> SRB2KART
# Trecho original por Deagahelio

@bot.event
async def on_message(message):
	if not message.content.startswith(config["prefix"]):
		if message.channel.id == config["chat_bridge_channel_id"]:
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
				path = config["server_folder_path"] + f"tmp/tmp{message.id}.cfg"
				with open(path, "w") as f:
					f.write(f"say [D] {message.author.name}: {text}")
				os.system(
					f"tmux send-keys -t {config['tmux_name']} \"exec tmp/tmp{message.id}.cfg\" ENTER"
				)
	# Se o canal de comandos for de fato um canal, e não um tópico, usar: message.channel.id == config["bot_commands_channel_id"]
	elif (isinstance(message.channel, discord.Thread) and message.channel.id == config["bot_commands_channel_id"]) or (any(role.name in config["allowed_roles"] for role in message.author.roles)):
		await bot.process_commands(message)

# APAGAR ARQUIVOS TEMPORÁRIOS
# Trecho original por Deagahelio

async def delete_tmp():
	while True:
		files = [
			config["server_folder_path"] + "tmp/" + f
			for f in os.listdir(config["server_folder_path"] + "tmp")
		]
		files.sort(key=os.path.getctime)
		for f in files[:-3]:
			os.system("rm " + f)
		await asyncio.sleep(10)

# INICIALIZAÇÃO DO BOT NO DISCORD

@bot.event
async def on_ready():
	await bot.change_presence(activity=discord.Game(name="como um anel!"))
	if config["chat_bridge"]:
		bot.loop.create_task(delete_tmp())
		# INICIALIZAR FUNÇÃO DE CHAT BRIDGE
		event_handler = logChangesDetect()
		observer = Observer()
		observer.schedule(event_handler, f"{config['server_folder_path']}logs", recursive=False)
		observer.start()

# RODAR BOT

bot.run(config["token"])