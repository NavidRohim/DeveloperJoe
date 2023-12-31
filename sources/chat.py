"""Handles conversations between the end-user and the GPT Engine."""

from __future__ import annotations
from curses import start_color

import datetime as _datetime, discord, openai as _openai, random as _random, asyncio as _asyncio, io as _io, speech_recognition as _speech_recognition

from typing import (
    Union as _Union, 
    Any as _Any, 
    AsyncGenerator as _AsyncGenerator,
    TYPE_CHECKING
)

from sources import models
from . import (
    exceptions, 
    confighandler, 
    history, 
    ttsmodels,
    models,
    protectedclass
)
from .common import (
    decorators,
    commands_utils,
    developerconfig,
    common,
    types
)

if TYPE_CHECKING:
    from joe import DeveloperJoe

from .voice import voice_client, reader

__all__ = [
    "GPTConversationContext",
    "DGTextChat",
    "DGVoiceChat"
]
    
class GPTConversationContext:
    """Class that should contain a users conversation history / context with a GPT Model."""
    def __init__(self) -> None:
        """Class that should contain a users conversation history / context with a GPT Model."""
        self._display_context, self._context = [], []
        
    @property
    def context(self) -> list:
        return self._context   
    
    def add_conversation_entry(self, query: str, answer: str, user_type: str) -> list:
        
        data_query = {"role": user_type, "content": query}
        data_reply = {"role": "assistant", "content": answer}
        
        self._context.extend([data_query, data_reply])
        self._display_context.append([data_query, data_reply]) # Add as whole
        
        return self._context
    
    def add_image_entry(self, prompt: str, image_url: str) -> list:
        interaction_data = [{'image': f'User asked GPT to compose the following image: "{prompt}"'}, {'image_return': image_url}]
        self._display_context.append(interaction_data)
        return self._display_context
    
    def get_temporary_context(self, query: str, user_type: str="user"):

        data = {"content": query, "role": user_type}
        _temp_context = self._context.copy()
        _temp_context.append(data)
        
        return _temp_context
        
