import json, discord
from typing import ( 
    Any as _Any
)

from . import (
    database, 
    exceptions,
    models
)
from .common import (
    commands_utils,
)

__all__ = [
    "DGGuildDatabaseModelHandler"
]
class DGGuildDatabaseModelHandler(database.DGDatabaseSession):
    # Old: DGRules
    """Database connection that manages model permissions (Model Lock List, or MLL, etc..) maybe more in the future."""

    def __enter__(self):
        
        self.in_database = self.has_guild()
        
        if self.in_database == False:
            self.in_database = bool(self.add_guild())
            
        return super().__enter__()

    def __exit__(self, type_, value_, traceback_):
        super().__exit__(type_, value_, traceback_)

    def __init__(self, guild: discord.Guild):
        """Class that manages model permissions (Model Lock List, or MLL, etc..) maybe more in the future."""
        
        self._guild: discord.Guild = guild
        self.in_database = False

        super().__init__()
    

    def _get_raw_models_database(self) -> list[tuple[str, ...]]:
        raw_models = self._exec_db_command("SELECT jsontables FROM model_rules WHERE gid=?", (self.guild.id,))
        if raw_models:
            return raw_models
        raise exceptions.GuildNotExist(self.guild)
    
    def _dump_into_database(self, __object: _Any) -> list[_Any]:
        json_string = json.dumps(__object)
        return self._exec_db_command("UPDATE model_rules SET jsontables=? WHERE gid=?", (json_string, self.guild.id))

    @property
    def in_database(self) -> bool:
        return self._in_database
    
    @in_database.setter
    def in_database(self, value: bool):
        self._in_database = value

    @property
    def guild(self):
        return self._guild
    
    def get_guild_model(self, model: models.GPTModelType) -> list[int]:
        models = self.get_guild_models()
        
        if models:
            if model in models: 
                return models[model]
            raise exceptions.ModelNotExist(self.guild, model.model)
        return []
    
    def get_guild_models(self) -> dict[models.GPTModelType, list[int]]:
        models = self._get_guild_models_raw()
        return {commands_utils.get_modeltype_from_name(model): data for model, data in models.items()}

    def _get_guild_models_raw(self) -> dict[str, list[int]]:
        _guild_pointer = self._get_raw_models_database()

        if _guild_pointer:
            guild_models = json.loads(_guild_pointer[0][0])
            return guild_models 
        return {}
    
    def has_guild(self) -> bool:
        return bool(self._exec_db_command("SELECT jsontables FROM model_rules WHERE gid=?", (self.guild.id,)))
    
    def upload_guild_model(self, model: models.GPTModelType, role: discord.Role) -> bool:
        guild_rules = self._get_guild_models_raw() 

        if model.model in list(guild_rules) and isinstance(guild_rules, dict) and role.id not in guild_rules[model.model]:
            guild_rules[model.model].append(role.id)
    
        elif isinstance(guild_rules, dict) and model not in list(guild_rules):
            guild_rules[model.model] = [role.id]

        else:
            return False
        
        self._dump_into_database(guild_rules)
        
        return True

    def remove_guild_model(self, model: models.GPTModelType, role: discord.Role):
        models_allowed_roles = self._get_guild_models_raw()

        if model.model in list(models_allowed_roles) and isinstance(models_allowed_roles, dict) and role.id in list(models_allowed_roles[model.model]):
            models_allowed_roles[model.model].remove(role.id)
        elif model not in list(models_allowed_roles):
            raise exceptions.ModelNotExist(self.guild, model.display_name)
        else:
            return None
        
        self._dump_into_database(models_allowed_roles)
        return role.id in self.get_guild_model(model)

    def add_guild(self) -> bool:
        if self.in_database == False:
            self._exec_db_command("INSERT INTO model_rules VALUES(?, ?)", (self.guild.id, json.dumps({})))
            return self.has_guild()
        raise exceptions.GuildExistsError(self.guild)
    
    def del_guild(self) -> bool:
        if self.in_database == True:
            self._exec_db_command("DELETE FROM model_rules WHERE gid=?", (self.guild.id,))
            return not self.has_guild()
        raise exceptions.GuildNotExist(self.guild)
    
    def user_has_model_permissions(self, user_role: discord.Role, model: models.GPTModelType) -> bool:
        try:
            model_roles = self.get_guild_model(model)
            def _does_have_senior_role():
                return [True for r_id in model_roles if user_role >= user_role.guild.get_role(int(r_id))]

            return (bool(model_roles) == False) \
            or (user_role.id in model_roles if isinstance(model_roles, list) else False) \
            or (not model_roles or bool(_does_have_senior_role())) # Check if the model has no restrictions. The user has a role contained within any possible restrictions, or if the user has a role that is higher that of any lower role.
        except exceptions.ModelNotExist:
            return True
    
    def get_models(self) -> tuple[models.GPTModelType, ...]:
        models = self.get_guild_models()
        return tuple(models.keys())
         