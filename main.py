"""
Point d'entrée principal du bot Mario Kart 8 Time Attack.
"""
import os
import asyncio
import discord
import signal
import sys
from discord import app_commands
from discord.ext import commands

from config import TOKEN
from utils.logger import logger, log_error

# Configuration de l'intention (intents) du bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Création de l'instance du bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Liste des cogs à charger
COGS = [
    "cogs.tournament",
    "cogs.scores",
    "cogs.admin"
]

# Fonction pour gérer l'arrêt propre du bot
async def shutdown(signal_received=None):
    """Arrête proprement le bot Discord."""
    print('Arrêt du bot en cours...')
    try:
        # Fermer proprement la connexion à la base de données
        from database.manager import DatabaseManager
        await DatabaseManager.close_connection()
        
        # Fermer le bot Discord
        await bot.close()
    except Exception as e:
        print(f"Erreur lors de l'arrêt du bot: {e}")
    finally:
        print('Bot déconnecté.')

# Gestionnaire de signal pour Ctrl+C
def signal_handler(sig, frame):
    print(f'Signal {sig} reçu, arrêt en cours...')
    # Utiliser asyncio pour appeler la fonction d'arrêt
    if asyncio.get_event_loop().is_running():
        asyncio.create_task(shutdown())
    else:
        sys.exit(0)

# Enregistrement des gestionnaires de signaux
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # kill

@bot.event
async def on_ready():
    """Événement déclenché lorsque le bot est prêt."""
    logger.info(f"Bot connecté en tant que {bot.user.name}")
    
    # Synchroniser les commandes slash
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synchronisé {len(synced)} commandes")
    except Exception as e:
        log_error(f"Erreur lors de la synchronisation des commandes: {str(e)}")
    
    # Mettre à jour la présence du bot
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="Mario Kart 8 Deluxe"
        )
    )
    
    logger.info("Bot prêt !")

@bot.event
async def on_guild_join(guild):
    """
    Événement déclenché lorsque le bot rejoint un nouveau serveur.
    
    Args:
        guild: Serveur Discord rejoint
    """
    logger.info(f"Bot ajouté au serveur: {guild.name} (ID: {guild.id})")
    
    # Envoyer un message de bienvenue dans le premier canal disponible
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="Merci de m'avoir ajouté !",
                description="Je suis un bot de tournoi Time Attack pour Mario Kart 8 Deluxe.",
                color=0x3498DB  # Bleu
            )
            
            embed.add_field(
                name="Commandes principales",
                value=(
                    "`/tournoi` - Crée un nouveau tournoi\n"
                    "`/participer` - Inscrit au tournoi en cours\n"
                    "`/score` - Soumet un temps\n"
                    "`/info` - Affiche les informations du tournoi\n"
                    "`/config` - Configure le bot (admin uniquement)"
                ),
                inline=False
            )
            
            embed.set_footer(text="Pour plus d'informations, utilisez la commande /aide")
            
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                continue
            break

@bot.event
async def on_command_error(ctx, error):
    """
    Événement déclenché lorsqu'une erreur se produit lors de l'exécution d'une commande.
    
    Args:
        ctx: Contexte de la commande
        error: Erreur survenue
    """
    if isinstance(error, commands.CommandNotFound):
        return
    
    log_error(f"Erreur de commande: {str(error)}")

@bot.tree.error
async def on_app_command_error(interaction, error):
    """
    Événement déclenché lorsqu'une erreur se produit lors de l'exécution d'une commande slash.
    
    Args:
        interaction: Interaction Discord
        error: Erreur survenue
    """
    if isinstance(error, app_commands.CommandNotFound):
        return
    
    log_error(f"Erreur de commande slash: {str(error)}")
    
    # Informer l'utilisateur de l'erreur
    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Une erreur s'est produite",
                    description=f"```{str(error)}```",
                    color=0xE74C3C  # Rouge
                ),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Une erreur s'est produite",
                    description=f"```{str(error)}```",
                    color=0xE74C3C  # Rouge
                ),
                ephemeral=True
            )
    except discord.HTTPException:
        pass

@bot.tree.command(name="aide", description="Affiche l'aide du bot")
async def help_command(interaction: discord.Interaction):
    """
    Affiche l'aide du bot.
    
    Args:
        interaction: Interaction Discord
    """
    embed = discord.Embed(
        title="Aide - Bot Mario Kart 8 Time Attack",
        description="Voici les commandes disponibles :",
        color=0x3498DB  # Bleu
    )
    
    embed.add_field(
        name="Commandes de tournoi",
        value=(
            "`/tournoi [classe] [duree] [course]` - Crée un nouveau tournoi\n"
            "`/tournois` - Liste les tournois actifs\n"
            "`/participer` - Inscrit au tournoi en cours\n"
            "`/info` - Affiche les informations du tournoi\n"
            "`/statut [mentionner]` - Affiche le statut actuel du tournoi  (admin uniquement)\n"
            "`/annuler` - Annule le tournoi en cours (admin uniquement)"
        ),
        inline=False
    )
    
    embed.add_field(
        name="Commandes de score",
        value=(
            "`/score <temps> [preuve]` - Soumet un temps\n"
            "`/messcores` - Affiche vos temps soumis\n"
            "`/verifier <utilisateur> <action> [score_index]` - Vérifie ou supprime un score (admin uniquement)"
        ),
        inline=False
    )
    
    embed.add_field(
        name="Commandes d'administration",
        value=(
            "`/config [prefix] [role_admin]` - Configure le bot\n"
            "`/historique` - Affiche l'historique des tournois"
        ),
        inline=False
    )
    
    embed.add_field(
        name="Threads de tournoi",
        value=(
            "Chaque tournoi crée automatiquement un thread dédié pour centraliser les interactions. "
            "Rejoignez ce thread pour suivre le tournoi, voir les classements et interagir avec les autres participants."
        ),
        inline=False
    )
    
    embed.set_footer(text="Bot développé par MaCheLaPizza")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def load_extensions():
    """Charge tous les cogs du bot."""
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            logger.info(f"Cog chargé: {cog}")
        except Exception as e:
            log_error(f"Erreur lors du chargement du cog {cog}: {str(e)}")

# Fonction principale pour exécuter le bot
async def main():
    try: 
        print("Chargement des cogs...")
        # Charger les extensions
        await load_extensions()
        print("Démarrage du bot...")
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("Interruption clavier détectée")
    except Exception as e:
        print(f"Erreur: {e}")
    finally:
        if not bot.is_closed():
            await shutdown()

# Lancer le bot
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Programme terminé par l'utilisateur")