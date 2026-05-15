import discord
from discord import app_commands
from discord.ext import tasks
import datetime
import json
import os

# 1. Configurações Iniciais e Base de Dados
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_DADOS = os.path.join(DIRETORIO_ATUAL, 'historico_tarefas.json')


MEU_ID_DISCORD

fuso_horario = datetime.timezone(datetime.timedelta(hours=-3))

CATEGORIAS = {
    "💻 Foco e Saúde": [
        "Estudar programação/cybersegurança",
        "Academia"
    ],
    "🕹️ Lazer e Habilidades": [
        "Praticar guitarra",
        "Ler manga",
        "Jogar persona 5 royal",
        "Aprender Japonês"
    ]
}

TAREFAS_PADRAO = []
for lista in CATEGORIAS.values():
    TAREFAS_PADRAO.extend(lista)

# 2. Funções de Base de Dados (JSON)
def obter_data_hoje():
    return datetime.datetime.now(fuso_horario).strftime("%Y-%m-%d")

def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def salvar_dados(dados):
    with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def inicializar_dia_se_necessario():
    dados = carregar_dados()
    hoje = obter_data_hoje()
    
    if hoje not in dados:
        dados[hoje] = {tarefa: False for tarefa in TAREFAS_PADRAO}
        salvar_dados(dados)
    
    for tarefa in TAREFAS_PADRAO:
        if tarefa not in dados[hoje]:
            dados[hoje][tarefa] = False
            salvar_dados(dados)
            
    return dados

# 3. Gerador da Interface (Visual com Categorias)
def criar_interface_tarefas():
    dados = inicializar_dia_se_necessario()
    hoje = obter_data_hoje()
    tarefas_de_hoje = dados[hoje]

    texto = f"**📋 As Suas Tarefas Diárias ({hoje}):**\n\n"
    todas_concluidas = True
    opcoes = []

    for categoria, lista_tarefas in CATEGORIAS.items():
        texto += f"{categoria}\n"
        
        for tarefa in lista_tarefas:
            concluida = tarefas_de_hoje.get(tarefa, False)
            icone = "✅" if concluida else "❌"
            texto += f"{icone} - {tarefa}\n"
            
            if not concluida:
                todas_concluidas = False
                label_seguro = tarefa[:95] + "..." if len(tarefa) > 95 else tarefa
                opcoes.append(discord.SelectOption(label=label_seguro, value=tarefa, description="Clique para concluir"))
        
        texto += "\n"

    view = discord.ui.View(timeout=None)
    
    if todas_concluidas:
        texto += "🎉 **Parabéns! Concluiu tudo hoje!**"
    else:
        view.add_item(MenuTarefas(opcoes[:25]))
        
    return texto, view

# 4. Classes de Interface do Discord
class MenuTarefas(discord.ui.Select):
    def __init__(self, opcoes):
        super().__init__(placeholder="Selecione a tarefa concluída...", min_values=1, max_values=1, options=opcoes)

    async def callback(self, interaction: discord.Interaction):
        escolha = self.values[0]
        
        dados = carregar_dados()
        hoje = obter_data_hoje()
        if hoje in dados and escolha in dados[hoje]:
            dados[hoje][escolha] = True
            salvar_dados(dados)
        
        novo_texto, nova_view = criar_interface_tarefas()
        await interaction.response.edit_message(content=novo_texto, view=nova_view)

class MenuDesmarcar(discord.ui.Select):
    def __init__(self, opcoes):
        super().__init__(placeholder="Selecione a tarefa para desmarcar...", min_values=1, max_values=1, options=opcoes)

    async def callback(self, interaction: discord.Interaction):
        escolha = self.values[0]
        
        dados = carregar_dados()
        hoje = obter_data_hoje()
        if hoje in dados and escolha in dados[hoje]:
            dados[hoje][escolha] = False 
            salvar_dados(dados)
        
        await interaction.response.edit_message(content=f"⏪ A tarefa **{escolha}** foi desmarcada com sucesso! Use `/tarefas` para ver a lista.", view=None)

