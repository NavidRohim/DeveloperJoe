import discord
from discord.ext import commands
from joe import DevJoe
from objects import GPTConfig, GPTModelRules, GPTExceptions

def in_correct_channel(interaction: discord.Interaction) -> bool:
    return bool(interaction.channel) == True and bool(interaction.channel.guild if interaction.channel else False)

# TODO: Add proper error handling for incorrect channel setting

class admin(commands.Cog):
    def __init__(self, client):
        self.client: DevJoe = client
        print(f"{self.__cog_name__} Loaded")

    @discord.app_commands.command(name="shutdown", description="Shuts down bot client")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def halt(self, interaction: discord.Interaction):
        await interaction.response.send_message("Shutting Down")
        await self.client.close()

        exit(0)

    @discord.app_commands.command(name="lock", description="Locks a select GPT Model behind a role or permission.")
    @discord.app_commands.checks.has_permissions(manage_channels=True)
    @discord.app_commands.choices(gpt_model=GPTConfig.MODEL_CHOICES)
    @discord.app_commands.describe(gpt_model="The GPT model you want to lock.", role="The role that will be added to the specified model's list of allowed roles.")
    @discord.app_commands.check(in_correct_channel)
    async def lock_role(self, interaction: discord.Interaction, gpt_model: str, role: discord.Role):

        with GPTModelRules.GPTModelRules(role.guild) as rules:
            rules.upload_guild_model(gpt_model, role)
            await interaction.response.send_message(f"Added {gpt_model} behind role {role.mention}.")

    @discord.app_commands.command(name="unlock", description="Unlocks a previously locked GPT Model.")
    @discord.app_commands.checks.has_permissions(manage_channels=True)
    @discord.app_commands.choices(gpt_model=GPTConfig.MODEL_CHOICES)
    @discord.app_commands.describe(gpt_model="The GPT model you want to unlock.", role="The role that will be removed from the specified model's list of allowed roles.")
    @discord.app_commands.check(in_correct_channel)
    async def unlock_role(self, interaction: discord.Interaction, gpt_model: str, role: discord.Role):
        try:
            with GPTModelRules.GPTModelRules(role.guild) as rules:
            
                new_rules = rules.remove_guild_model(gpt_model, role)
                print(new_rules)
                await interaction.response.send_message(f"Removed requirement role {role.mention} from {gpt_model}." if new_rules != None else f"{role.mention} has not been added to unlock database.")
        except Exception as mne: # GPTExceptions.ModelNotExist
            print(mne, type(mne))
            await interaction.response.send_message(mne.args[0])

    @discord.app_commands.command(name="locks", description="View all models and which roles may utilise them.")
    @discord.app_commands.checks.has_permissions(manage_channels=True)
    @discord.app_commands.check(in_correct_channel)
    async def view_locks(self, interaction: discord.Interaction):    
        with GPTModelRules.GPTModelRules(interaction.guild) as rules:
            text = ""
            models = rules.get_models_for_guild()
            no_roles = "No added roles. \n\n"

            for model in models.items():
                text += f"~ {model[0]} ~\n{no_roles if not model[1] else ''}"
                for r_id in model[1]:
                    text += f"\n{interaction.guild.get_role(int(r_id)).mention}\n"
            
            if not models:        
                text = no_roles

            await interaction.response.send_message(text)
        
        

async def setup(client):
    await client.add_cog(admin(client))