class DGChats:
        
    def __init__(self,
                member:  discord.Member, 
                bot_instance: DeveloperJoe,
                openai_token: str, 
                name: str,
                stream: bool,
                display_name: str, 
                model: models.GPTModelType | str=confighandler.get_config('default_gpt_model'), 
                associated_thread: _Union[discord.Thread, None]=None,
                is_private: bool=True,
                voice: _Union[discord.VoiceChannel, discord.StageChannel, None]=None
        ):
        """Represents a base DGChat. Do not use, inherit from this.

        Args:
            bot_instance (_DeveloperJoe): _description_
            _openai_token (str): _description_
            user (_Union[discord.User, discord.Member]): _description_
            name (str): _description_
            stream (bool): _description_
            display_name (str): _description_
            model (models.GPTModelType, optional): _description_. Defaults to default_gpt_model. If the config changes while the bot is active, this default will not change as it is defined at runtime.
            associated_thread (_Union[discord.Thread, None], optional): _description_. Defaults to None.
            is_private (bool, optional): _description_. Defaults to True.
            voice (_Union[discord.VoiceChannel, discord.StageChannel, None], optional): _description_. Defaults to None.
        """
        
        self.bot: DeveloperJoe = bot_instance
        self.member: discord.Member = member
        self.time: _datetime.datetime = _datetime.datetime.now()
        self.hid = hex(int(_datetime.datetime.timestamp(_datetime.datetime.now()) + member.id) * _random.randint(150, 1500))
        self.chat_thread = associated_thread
        self.last_channel: developerconfig.InteractableChannel | None = None
        self.oapi = openai_token

        self.name = name
        self.display_name = display_name
        self.stream = stream

        self.model = model if isinstance(model, models.GPTModelType) else commands_utils.get_modeltype_from_name(model)
        self.tokens = 0

        self._private, self._is_active, self.is_processing = is_private, True, False
        self.header = f'{self.display_name} | {self.model.display_name}'
        self.context = GPTConversationContext()
        # Voice attributes
        
        self._voice = voice
        self._client_voice_instance: _Union[voice_client.VoiceRecvClient, None] = discord.utils.get(self.bot.voice_clients, guild=member.guild) # type: ignore because all single instances are `discord.VoiceClient`
        self.proc_packet, self._is_speaking = False, False
        
        self.voice_tss_queue: list[str] = []
        _openai.api_key = self.oapi
    
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
            
    async def __send_query__(self, query_type: str, save_message: bool=True, **kwargs) -> models.AIQueryResponse:
        self.is_processing = True
        # Put necessary variables here (Doesn't matter weather streaming or not)
        # Reply format: ({"content": "Reply content", "role": "assistent"})
        # XXX: Need to transfer this code to GPT-3 / GPT-4 model classes (__askmodel__)
        
        try:
            response: models.AIQueryResponse = await self.model.__askmodel__(kwargs["content"], self.context, "user", save_message)
            
            if save_message:
                self.tokens += response.completion_tokens
            self.is_processing = False

            return response
        except KeyError:
            common.send_fatal_error_warning(f"The Provided OpenAI API key was invalid.")
            return await self.bot.close()
        except TimeoutError:
            raise exceptions.GPTTimeoutError()
        
        return response

    async def __generate_image__(self, save_message: bool=True, **kwargs) -> models.AIImageResponse:
        # Required Arguments: Prompt (String < 1000 chars), Size (String)
        try:
            # XXX: Remove and insert into another function
            
            response = await self.model.__imagegenerate__("Cat doing a backflip", "1024x1024", "dall-e-2")
            if response.is_image == True:
                self.context.add_image_entry(kwargs["prompt"], response.image_url if response.image_url else "Empty")
        except _openai.BadRequestError:
            raise exceptions.GPTContentFilter(kwargs["prompt"])
        
        return response
    
    async def __stream_send_query__(self, query: str, save_message: bool=True, **kwargs) -> _AsyncGenerator[str, None]:
        self.is_processing = True
        try:
            tokens = 0
            ai_reply = self.model.__askmodelstream__(query, self.context, "user", **kwargs)
            async for chunk, token in ai_reply:
                tokens += token
                yield chunk
                
        except exceptions.GPTReachedLimit as e:
            self.is_active = False
            raise e
        except AttributeError:
            self.is_active = False
            raise exceptions.DGException("This model does not support streaming.")
        finally:
            self.is_processing = False
        
        if save_message:
            self.tokens += tokens
    
    async def ask(self, query: str, *_args, **_kwargs) -> str:
        raise NotImplementedError
        
    async def ask_stream(self, query: str, channel: developerconfig.InteractableChannel) -> _AsyncGenerator:
        raise NotImplementedError
    
    async def generate_image(self, prompt: str, resolution: str="512x512") -> models.AIImageResponse:
        raise NotImplementedError
        
    async def start(self) -> None:
        self.bot.add_conversation(self.member, self.display_name, self)
        self.bot.set_default_conversation(self.member, self.display_name)

    def clear(self) -> None:
        raise NotImplementedError
    
    async def stop(self, interaction: discord.Interaction, save_history: bool) -> str:
        raise NotImplementedError

    @property
    def voice(self):
        return self._voice
    
    @voice.setter
    def voice(self, _voice: _Union[discord.VoiceChannel, discord.StageChannel, None]):
        self._voice = _voice
    
    @property
    def type(self):
        return types.DGChatTypesEnum.VOICE

    @property
    def is_speaking(self) -> bool:
        return self.client_voice.is_playing() if self.client_voice else False
    
    @property
    def client_voice(self) -> voice_client.VoiceRecvClient | None:
        return self._client_voice_instance
    
    @property
    def has_voice(self):
        return True if self.voice else False
    
    @client_voice.setter
    def client_voice(self, _bot_vc: voice_client.VoiceRecvClient | None) -> None:
        self._client_voice_instance = _bot_vc 
    
    async def manage_voice_packet_callback(self, member: discord.Member, voice: _io.BytesIO):
        raise NotImplementedError
        
    async def manage_voice(self) -> discord.VoiceClient:
       raise NotImplementedError
   
    async def speak(self, text: str, channel: developerconfig.InteractableChannel): 
       raise NotImplementedError
            
    def stop_speaking(self):
        raise NotImplementedError
    
    def pause_speaking(self):
        raise NotImplementedError
    
    def resume_speaking(self):
        raise NotImplementedError
    
    def listen(self):
        raise NotImplementedError
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
    
    def __str__(self) -> str:
        return self.display_name