# 5. O Bot Principal
class MeuBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.ja_enviou_lembrete = False # Evita que ele envie a mensagem mais de uma vez

    async def setup_hook(self):
        self.rotina_meia_noite.start()
        await self.tree.sync()
        print("Bot online, comandos sincronizados e base de dados pronta!")

    # Evento que dispara logo que o bot faz login (quando o PC liga)
    async def on_ready(self):
        if not self.ja_enviou_lembrete:
            try:
                eu = await self.fetch_user(MEU_ID_DISCORD)
                await eu.send("👋 O PC foi ligado! Lembre-se de concluir as suas tarefas de hoje. Utilize o comando `/tarefas`.")
                self.ja_enviou_lembrete = True
            except Exception as e:
                print(f"Não foi possível enviar o lembrete de arranque: {e}")

    horario_reset = datetime.time(hour=0, minute=0, tzinfo=fuso_horario)

    @tasks.loop(time=horario_reset)
    async def rotina_meia_noite(self):
        inicializar_dia_se_necessario()
        print("Meia-noite! Novo dia registado no histórico.")
        
        # Limpar as mensagens enviadas pelo bot nas Mensagens Diretas
        try:
            eu = await self.fetch_user(MEU_ID_DISCORD)
            canal_dm = await eu.create_dm()
            
            # Percorre as últimas 30 mensagens do chat
            async for mensagem in canal_dm.history(limit=30):
                if mensagem.author == self.user: # Se a mensagem foi enviada pelo bot
                    await mensagem.delete()
        except Exception as e:
            print(f"Erro ao limpar o chat à meia-noite: {e}")

cliente = MeuBot()

# COMANDOS 

@cliente.tree.command(name="tarefas", description="Mostra a sua lista de tarefas diárias.")
async def comando_tarefas(interaction: discord.Interaction):
    texto, view = criar_interface_tarefas()
    await interaction.response.send_message(texto, view=view)


@cliente.tree.command(name="relatorio", description="Mostra o resumo de constância do mês atual.")
async def comando_relatorio(interaction: discord.Interaction):
    dados = carregar_dados()
    mes_atual = datetime.datetime.now(fuso_horario).strftime("%Y-%m")
    
    total_tarefas = 0
    tarefas_concluidas = 0
    dias_registrados = 0
    
    for data, tarefas_do_dia in dados.items():
        if data.startswith(mes_atual):
            dias_registrados += 1
            for status in tarefas_do_dia.values():
                total_tarefas += 1
                if status:
                    tarefas_concluidas += 1
                    
    if total_tarefas == 0:
        await interaction.response.send_message("Nenhum dado registado para este mês ainda.")
        return
        
    porcentagem = (tarefas_concluidas / total_tarefas) * 100
    
    texto = f"📊 **Relatório de Constância ({mes_atual})**\n\n"
    texto += f"🗓️ **Dias registados:** {dias_registrados}\n"
    texto += f"✅ **Tarefas concluídas:** {tarefas_concluidas} de {total_tarefas} ({porcentagem:.1f}%)\n"
    
    if porcentagem >= 80:
        texto += "\n🔥 **Excelente constância!** Está a dominar a rotina."
    elif porcentagem >= 50:
        texto += "\n👍 **Bom trabalho!** Mas ainda dá para melhorar."
    else:
        texto += "\n💪 **Atenção!** Vamos focar mais na disciplina este mês!"
        
    await interaction.response.send_message(texto)


@cliente.tree.command(name="desmarcar", description="Desmarca uma tarefa que foi concluída por engano.")
async def comando_desmarcar(interaction: discord.Interaction):
    dados = carregar_dados()
    hoje = obter_data_hoje()
    
    if hoje not in dados:
        await interaction.response.send_message("Nenhum dado para hoje.", ephemeral=True)
        return
        
    tarefas_concluidas = [tarefa for tarefa, status in dados[hoje].items() if status == True]
    
    if not tarefas_concluidas:
        await interaction.response.send_message("Não há nenhuma tarefa concluída para desmarcar neste momento.", ephemeral=True)
        return
        
    opcoes = []
    for tarefa in tarefas_concluidas:
        label_seguro = tarefa[:95] + "..." if len(tarefa) > 95 else tarefa
        opcoes.append(discord.SelectOption(label=label_seguro, value=tarefa))
        
    view = discord.ui.View(timeout=None)
    view.add_item(MenuDesmarcar(opcoes[:25]))
    
    await interaction.response.send_message("**⏪ Qual tarefa deseja desmarcar?**", view=view, ephemeral=True)

# Substitua pela sua chave (Mantenha as aspas)
TOKEN = ""
cliente.run(TOKEN)