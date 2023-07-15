import discord, logging, asyncio, os, io, datetime

from discord import abc
from discord.ext import commands
from typing import Coroutine, Any, Union
from objects import GPTChat, GPTHistory, GPTConfig

# Configuration

try:
    with open('dependencies/token', 'r') as tk_file:
        TOKEN: str = tk_file.read()
except FileNotFoundError:
    print("Missing token file."); exit(1)

INTENTS = discord.Intents.all()
full_user_chat_return_type = Union[dict[str, GPTChat.GPTChat], dict]

"""Changelog:
    Fixed streaming message size error
    Secured DeveloperJoe chat requirements (What channels it may speak in)
"""

# Main Bot Class

class DevJoe(commands.Bot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_uptime(self) -> datetime.timedelta:
        return (datetime.datetime.now(tz=GPTConfig.TIMEZONE) - self.start_time)
    
    def get_user_conversation(self, id_: int, chat_name: Union[str, None]=None, all: bool=False) -> Union[Union[GPTChat.GPTChat, int], full_user_chat_return_type]:
        if int(id_) in list(self.chats) and self.chats[id_]:
            if all == True:
                return self.chats[id_]
            if not chat_name:
                return self.chats[id_]["0"]
            elif chat_name:
                return self.chats[id_][chat_name]
        return 0
    
    def add_conversation(self, uid: int, name: str, conversation: GPTChat.GPTChat) -> None:
        self.chats[uid][name] = conversation
        
    def to_file(self, content: str, name: str) -> discord.File:
        f = io.BytesIO(content.encode())
        f.name = name
        return discord.File(f)
    
    async def get_confirmation(self, interaction: discord.Interaction, msg: str) -> discord.Message:
        def _check_if_user(message: discord.Message) -> bool:
            return message.author.id == interaction.user.id and message.channel == interaction.channel
        
        await interaction.response.send_message(msg) if not interaction.response.is_done() else await interaction.followup.send(msg)
        message: discord.Message = await self.wait_for('message', check=_check_if_user, timeout=GPTConfig.QUERY_TIMEOUT)
        return message
    
    async def send_debug_message(self, interaction: discord.Interaction, error: BaseException, cog: str) -> None:
        if GPTConfig.DEBUG == True:
            exception_text = f"From main class error handler \n\nError Class: {str(Exception)}\nError Arguments: {str(Exception.args)}\nFrom cog: {cog} "
            await interaction.followup.send(exception_text) if interaction.response.is_done() else await interaction.response.send_message(exception_text) 
            raise error
            
    async def on_ready(self):
        if self.application:
            print(f"{self.application.name} Online (V: {GPTConfig.VERSION})")

            self.chats: dict[int, full_user_chat_return_type] = {}
            self.start_time = datetime.datetime.now(tz=GPTConfig.TIMEZONE)
            
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="AND answering lifes biggest questions. (/help)"))

            _history = GPTHistory.GPTHistory()
            async def _check_integrity(i: int):
                if not i > 1:
                    if not _history.__check__():
                        print("Database file has been modified / deleted, rebuilding..")
                        _history.init_history()
                        return await _check_integrity(i+1)
                    return print("Database all set.")
                print("Database could not be rebuilt. Aborting. Check database files.")
                return await self.close()
            
            await _check_integrity(0)
            self.chats = {user.id: {} for user in self.users}

    async def setup_hook(self) -> Coroutine[Any, Any, None]:
        for file in os.listdir(f"extensions"):
            if file.endswith(".py"):
                await self.load_extension(f"extensions.{file[:-3]}")

        await self.tree.sync()
        return await super().setup_hook() # type: ignore
    
# Driver Code

async def run_bot():
    client = None
    try:
        logging_handler = logging.FileHandler("misc/bot_log.log", mode="w+")
        discord.utils.setup_logging(level=logging.ERROR, handler=logging_handler)
        
        async with DevJoe(command_prefix="?", intents=INTENTS) as client:
            await client.start(TOKEN)
    except KeyboardInterrupt:
        if client:
            await client.close()
            exit(0)
        
if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        pass