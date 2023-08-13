"""Handles conversations between the end-user and the GPT Engine."""

import datetime as _datetime, discord as _discord, openai as _openai, random as _random, openai_async as _openai_async, json as _json, asyncio as _asyncio

from discord.ext import commands as _commands
from enum import Enum as _Enum
from typing import (
    Union as _Union, 
    Any as _Any, 
    AsyncGenerator as _AsyncGenerator
)
from . import (
    exceptions, 
    guildconfig, 
    config, 
    history, 
    models, 
    utils, 
    ttsmodels
)

class DGTextChat:
    """Represents a text-only DG Chat."""
    def __init__(self, 
                bot_instance: _commands.Bot,
                _openai_token: str, 
                user: _Union[_discord.User, _discord.Member], 
                name: str,
                stream: bool,
                display_name: str, 
                model: models.GPTModelType=config.DEFAULT_GPT_MODEL, 
                associated_thread: _Union[_discord.Thread, None]=None,
                is_private: bool=True 
        ):
        """Represents a text DG Chat.

        Args:
            _openai_token (str): Your OpenAI API Token
            user (_Union[_discord.User, _discord.Member]): The member this text chat will belong too.
            name (str): Name of the chat.
            stream (bool): Weather the chat will be streamed. (Like ChatGPT)
            display_name (str): What the display name of the chat will be.
            model (GPTModelType, optional): Which GPT Model to use. Defaults to DEFAULT_GPT_MODEL.
            associated_thread (_Union[_discord.Thread, None], optional): What the dedicated discord thread is. Defaults to None.
        """
        self.bot = bot_instance
        self.user: _Union[_discord.User, _discord.Member] = user
        self.time: _datetime.datetime = _datetime.datetime.now()
        self.hid = hex(int(_datetime.datetime.timestamp(_datetime.datetime.now()) + user.id) * _random.randint(150, 1500))
        self.chat_thread = associated_thread

        self.oapi = _openai_token

        self.name = name
        self.display_name = display_name
        self.stream = stream

        self.model = model
        self.tokens = 0

        self._private, self._is_active, self.is_processing = is_private, True, False
        self.chat_history, self.readable_history = [], []
        

        _openai.api_key = self.oapi
    
    @property
    def type(self):
        return DGChatTypesEnum.TEXT
    
    @property
    def is_active(self) -> bool:
        return self._is_active
    
    @is_active.setter
    def is_active(self, value: bool):
        self._is_active = value
    
    @property
    def private(self) -> bool:
        return self._private

    @private.setter
    def private(self, is_p: bool):
        self._private = is_p
        
    def __manage_history__(self, is_gpt_reply: _Any, query_type: str, save_message: bool, tokens: int):
        self.is_processing = False

        if not save_message and query_type == "query":
            self.chat_history = self.chat_history[:len(self.chat_history)-2]
        self.readable_history.pop()

        if is_gpt_reply and save_message and query_type == "query":
            self.tokens += tokens
    
    @utils.check_enabled
    async def __get_stream_parsed_data__(self, messages: list[dict], **kwargs) -> _AsyncGenerator:
        payload = {"model": self.model.model, "messages": messages, "stream": True} | kwargs
        reply = await _openai_async.chat_complete(api_key=self.oapi, timeout=config.GPT_REQUEST_TIMEOUT, payload=payload)

        # Setup the list of responses
        responses: list[str] = [""]
        last_char = 0

        # For every character byte in byte stream
        for char in reply.read():
            # Check if current character and last char are line feed characters (Represents new chunk)
            if char == 10 and last_char == 10:
                
                # Check if chunk is the right format, or doesn't equal anything
                if responses[-1].strip("\n") in ["data: [DONE]", ""]:
                    responses.pop()
                else:
                    responses[-1] = _json.loads(responses[-1][6:]) # Filter out the "data: " part, and translate to a dictionary

                    yield responses[-1] # Yield finished chunk
                    responses.append("") # Append start of a new chunk
            else:
                # Append part of new chunk to string
                responses[-1] += chr(char)

            last_char = char
            
    @utils.check_enabled
    async def __send_query__(self, query_type: str, save_message: bool=True, **kwargs):
            
        error, replied_content = None, None
        r_history = []
        replied_content = ""

        reply: _Union[None, dict] = None
        usage: _Union[None, dict] = None
        self.is_processing = True

        if query_type == "query":
            
            # Put necessary variables here (Doesn't matter weather streaming or not)
            self.chat_history.append(kwargs)

            # TODO: Test async module
            # Reply format: ({"content": "Reply content", "role": "assistent"})
            payload = {
                        "model": self.model.model,
                        "messages": self.chat_history    
            }
            _reply = await _openai_async.chat_complete(api_key=self.oapi, timeout=config.GPT_REQUEST_TIMEOUT, payload=payload)
            
            reply = _reply.json()["choices"][0]
            usage = _reply.json()["usage"]

            if isinstance(reply, dict):
                actual_reply = reply["message"]  
                replied_content = actual_reply["content"]

                self.chat_history.append(dict(actual_reply))
                r_history.extend([kwargs, dict(actual_reply)])
                self.readable_history.append(r_history)
            else:
                raise exceptions.GPTReplyError(reply, type(reply))
            
        elif query_type == "image":
            # Required Arguments: Prompt (String < 1000 chars), Size (String, 256x256, 512x512, 1024x1024)

            image_request: dict = dict(_openai.Image.create(**kwargs))
            if isinstance(image_request, dict) == True:
                image_url = image_request['data'][0]['url']
                replied_content = f"Created Image at {_datetime.datetime.fromtimestamp(image_request['created'])}\nImage Link: {image_url}"
                r_history.extend([{'image': f'User asked GPT to compose the following image: "{kwargs["prompt"]}"'}, {'image_return': image_url}])

                self.readable_history.append(r_history)
            else:
                raise exceptions.GPTReplyError(image_request, type(image_request), dir(image_request))
        
        else:
            error = f"Generic ({query_type})"

        self.__manage_history__(reply, query_type, save_message, usage["total_tokens"] if reply and usage else 0)
        return replied_content if not error or not str(error).strip() else f"Error: {str(error)}"

    @utils.check_enabled
    async def __stream_send_query__(self, save_message: bool=True, **kwargs):
        total_tokens = len(self.model.tokeniser.encode(kwargs["content"]))
        r_history = []
        replied_content = ""

        add_history, self.is_processing = True, True
        self.chat_history.append(kwargs)
        generator_reply = self.__get_stream_parsed_data__(self.chat_history)

        async for chunk in generator_reply:
            stop_reason = chunk["choices"][0]["finish_reason"]
            if stop_reason == None:
                c_token = chunk["choices"][0]["delta"]["content"].encode("latin-1").decode()
                replied_content += c_token
                total_tokens += len(self.model.tokeniser.encode(c_token))

                yield c_token
            elif stop_reason == "length":
                add_history = self.is_active = False
                raise exceptions.GPTReachedLimit()

            elif stop_reason == "content_filter":
                add_history = False
                raise exceptions.GPTContentFilter(kwargs["content"])

        if add_history == True:
            replicate_reply = {"role": "assistant", "content": replied_content}
            self.chat_history.append(replicate_reply)
            r_history.extend([kwargs, replicate_reply])

            self.readable_history.append(r_history)

            self.__manage_history__(generator_reply, "query", save_message, total_tokens)

    @utils.check_enabled
    async def ask(self, query: str) -> str:
        """Asks your GPT Model a question.

        Args:
            query (str): The message you want to ask.

        Raises:
            ChatIsDisabledError: Raised if your chat is disabled.

        Returns:
            str: The reply GPT sent.
        """
        return str(await self.__send_query__(query_type="query", role="user", content=query))

    @utils.check_enabled
    def ask_stream(self, query: str) -> _AsyncGenerator:
        """Asks your GPT Model a question, but the reply is a generator (yield)

        Args:
            query (str): The message you want to ask

        Raises:
            ChatIsDisabledError: Raised if your chat is disabled.

        Returns:
            _AsyncGenerator: Thr reply GPT sent.
        """
        return self.__stream_send_query__(role="user", content=query)
    
    async def start(self) -> str:
        """Sends a start query to GPT.

        Returns:
            str: The welcome message.
        """
        return str(await self.__send_query__(save_message=False, query_type="query", role="system", content="Please give a short and formal introduction to yourself, what you can do, and limitations."))

    def clear(self) -> None:
        """Clears the internal chat history."""
        self.readable_history.clear()
        self.chat_history.clear()
    
    async def stop(self, interaction: _discord.Interaction, history: history.DGHistorySession, save_history: str) -> str:
        """Stops the chat instance.

        Args:
            interaction (_discord.Interaction): The discord interaction instance.
            history (DGHistorySession): A chat history session to upload chat data.
            save_history (str): Weather the chat should be saved. (Will be boolean soon)

        Raises:
            CannotDeleteThread: Raised if the associated thread cannot be deleted.
            DGException: Raised if DG cannot delete your chat thread because of insuffient permissions.

        Returns:
            str: A farewell message.
        """
        if isinstance(self.chat_thread, _discord.Thread) and self.chat_thread.id == interaction.channel_id:
            raise exceptions.CannotDeleteThread(self.chat_thread)
        try:
            farewell = f"Ended chat: {self.display_name} with {config.BOT_NAME}!"
            if save_history == "y":
                history.upload_chat_history(self)
                farewell += f"\n\n\n*Saved chat history with ID: {self.hid}*"
            else:
                farewell += "\n\n\n*Not saved chat history*"

            if isinstance(self.chat_thread, _discord.Thread):
                await self.chat_thread.delete()
            return farewell
        except _discord.Forbidden as e:
            raise exceptions.DGException(f"I have not been granted suffient permissions to delete your thread in this server. Please contact the servers administrator(s).", e)

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} type={self.type}, user={self.user} is_active={self.is_active}>"
    
