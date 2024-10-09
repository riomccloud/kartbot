# CARREGA O ARQUIVO DE CONFIGURAÇÃO

with open(
	str(pathlib.Path(__file__).parent.absolute()) + "/kartbot_config.json", "r"
) as f:
	config = json.loads(f.read())