class DGTextChat(DGChats):
    """Represents a text-only DG Chat."""
    def __init__(self, 
                member: discord.Member,
                bot_instance: DeveloperJoe,
                _openai_token: str, 
                name: str,
                stream: bool,
                display_name: str, 
                model: models.GPTModelType | str=confighandler.get_config('default_gpt_model'), 
                associated_thread: _Union[discord.Thread, None]=None,
                is_private: bool=True 
        ):
        """Represents a text DG Chat.

        Args:
            bot_instance (DeveloperJoe): The DeveloperJoe client instance. This is not type checked so please be wary.
            _openai_token (str): Your OpenAI API Token
            user (_Union[discord.User, discord.Member]): The member this text chat will belong too.
            name (str): Name of the chat.
            stream (bool): Weather the chat will be streamed. (Like ChatGPT)
            display_name (str): What the display name of the chat will be.
            model (GPTModelType, optional): Which GPT Model to use. Defaults to DEFAULT_GPT_MODEL.
            associated_thread (_Union[discord.Thread, None], optional): What the dedicated discord thread is. Defaults to None.
            is_private (bool): Weather the chat will be private (Only showable to the user) Defaults to True.
        """
        
        super().__init__(
            bot_instance=bot_instance,
            openai_token=_openai_token,
            member=member,
            name=name,
            stream=stream,
            display_name=display_name,
            model=model,
            associated_thread=associated_thread,
            is_private=is_private
        )
    
    @property
    def type(self):
        return types.DGChatTypesEnum.TEXT
    
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
    
    @decorators.check_enabled
    async def ask_stream(self, query: str, channel: developerconfig.InteractableChannel) -> str:
        og_message = await channel.send(developerconfig.STREAM_PLACEHOLDER)
                            
        msg: list[discord.Message] = [og_message]
        reply = self.__stream_send_query__(query, True)
        full_message = f"## {self.header}\n\n"
        i, start_message_at = 0, 0
        sendable_portion = "<>"
        message = ""
        
        try:
            async with channel.typing():
                
                async for t in reply:
                    
                    i += 1
                    full_message += t
                    message += t
                    sendable_portion = full_message[start_message_at * developerconfig.CHARACTER_LIMIT:((start_message_at + 1) * developerconfig.CHARACTER_LIMIT)]
            
                    if len(full_message) and len(full_message) >= (start_message_at + 1) * developerconfig.CHARACTER_LIMIT:
                        await msg[-1].edit(content=sendable_portion)
                        msg.append(await msg[-1].channel.send(developerconfig.STREAM_PLACEHOLDER))

                    start_message_at = len(full_message) // developerconfig.CHARACTER_LIMIT
                    if i and i % developerconfig.STREAM_UPDATE_MESSAGE_FREQUENCY == 0:
                        await msg[-1].edit(content=sendable_portion)

                else:
                    if not msg:
                        await og_message.edit(content=sendable_portion)
                    else:
                        await msg[-1].edit(content=sendable_portion)
                        
        except discord.NotFound:
            self.is_processing = False
            raise exceptions.DGException("Stopped query since someone deleted the streaming message.")
        else:            
            return message
    
    @decorators.check_enabled
    async def generate_image(self, prompt: str, resolution: str = "512x512") -> models.AIImageResponse:
        return await self.__generate_image__(query_type="image", prompt=prompt, size=resolution, n=1)
    
    @decorators.check_enabled
    async def ask(self, query: str, channel: developerconfig.InteractableChannel):
        async with channel.typing():
            reply = await self.__send_query__(query_type="query", role="user", content=query)
            final_user_reply = f"## {self.header}\n\n{reply.response}"
            
            if len(final_user_reply) > developerconfig.CHARACTER_LIMIT:
                file_reply: discord.File = commands_utils.to_file(final_user_reply, "reply.txt")
                await channel.send(file=file_reply)
            else:
                await channel.send(final_user_reply)
                
        return reply
            
    async def start(self, silent: bool=True) -> models.AIQueryResponse | None:
        """Sends a start query to GPT.

        Returns:
            str: The welcome message.
        """
        await super().start()
        if not silent:
            return await self.__send_query__(save_message=False, query_type="query", role="system", content=confighandler.get_config("starting_query"))

    def clear(self) -> None:
        """Clears the internal chat history."""
        self.context._context.clear()
        self.context._display_context.clear()
    
    async def stop(self, interaction: discord.Interaction, save_history: bool) -> str:
        """Stops the chat instance.

        Args:
            interaction (discord.Interaction): The discord interaction instance.
            history (DGHistorySession): A chat history session to upload chat data.
            save_history (str): Weather the chat should be saved. (Will be boolean soon)

        Raises:
            CannotDeleteThread: Raised if the associated thread cannot be deleted.
            DGException: Raised if DG cannot delete your chat thread because of insuffient permissions.

        Returns:
            str: A farewell message.
        """
        with history.DGHistorySession() as dg_history:
            member: discord.Member = commands_utils.assure_class_is_value(interaction.user, discord.Member)
            if isinstance(self.chat_thread, discord.Thread) and self.chat_thread.id == interaction.channel_id:
                raise exceptions.CannotDeleteThread(self.chat_thread)
            try:
                farewell = f"Ended chat: {self.display_name} with {confighandler.get_config('bot_name')}!"
                self.bot.delete_conversation(member, self.display_name)
                self.bot.reset_default_conversation(member)
                
                if save_history == True:
                    dg_history.upload_chat_history(self)
                    farewell += f"\n\n\n*Saved chat history with ID: {self.hid}*"
                else:
                    farewell += "\n\n\n*Not saved chat history*"

                if isinstance(self.chat_thread, discord.Thread):
                    await self.chat_thread.delete()
                return farewell
            except discord.Forbidden as e:
                raise exceptions.DGException(f"I have not been granted suffient permissions to delete your thread in this server. Please contact the servers administrator(s).", e)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} type={self.type}, user={self.member} is_active={self.is_active}>"
    
    def __str__(self) -> str:
        return self.display_name