class DGVoiceChat(DGTextChat):
    """Represents a voice and text DG Chat."""
    def __init__(
            self,
            bot_instance: _commands.Bot,
            _openai_token: str, 
            user: _discord.Member, 
            name: str,
            stream: bool,
            display_name: str, 
            model: models.GPTModelType=config.DEFAULT_GPT_MODEL, 
            associated_thread: _Union[_discord.Thread, None]=None, 
            is_private: bool=True,
            voice: _Union[_discord.VoiceChannel, _discord.StageChannel, None]=None
        ):
        """Represents a voice and text DG Chat.

        Args:
            bot_instance (_commands.Bot): Your bots main instance.
            _openai_token (str): Your OpenAI API Token
            user (_Union[_discord.User, _discord.Member]): The member this text chat will belong too.
            name (str): Name of the chat.
            stream (bool): Weather the chat will be streamed. (Like ChatGPT)
            display_name (str): What the display name of the chat will be.
            model (GPTModelType, optional): Which GPT Model to use. Defaults to DEFAULT_GPT_MODEL.
            associated_thread (_Union[_discord.Thread, None], optional): What the dedicated discord thread is. Defaults to None.
            voice (_Union[_discord.VoiceChannel, _discord.StageChannel, None], optional): (DGVoiceChat only) What voice channel the user is in. This is set dynamically by listeners. Defaults to None.
        """
        super().__init__(bot_instance, _openai_token, user, name, stream, display_name, model, associated_thread, is_private)
        self._voice = voice
        self._client_voice_instance: _Union[_discord.VoiceClient, None] = _discord.utils.get(self.bot.voice_clients, guild=user.guild) # type: ignore because all single instances are `discord.VoiceClient`
        self._is_speaking = False
        self.voice_tss_queue: list[str] = []
    
    @property
    def voice(self):
        return self._voice
    
    @voice.setter
    def voice(self, _voice: _Union[_discord.VoiceChannel, _discord.StageChannel, None]):
        self._voice = _voice
    
    @property
    def type(self):
        return DGChatTypesEnum.VOICE

    @property
    def is_speaking(self) -> bool:
        return self.client_voice.is_playing() if self.client_voice else False
    
    @property
    def client_voice(self) -> _discord.VoiceClient | None:
        return self._client_voice_instance
    
    @client_voice.setter
    def client_voice(self, _bot_vc: _discord.VoiceClient | None) -> None:
        self._client_voice_instance = _bot_vc
        
    async def manage_voice(self) -> _discord.VoiceClient:
        
        voice: _discord.VoiceClient = _discord.utils.get(self.bot.voice_clients, guild=self.voice.guild if self.voice else None) # type: ignore because all single instances are `discord.VoiceClient`
        
        # I know elif exists. I am doing this for effiency.
        if voice and voice.is_connected() and (self.voice == voice.channel):
            pass
        else:
            if voice and voice.is_connected() and (self.voice != voice.channel):
                await voice.move_to(self.voice)
            elif self.voice:
                self.client_voice = voice = await self.voice.connect()
                
            await _asyncio.sleep(5.0)
        
        return voice
    
    @utils.check_enabled
    @utils.has_voice
    async def speak(self, text: str): 
        try:
            self.voice_tss_queue.append(text)
            new_voice = await self.manage_voice()
            
            def _play_voice(index: int, error: _Any=None):
                if not error:
                    if not (index >= len(self.voice_tss_queue)):
                        speed = guildconfig.get_guild_config(new_voice.guild).config_data["speed"]
                        return new_voice.play(_discord.FFmpegPCMAudio(source=ttsmodels.GTTSModel(self.voice_tss_queue[index]).process_text(speed), pipe=True), after=lambda error: _play_voice(index + 1, error))
                        
                    self.voice_tss_queue.clear()
                else:
                    raise exceptions.DGException(f"VoiceError: {str(error)}", log_error=True, send_exceptions=True)
                
            _play_voice(0)
            
        except _discord.ClientException:
            pass
        except IndexError:
            self.voice_tss_queue.clear()
            
        
    @utils.check_enabled
    @utils.has_voice_with_error
    @utils.dg_in_voice_channel
    @utils.dg_is_speaking
    def stop_speaking(self):
        if self.client_voice: self.client_voice.stop()
    
    @utils.check_enabled
    @utils.has_voice_with_error
    @utils.dg_in_voice_channel
    @utils.dg_is_speaking
    def pause_speaking(self):
        if self.client_voice: self.client_voice.pause()
    
    @utils.check_enabled
    @utils.has_voice_with_error
    @utils.dg_in_voice_channel
    @utils.dg_isnt_speaking
    def resume_speaking(self):
        if self.client_voice: self.client_voice.resume()
        
    def __str__(self) -> str:
        return f"<{self.__class__.__name__} type={self.type}, user={self.user}, voice={self.voice}, is_active={self.is_active}>"
    
class DGChatTypesEnum(_Enum):
    """Enums for chat types (text or voice)"""
    TEXT = 1
    VOICE = 2

DGChatType = _Union[DGTextChat, DGVoiceChat]