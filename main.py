import nextcord
from nextcord.ext import commands
from nextcord import Interaction

bot = commands.Bot(command_prefix="!")

@bot.event
async def on_ready():
    print(f"{bot.user.name} est connecté au Discord!")

@bot.slash_command(guild_ids=[1202362398728785940])  # Remplacez avec l'ID de votre serveur
async def hello(interaction: Interaction):
    await interaction.response.send_message("Bonjour!")


bot.run("token")