@protectedclass.protect_class
class DGVoiceChat(DGTextChat):
    
    """Represents a voice and text DG Chat."""
    
    def __init__(
            self,
            member: discord.Member, 
            bot_instance: DeveloperJoe,
            openai_token: str, 
            name: str,
            stream: bool,
            display_name: str, 
            model: models.GPTModelType | str=confighandler.get_config('default_gpt_model'), 
            associated_thread: _Union[discord.Thread, None]=None, 
            is_private: bool=True,
            voice: _Union[discord.VoiceChannel, discord.StageChannel, None]=None
        ):
        """Represents a voice and text DG Chat.

        Args:
            bot_instance (_commands.Bot): Your bots main instance.
            _openai_token (str): Your OpenAI API Token
            user (_Union[discord.User, discord.Member]): The member this text chat will belong too.
            name (str): Name of the chat.
            stream (bool): Weather the chat will be streamed. (Like ChatGPT)
            display_name (str): What the display name of the chat will be.
            model (GPTModelType, optional): Which GPT Model to use. Defaults to DEFAULT_GPT_MODEL.
            associated_thread (_Union[discord.Thread, None], optional): What the dedicated discord thread is. Defaults to None.
            voice (_Union[discord.VoiceChannel, discord.StageChannel, None], optional): (DGVoiceChat only) What voice channel the user is in. This is set dynamically by listeners. Defaults to None.
        """
        super().__init__(member, bot_instance, openai_token, name, stream, display_name, model, associated_thread, is_private)
        self._voice = voice
        self._client_voice_instance: _Union[voice_client.VoiceRecvClient, None] = discord.utils.get(self.bot.voice_clients, guild=member.guild) # type: ignore because all single instances are `discord.VoiceClient`
        self._is_speaking = False
        self.voice_tss_queue: list[str] = []
    
    @classmethod
    def get_protected_name(cls) -> str:
        return "Voice Chat"
    
    @classmethod
    def get_protected_description(cls) -> str:
        return "This represents a voice and text chat."
    
    @classmethod
    def get_error_message(cls, role: discord.Role) -> str:
        return f"You need to be in the role **{role.name}** or higher to use voice capabilities."
    
    @property
    def voice(self):
        return self._voice
    
    @voice.setter
    def voice(self, _voice: _Union[discord.VoiceChannel, discord.StageChannel, None]):
        self._voice = _voice
    
    @property
    def type(self):
        return types.DGChatTypesEnum.VOICE

    @property
    def is_speaking(self) -> bool:
        return self.client_voice.is_playing() if self.client_voice else False
    
    @property
    def is_listening(self) -> bool:
        return self.client_voice.is_listening() if self.client_voice else False
    
    @property
    def client_voice(self) -> voice_client.VoiceRecvClient | None:
        return self._client_voice_instance
    
    @property
    def has_voice(self):
        return True if self.voice else False
    
    @client_voice.setter
    def client_voice(self, _bot_vc: voice_client.VoiceRecvClient | None) -> None:
        self._client_voice_instance = _bot_vc 
    
    async def manage_voice_packet_callback(self, member: discord.Member, voice: _io.BytesIO):
        try:
            if self.proc_packet == False:
                self.proc_packet = True
                
                recogniser = _speech_recognition.Recognizer()

                try:
                    with _speech_recognition.AudioFile(voice) as wav_file:
                        
                        recogniser.adjust_for_ambient_noise(wav_file, 0.7) # type: ignore float values can be used but that package does not have annotations                  
                        data = recogniser.record(wav_file)
                        text = recogniser.recognize_google(data, pfilter=0)
                        
                except _speech_recognition.UnknownValueError:
                    pass
                else:
                    prefix = confighandler.get_guild_config_attribute(member.guild, "voice-keyword").lower()

                    if prefix and isinstance(text, str) and self.last_channel: # Recognise keyword
                        text = text.lower()
                        if keyword_index := text.find(prefix) != -1:
                            text = text[keyword_index + len(prefix):].lstrip()
                            usr_voice_convo = self.bot.get_default_voice_conversation(member)
                        
                            if isinstance(usr_voice_convo, DGVoiceChat): # Make sure user has vc chat
                                await getattr(usr_voice_convo, "ask" if usr_voice_convo.stream == False else "ask_stream")(text, self.last_channel)
                                ...
                                
        except _speech_recognition.RequestError:
            common.send_fatal_error_warning("The connection has been lost, or the operation failed.")       
        except Exception as error:
            common.send_fatal_error_warning(str(error))
        finally:
            self.proc_packet = False
        
    async def manage_voice(self) -> discord.VoiceClient:
        
        voice: voice_client.VoiceRecvClient = discord.utils.get(self.bot.voice_clients, guild=self.voice.guild if self.voice else None) # type: ignore because all single instances are `discord.VoiceClient`
        
        # I know elif exists. I am doing this for effiency.
        if voice and voice.is_connected() and (self.voice == voice.channel):
            pass
        else:
            if voice and voice.is_connected() and (self.voice != voice.channel):
                await voice.move_to(self.voice)
            elif self.voice:
                self.client_voice = await self.voice.connect(cls=voice_client.VoiceRecvClient)
                voice: voice_client.VoiceRecvClient = self.client_voice
            await _asyncio.sleep(5.0)
        
        return voice
    
    @decorators.has_voice
    async def speak(self, text: str, channel: developerconfig.InteractableChannel): 
        try:
            self.last_channel = channel
            self.voice_tss_queue.append(text)
            new_voice = await self.manage_voice()
            
            def _play_voice(index: int, error: _Any=None):
                if not error:
                    if not (index >= len(self.voice_tss_queue)):
                        speed: int = confighandler.get_guild_config_attribute(new_voice.guild, "voice-speed")
                        volume: int = confighandler.get_guild_config_attribute(new_voice.guild, "voice-volume")
                        
                        ffmpeg_pcm = discord.FFmpegPCMAudio(source=ttsmodels.GTTSModel(self.member, self.voice_tss_queue[index]).process_text(speed), executable=developerconfig.FFMPEG, pipe=True)
                        volume_source = discord.PCMVolumeTransformer(ffmpeg_pcm)
                        volume_source.volume = volume
                        
                        return new_voice.play(volume_source, after=lambda error: _play_voice(index + 1, error))
                        
                    self.voice_tss_queue.clear()
                else:
                    raise exceptions.DGException(f"VoiceError: {str(error)}", log_error=True, send_exceptions=True)

            
            if new_voice.is_paused():
                new_voice.stop()
            _play_voice(0)
            
        except discord.ClientException:
            pass
        except IndexError:
            self.voice_tss_queue.clear()
            
        
    @decorators.check_enabled
    @decorators.has_voice_with_error
    @decorators.dg_in_voice_channel
    @decorators.dg_is_speaking
    async def stop_speaking(self):
        """Stops the bots voice reply for a user. (Cannot be resumed)"""
        self.client_voice.stop_playing() # type: ignore checks in decorators
    
    @decorators.check_enabled
    @decorators.has_voice_with_error
    @decorators.dg_in_voice_channel
    @decorators.dg_is_speaking
    async def pause_speaking(self):
        """Pauses the bots voice reply for a user."""
        self.client_voice.pause() # type: ignore Checks done with decorators.
    
    @decorators.check_enabled
    @decorators.has_voice_with_error
    @decorators.dg_in_voice_channel
    @decorators.dg_isnt_speaking
    async def resume_speaking(self):
        """Resumes the bots voice reply for a user."""
        self.client_voice.resume() # type: ignore Checks done with decorators.
    
    @decorators.check_enabled
    @decorators.has_voice_with_error
    @decorators.dg_in_voice_channel
    @decorators.dg_isnt_speaking
    @decorators.dg_isnt_listening
    async def listen(self):
        """Starts the listening events for a users voice conversation."""
        self.client_voice.listen(reader.SentenceSink(self.bot, self.manage_voice_packet_callback, 0.7)) # type: ignore Checks done with decorators.
    
    @decorators.check_enabled
    @decorators.has_voice_with_error
    @decorators.dg_in_voice_channel
    @decorators.dg_is_listening
    async def stop_listening(self):
        """Stops the listening events for a users voice conversation"""
        self.client_voice._reader.sink.cleanup() # type: ignore Checks done with decorators.
        self.client_voice.stop_listening() # type: ignore Checks done with decorators.
        
        
    async def ask(self, query: str, channel: developerconfig.InteractableChannel) -> str:
        
        text = await super().ask(query, channel)
        if isinstance(channel, developerconfig.InteractableChannel):
            await self.speak(str(text), channel)
        else:
            raise TypeError("channel cannot be {}. utils.InteractableChannels only.".format(channel.__class__))
        
        return str(text)

    async def ask_stream(self, query: str, channel: developerconfig.InteractableChannel) -> str:

        text = await super().ask_stream(query, channel)
        if isinstance(channel, developerconfig.InteractableChannel):
            await self.speak(text, channel)
        else:
            raise TypeError("channel cannot be {}. utils.InteractableChannels only.".format(channel.__class__))

        return text
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} type={self.type}, user={self.member}, voice={self.voice}, is_active={self.is_active}>"
    
    def __str__(self) -> str:
        return self.display_name

DGChatType = DGTextChat | DGVoiceChat | DGChats