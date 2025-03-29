"""
Cog pour les commandes d'administration du bot Mario Kart 8 Time Attack.
"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List

from database.manager import DatabaseManager
from utils.embeds import EmbedBuilder
from utils.logger import log_command, log_error
from database.models import parse_time, format_time

class AdminCog(commands.Cog):
    """
    Commandes d'administration pour le bot Mario Kart 8 Time Attack.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def is_admin(self, interaction: discord.Interaction) -> bool:
        """
        Vérifie si l'utilisateur a les permissions d'administration.
        
        Args:
            interaction: Interaction Discord
            
        Returns:
            True si l'utilisateur est administrateur, False sinon
        """
        # Vérifier si l'utilisateur est administrateur du serveur
        if interaction.user.guild_permissions.administrator:
            return True
        
        # Vérifier si l'utilisateur a le rôle d'administration configuré
        admin_role_id = await DatabaseManager.get_admin_role(interaction.guild_id)
        if admin_role_id:
            role = interaction.guild.get_role(admin_role_id)
            if role and role in interaction.user.roles:
                return True
        
        return False
    
    @app_commands.command(
        name="config",
        description="Configure les paramètres du bot"
    )
    @app_commands.describe(
        prefix="Préfixe de commande (ex: !mk)",
        role_admin="Rôle pouvant administrer le bot"
    )
    async def configure_bot(
        self,
        interaction: discord.Interaction,
        prefix: Optional[str] = None,
        role_admin: Optional[discord.Role] = None
    ):
        """
        Configure les paramètres du bot pour le serveur.
        
        Args:
            interaction: Interaction Discord
            prefix: Nouveau préfixe de commande (optionnel)
            role_admin: Rôle d'administration (optionnel)
        """
        # Journaliser la commande
        log_command(interaction.guild_id, interaction.user.id, "config")
        
        # Vérifier les permissions d'administration
        if not await self.is_admin(interaction):
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Permission refusée",
                    "Vous devez être administrateur pour configurer le bot."
                ),
                ephemeral=True
            )
            return
        
        # Enregistrer le serveur s'il n'existe pas déjà
        await DatabaseManager.register_server(interaction.guild_id, interaction.guild.name)
        
        changes = []
        
        # Mettre à jour le préfixe si fourni
        if prefix:
            if len(prefix) > 10:
                await interaction.response.send_message(
                    embed=EmbedBuilder.error_message(
                        "Préfixe trop long",
                        "Le préfixe doit comporter moins de 10 caractères."
                    ),
                    ephemeral=True
                )
                return
            
            await DatabaseManager.update_server_prefix(interaction.guild_id, prefix)
            changes.append(f"Préfixe défini sur `{prefix}`")
        
        # Mettre à jour le rôle d'administration si fourni
        if role_admin:
            await DatabaseManager.update_admin_role(interaction.guild_id, role_admin.id)
            changes.append(f"Rôle d'administration défini sur {role_admin.mention}")
        
        # Répondre avec les changements effectués
        if changes:
            await interaction.response.send_message(
                embed=EmbedBuilder.confirmation_message(
                    "Configuration mise à jour",
                    "\n".join(changes)
                )
            )
        else:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Aucun changement",
                    "Veuillez spécifier au moins un paramètre à modifier."
                ),
                ephemeral=True
            )
    
    @app_commands.command(
        name="verifier",
        description="Vérifie ou invalide un score soumis"
    )
    @app_commands.describe(
        utilisateur="Utilisateur dont le score doit être vérifié",
        action="Action à effectuer",
        score_index="Index du score à vérifier (1 = meilleur temps, 2 = 2ème meilleur, etc.)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Vérifier le score", value="verify"),
        app_commands.Choice(name="Supprimer le score", value="delete")
    ])
    async def verify_score(
        self,
        interaction: discord.Interaction,
        utilisateur: discord.User,
        action: str,
        score_index: Optional[int] = 1
    ):
        """
        Vérifie ou invalide un score soumis.
        
        Args:
            interaction: Interaction Discord
            utilisateur: Utilisateur dont le score doit être vérifié
            action: Action à effectuer (vérifier ou supprimer)
            score_index: Index du score à vérifier (1 = meilleur temps, 2 = 2ème meilleur, etc.)
        """
        # Journaliser la commande
        log_command(interaction.guild_id, interaction.user.id, "verifier")
        
        # Vérifier les permissions d'administration
        if not await self.is_admin(interaction):
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Permission refusée",
                    "Vous devez être administrateur pour vérifier les scores."
                ),
                ephemeral=True
            )
            return
        
        # Vérifier s'il y a un tournoi actif
        tournament = await DatabaseManager.get_active_tournament(interaction.guild_id)
        if not tournament:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Aucun tournoi actif",
                    "Il n'y a pas de tournoi en cours sur ce serveur."
                ),
                ephemeral=True
            )
            return
        
        # Récupérer l'ID utilisateur
        user_id = await DatabaseManager.register_user(str(utilisateur.id), utilisateur.display_name)
        
        # Vérifier si l'utilisateur participe au tournoi
        participation_id = await DatabaseManager.get_participation_id(tournament['id'], user_id)
        
        if not participation_id:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Pas de participation",
                    f"{utilisateur.mention} ne participe pas au tournoi en cours."
                ),
                ephemeral=True
            )
            return
        
        # Récupérer tous les scores de l'utilisateur
        scores = await DatabaseManager.get_user_scores(participation_id)
        
        if not scores:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Aucun score",
                    f"{utilisateur.mention} n'a pas encore soumis de temps pour ce tournoi."
                ),
                ephemeral=True
            )
            return
        
        # Trier par temps (du meilleur au pire)
        scores.sort(key=lambda x: x['time_ms'])
        
        # Vérifier si l'index du score est valide
        if score_index < 1 or score_index > len(scores):
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Index de score invalide",
                    f"{utilisateur.mention} n'a que {len(scores)} score(s). Veuillez choisir un index entre 1 et {len(scores)}."
                ),
                ephemeral=True
            )
            return
        
        # Obtenir le score selon l'index (en soustrayant 1 car les listes commencent à 0)
        selected_score = scores[score_index - 1]
        
        # Créer les informations utilisateur pour l'embed
        user_data = {
            "username": utilisateur.display_name,
            "discord_id": str(utilisateur.id)
        }
        
        # Créer l'embed avec les détails du score et une indication de l'index
        embed = discord.Embed(
            title=f"Vérification de score: {user_data['username']} (Score #{score_index}/{len(scores)})",
            description=f"Score soumis pour **{tournament['course_name']}** ({tournament['vehicle_class']})",
            color=0x3498DB  # Bleu
        )
        
        embed.add_field(
            name="Temps",
            value=f"**{format_time(selected_score['time_ms'])}**",
            inline=True
        )
        
        embed.add_field(
            name="Soumis le",
            value=selected_score['submitted_at'].strftime("%d/%m/%Y à %H:%M"),
            inline=True
        )
        
        embed.add_field(
            name="Status",
            value="✅ Vérifié" if selected_score['verified'] else "⏳ En attente de vérification",
            inline=True
        )
        
        # Ajouter un champ montrant tous les temps soumis
        status_icons = {
            1: "⏳",  # pending
            2: "✅",  # verified
            3: "📁",  # archived
            4: "❌"   # rejected
        }

        scores_list = ""
        for i, score in enumerate(scores):
            status_icon = status_icons.get(score['status_id'], "⏳")
            current_marker = "➡️ " if i == (score_index - 1) else ""
            scores_list += f"{current_marker}#{i+1}: **{format_time(score['time_ms'])}** {status_icon}\n"
        
        embed.add_field(
            name="Tous les temps soumis",
            value=scores_list,
            inline=False
        )
        
        if selected_score['screenshot_url']:
            embed.add_field(
                name="Capture d'écran",
                value="Voir ci-dessous",
                inline=False
            )
            embed.set_image(url=selected_score['screenshot_url'])
        else:
            embed.add_field(
                name="Capture d'écran",
                value="Aucune capture d'écran fournie",
                inline=False
            )
        
        embed.set_thumbnail(url=tournament['course_image'])
        embed.set_footer(text=f"ID du score: {selected_score['id']}")
        
        if action == "verify":
            # Vérifier le score sélectionné
            await DatabaseManager.verify_score(selected_score['id'])
            
            # Archiver automatiquement uniquement les scores MOINS BONS que celui validé
            other_scores_archived   = False
            archived_count          = 0
            
            for other_score in scores:
                # Ne pas toucher au score qu'on vient de vérifier
                if other_score['id'] == selected_score['id']:
                    continue
                # Ne pas modifier les scores déjà supprimés (status_id = 4)
                if other_score['status_id'] == 4:
                    continue
                    
                # Archiver seulement si le temps est moins bon (plus grand) que le temps validé
                if other_score['time_ms'] > selected_score['time_ms']:
                    await DatabaseManager.update_score_status(other_score['id'], 3)  # status_id=3 pour "archived"
                    archived_count += 1
                    other_scores_archived = True

            # Mettre à jour l'embed pour refléter le nouveau statut
            embed.remove_field(2)  # Supprime le champ "Status"
            embed.insert_field_at(
                2,
                name="Status",
                value="✅ Vérifié",  # Maintenant vérifié
                inline=True
            )
            
            # Créer le message de confirmation
            confirm_message = f"Le score #{score_index} de {utilisateur.mention} ({format_time(selected_score['time_ms'])}) a été marqué comme vérifié."
            if other_scores_archived:
                confirm_message += f"\n{archived_count} score(s) moins bon(s) ont été automatiquement archivés."
            
            # Mettre à jour la liste des scores
            scores_list = ""
            for i, score in enumerate(scores):
                # Si le score est déjà supprimé, conserver l'icône supprimé
                if score['status_id'] == 4:  # status_id=4 pour "supprimé"
                    status_icon = "❌"  # Supprimé
                # Pour le score qu'on vient de vérifier
                elif i == (score_index - 1):
                    status_icon = "✅"
                # Pour les scores qui viennent d'être archivés (moins bons que celui vérifié)
                elif score['time_ms'] > selected_score['time_ms']:
                    status_icon = "📁"  # Archivé
                # Pour les autres scores (inchangés)
                else:
                    status_icon = status_icons.get(score['status_id'], "⏳")
                
                current_marker = "➡️ " if i == (score_index - 1) else ""
                scores_list += f"{current_marker}#{i+1}: **{format_time(score['time_ms'])}** {status_icon}\n"
            
            # Mettre à jour le champ avec la liste des scores
            embed.remove_field(3)  # Supprime le champ "Tous les temps soumis"
            embed.insert_field_at(
                3,
                name="Tous les temps soumis",
                value=scores_list,
                inline=False
            )
            
            # Envoyer l'embed mis à jour avec le message de confirmation
            await interaction.response.send_message(
                content=confirm_message,
                embed=embed,
                ephemeral=True
            )
            
            # Vérifier si un thread de tournoi existe et y envoyer une notification
            if tournament['thread_id']:
                try:
                    thread = interaction.guild.get_thread(int(tournament['thread_id']))
                    if thread:
                        # Créer un embed pour l'annonce dans le thread
                        thread_embed = discord.Embed(
                            title="✅ Score vérifié",
                            description=f"Le score de {utilisateur.mention} a été vérifié par {interaction.user.mention}.",
                            color=0x2ECC71  # Vert
                        )
                        
                        thread_embed.add_field(
                            name="Temps vérifié",
                            value=f"**{format_time(selected_score['time_ms'])}**",
                            inline=True
                        )
                        
                        if other_scores_archived:
                            thread_embed.add_field(
                                name="Note",
                                value=f"Les autres temps soumis ont été archivés automatiquement.",
                                inline=True
                            )
                        
                        thread_embed.set_thumbnail(url=tournament['course_image'])
                        
                        await thread.send(embed=thread_embed)
                except Exception as e:
                    log_error(f"Erreur lors de l'envoi de la notification de vérification dans le thread: {str(e)}")
            
        elif action == "delete":
            # Similaire pour l'action "delete"
            # Supprimer le score
            await DatabaseManager.update_score_status(selected_score['id'], 4) # status_id=4 pour "rejected"   
            
            # Mettre à jour l'embed pour indiquer que le score a été supprimé
            embed.remove_field(2)  # Supprime le champ "Status"
            embed.insert_field_at(
                2,
                name="Status",
                value="❌ Supprimé",  # Indique que le score est supprimé
                inline=True
            )
            
            # Mettre à jour également la liste des scores
            scores_list = ""
            for i, score in enumerate(scores):
                # Pour le score supprimé, on met une croix rouge
                if i == (score_index - 1):
                    status_icon = "❌"
                    current_marker = "➡️ "
                else:
                    status_icon = status_icons.get(score['status_id'], "⏳")
                    current_marker = "➡️ " if i == (score_index - 1) else ""
                scores_list += f"{current_marker}#{i+1}: **{format_time(score['time_ms'])}** {status_icon}\n"
            
            # Mettre à jour le champ avec la liste des scores
            embed.remove_field(3)  # Supprime le champ "Tous les temps soumis"
            embed.insert_field_at(
                3,
                name="Tous les temps soumis",
                value=scores_list,
                inline=False
            )
            
            # Envoyer l'embed mis à jour avec un message de confirmation
            await interaction.response.send_message(
                content=f"Le score #{score_index} de {utilisateur.mention} ({format_time(selected_score['time_ms'])}) a été supprimé.",
                embed=embed,
                ephemeral=True
            )
            
            # Vérifier si un thread de tournoi existe et y envoyer une notification
            if tournament['thread_id']:
                try:
                    thread = interaction.guild.get_thread(int(tournament['thread_id']))
                    if thread:
                        # Créer un embed pour l'annonce dans le thread
                        thread_embed = discord.Embed(
                            title="❌ Score supprimé",
                            description=f"Un score de {utilisateur.mention} a été supprimé par {interaction.user.mention}.",
                            color=0xE74C3C  # Rouge
                        )
                        
                        thread_embed.add_field(
                            name="Temps supprimé",
                            value=f"**{format_time(selected_score['time_ms'])}**",
                            inline=True
                        )
                        
                        thread_embed.set_thumbnail(url=tournament['course_image'])
                        
                        await thread.send(embed=thread_embed)
                except Exception as e:
                    log_error(f"Erreur lors de l'envoi de la notification de suppression dans le thread: {str(e)}")

        # Mettre à jour le classement
        tournament_cog = self.bot.get_cog('TournamentCog')
        if tournament_cog:
            await tournament_cog.update_leaderboard(interaction.guild_id, tournament['id'])    
    @app_commands.command(
        name="scores",
        description="Affiche tous les scores d'un utilisateur pour le tournoi en cours"
    )
    @app_commands.describe(
        utilisateur="Utilisateur dont vous voulez voir les scores"
    )
    async def view_user_scores(self, interaction: discord.Interaction, utilisateur: discord.User):
        """
        Affiche tous les scores soumis par un utilisateur pour le tournoi en cours.
        
        Args:
            interaction: Interaction Discord
            utilisateur: Utilisateur dont on veut voir les scores
        """
        # Journaliser la commande
        log_command(interaction.guild_id, interaction.user.id, "scores")
        
        # Vérifier les permissions d'administration
        if not await self.is_admin(interaction):
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Permission refusée",
                    "Vous devez être administrateur pour voir les scores des autres utilisateurs."
                ),
                ephemeral=True
            )
            return
        
        # Vérifier s'il y a un tournoi actif
        tournament = await DatabaseManager.get_active_tournament(interaction.guild_id)
        if not tournament:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Aucun tournoi actif",
                    "Il n'y a pas de tournoi en cours sur ce serveur."
                ),
                ephemeral=True
            )
            return
        
        # Récupérer l'ID utilisateur
        user_id = await DatabaseManager.register_user(str(utilisateur.id), utilisateur.display_name)
        
        # Vérifier si l'utilisateur participe au tournoi
        participation_id = await DatabaseManager.get_participation_id(tournament['id'], user_id)
        
        if not participation_id:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Pas de participation",
                    f"{utilisateur.mention} ne participe pas au tournoi en cours."
                ),
                ephemeral=True
            )
            return
        
        # Récupérer tous les scores de l'utilisateur
        scores = await DatabaseManager.get_user_scores(participation_id)
        
        if not scores:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Aucun score",
                    f"{utilisateur.mention} n'a pas encore soumis de temps pour ce tournoi."
                ),
                ephemeral=True
            )
            return
        
        # Trier par temps (du meilleur au pire)
        scores.sort(key=lambda x: x['time_ms'])
        
        # Créer un embed pour afficher les scores
        embed = discord.Embed(
            title=f"Scores de {utilisateur.display_name} pour {tournament['course_name']}",
            description=f"**{len(scores)}** temps soumis pour le tournoi en cours.",
            color=0x3498DB  # Bleu
        )
        
        # Ajouter un champ montrant tous les temps soumis
        status_icons = {
            1: "⏳",  # pending
            2: "✅",  # verified
            3: "📁",  # archived
            4: "❌"   # rejected
        }

        scores_list = ""
        for i, score in enumerate(scores):
            status_icon = status_icons.get(score['status_id'], "⏳")
            
            # Ajouter le lien vers la preuve si elle existe
            proof_link  = f" • [voir preuve]({score['screenshot_url']})" if score['screenshot_url'] else " • *aucune preuve*"
            scores_list += f"#{i+1}: **{format_time(score['time_ms'])}** {status_icon} - {score['submitted_at'].strftime('%d/%m/%Y à %H:%M')}{proof_link}\n"
        
        embed.add_field(
            name="Tous les temps soumis",
            value=scores_list,
            inline=False
        )
        
        embed.set_thumbnail(url=tournament['course_image'])
        embed.set_footer(text=f"Pour vérifier un score spécifique, utilisez /verifier avec le paramètre score_index")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="historique",
        description="Affiche l'historique des tournois terminés"
    )
    async def tournament_history(self, interaction: discord.Interaction):
        """
        Affiche l'historique des tournois terminés sur le serveur.
        
        Args:
            interaction: Interaction Discord
        """
        # Journaliser la commande
        log_command(interaction.guild_id, interaction.user.id, "historique")
        
        # Récupérer l'historique des tournois (implémentation à faire)
        # Cette fonctionnalité nécessiterait une requête supplémentaire dans le DatabaseManager
        
        # Pour l'instant, renvoyer un message temporaire
        await interaction.response.send_message(
            embed=EmbedBuilder.confirmation_message(
                "Fonctionnalité à venir",
                "L'historique des tournois sera disponible dans une prochaine mise à jour."
            ),
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    """
    Ajoute le cog au bot.
    
    Args:
        bot: Instance du bot Discord
    """
    await bot.add_cog(AdminCog(bot))