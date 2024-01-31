"""Handles conversations between the end-user and the GPT Engine."""

from __future__ import annotations

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
    exceptions,
    errors
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

_openai.api_key = confighandler.get_api_key("openai_api_key")
__all__ = [
    "DGTextChat",
    "DGVoiceChat"
]
    

"""
async for chunk in readable_chunks:
        if isinstance(chunk, AIErrorResponse):
            _handle_error(chunk)
        else:
            stop_reason = chunk.finish_reason

            if stop_reason == None:
                c_token = chunk.response
                replied_content += c_token
                total_tokens += len(tokenizer.encode(c_token))

                yield (c_token, total_tokens)
                
            elif stop_reason == "length":
                add_history = False
                raise GPTReachedLimit()

            elif stop_reason == "content_filter":
                add_history = False
                raise GPTContentFilter(query)

    if add_history == True and isinstance(context, GPTConversationContext):
        context.add_conversation_entry(query, replied_content, "user")
""" # TODO: Implement into ask_stream
    
class DGChat:
        
    def __init__(self,
                member:  discord.Member, 
                bot_instance: DeveloperJoe,
                name: str,
                stream: bool,
                display_name: str, 
                model: models.AIModelType | str=confighandler.get_config('default_gpt_model'), 
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
            model (models.AIModelType, optional): _description_. Defaults to default_gpt_model. If the config changes while the bot is active, this default will not change as it is defined at runtime.
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

        self.name = name
        self.display_name = display_name
        self.stream = stream

        if isinstance(model, models.AIModelType):
            self.model: models.AIModelType = model(member) # type: ignore shutup I did the check
        else:
            self.model: models.AIModelType = commands_utils.get_modeltype_from_name(model)(member)

        self._private, self._is_active, self.is_processing = is_private, True, False
        self.header = f'{self.display_name} | {self.model.display_name}'
    
        # Voice attributes
        
        self._voice = voice
        self._client_voice_instance: _Union[voice_client.VoiceRecvClient, None] = discord.utils.get(self.bot.voice_clients, guild=member.guild) # type: ignore because all single instances are `discord.VoiceClient`
        self.proc_packet, self._is_speaking = False, False
        
        self.voice_tss_queue: list[str] = []
    
    async def get_personal_channel_or_current(self, channel: discord.abc.Messageable) -> discord.abc.Messageable:
        
        if not self.private:
            return channel
        elif self.private and self.member.dm_channel == None:
            return await self.member.create_dm()
        elif isinstance(self.member.dm_channel, discord.DMChannel):
            return self.member.dm_channel
        
        return channel
            
    
    
    @property
    def is_active(self) -> bool:
        return self._is_active
    
    @is_active.setter
    def is_active(self, value: bool):
        self._is_active = value
    
    @property
    def private(self) -> bool:
        return self._private

    @property
    def context(self) -> models.ReadableContext:
        return self.model.context
    
    @private.setter
    def private(self, is_p: bool):
        self._private = is_p
    
    async def ask(self, query: str, *_args, **_kwargs) -> str:
        raise NotImplementedError
        
    async def ask_stream(self, query: str, channel: developerconfig.InteractableChannel) -> _AsyncGenerator:
        raise NotImplementedError
    
    async def generate_image(self, prompt: str, resolution: str="512x512") -> models.AIImageResponse:
        raise NotImplementedError
        
    async def start(self) -> None:
        self.bot.add_conversation(self.member, self.display_name, self)
        self.bot.set_default_conversation(self.member, self.display_name)
        self.model.start_chat()

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

class DGTextChat(DGChat):
    """Represents a text-only DG Chat."""
    def __init__(self, 
                member: discord.Member,
                bot_instance: DeveloperJoe,
                name: str,
                stream: bool,
                display_name: str, 
                model: models.AIModelType | str=confighandler.get_config('default_gpt_model'), 
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
            model (AIModelType, optional): Which GPT Model to use. Defaults to DEFAULT_GPT_MODEL.
            associated_thread (_Union[discord.Thread, None], optional): What the dedicated discord thread is. Defaults to None.
            is_private (bool): Weather the chat will be private (Only showable to the user) Defaults to True.
        """
        
        super().__init__(
            bot_instance=bot_instance,
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
        
        if self.model.can_stream == False:
            raise exceptions.DGException(f"{self.model} does not support streaming text.")
        
        private_channel = self.get_personal_channel_or_current(channel)
        og_message = await private_channel.send(developerconfig.STREAM_PLACEHOLDER)
        self.is_processing = True
        
        async def _stream_reply():
            try:
                ai_reply: _AsyncGenerator[models.AIQueryResponseChunk | models.AIErrorResponse, None] = self.model.ask_model_stream(query)
                async for chunk in ai_reply:
                    if isinstance(chunk, models.AIQueryResponseChunk):
                        yield chunk.response
                    
                    elif isinstance(chunk, models.AIErrorResponse):
                        models._handle_error(chunk)
                    
                    # TODO: Must sort out stop_reason (If is ResponseChunk)
                    
            except discord.Forbidden as e: # XXX: old exception was GPTReachedLimit. Must conform to new model systems. New exception (Forbidden) is temp
                self.is_active = False
                raise e
            except AttributeError:
                self.is_active = False
                raise exceptions.DGException("This model does not support streaming.")
            finally:
                self.is_processing = False
                
        msg: list[discord.Message] = [og_message]
        reply = _stream_reply()
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
            self.context.add_conversation_entry(query, full_message)
            return message
    
    @decorators.check_enabled
    async def generate_image(self, prompt: str, resolution: str = "512x512") -> models.AIImageResponse:
        if self.model.can_generate_images == False:
            raise exceptions.DGException(f"{self.model} does not support image generation.")
        
        try:
            image = await self.model.generate_image(prompt)
            self.context.add_image_entry(prompt, str(image.image_url))
            return image
        except _openai.BadRequestError:
            raise exceptions.DGException(errors.AIErrors.AI_REQUEST_ERROR)
        
    @decorators.check_enabled
    async def ask(self, query: str, channel: developerconfig.InteractableChannel):
        if self.model.can_talk == False:
            raise exceptions.DGException(f"{self.model} cannot talk.")
        
        async def _send_query():
            self.is_processing = True
            # Put necessary variables here (Doesn't matter weather streaming or not)
            # Reply format: ({"content": "Reply content", "role": "assistent"})
            
            try:
                response: models.AIQueryResponse = await self.model.ask_model(query)
                self.is_processing = False

                return response
            except KeyError:
                common.send_fatal_error_warning(f"The Provided OpenAI API key was invalid.")
                return await self.bot.close()
            except TimeoutError:
                raise exceptions.DGException(errors.AIErrors.AI_TIMEOUT_ERROR)
            
        async with channel.typing():
            reply = await _send_query()
            final_user_reply = f"## {self.header}\n\n{reply.response}"
            private_channel = await self.get_personal_channel_or_current(channel)
            
            if len(final_user_reply) > developerconfig.CHARACTER_LIMIT:
                file_reply: discord.File = commands_utils.to_file(final_user_reply, "reply.txt")
                await private_channel.send(file=file_reply)
            else:
                await private_channel.send(final_user_reply)
        
        self.context.add_conversation_entry(query, reply.response)        
        return reply
            
    async def start(self) -> None:
        """Sends a start query to GPT.

        Returns:
            str: The welcome message.
        """
        await super().start()

    def clear(self) -> None:
        """Clears the internal chat history."""
        # FIXME: Waiting to be transfered to new model system

        self.model.clear_context()
        self.context.clear()
    
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
                raise exceptions.DGException(errors.ConversationErrors.CANNOT_STOP_IN_CHANNEL)
            try:
                farewell = f"Ended chat: {self.display_name} with {confighandler.get_config('bot_name')}!"
                await self.bot.delete_conversation(member, self.display_name)
                self.bot.reset_default_conversation(member)
                
                if save_history == True:
                    dg_history.upload_chat_history(self)
                    farewell += f"\n\n\n*Saved chat history with ID: {self.hid}*"
                else:
                    farewell += "\n\n\n*Not saved chat history*"

                if isinstance(self.chat_thread, discord.Thread):
                    await self.chat_thread.delete()
                return farewell
            
            # TODO: Return History ID instead of a message
            
            except discord.Forbidden as e:
                raise exceptions.DGException(f"I have not been granted suffient permissions to delete your thread in this server. Please contact the servers administrator(s).", e)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} type={self.type}, user={self.member} is_active={self.is_active}>"
    
    def __str__(self) -> str:
        return self.display_name


class DGVoiceChat(DGTextChat):
    
    """Represents a voice and text DG Chat."""
    
    def __init__(
            self,
            member: discord.Member, 
            bot_instance: DeveloperJoe,
            name: str,
            stream: bool,
            display_name: str, 
            model: models.AIModelType | str=confighandler.get_config('default_gpt_model'), 
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
            model (AIModelType, optional): Which GPT Model to use. Defaults to DEFAULT_GPT_MODEL.
            associated_thread (_Union[discord.Thread, None], optional): What the dedicated discord thread is. Defaults to None.
            voice (_Union[discord.VoiceChannel, discord.StageChannel, None], optional): (DGVoiceChat only) What voice channel the user is in. This is set dynamically by listeners. Defaults to None.
        """
        super().__init__(member, bot_instance, name, stream, display_name, model, associated_thread, is_private)
        self._voice = voice
        self._client_voice_instance: _Union[voice_client.VoiceRecvClient, None] = discord.utils.get(self.bot.voice_clients, guild=member.guild) # type: ignore because all single instances are `discord.VoiceClient`
        self._is_speaking = False
        self.voice_tss_queue: list[str] = []
    
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
    
    async def cleanup_voice(self):
        self.voice_tss_queue.clear()
        await self.stop_listening()
        await self.stop_speaking()
        
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
                self.client_voice = await self.voice.connect(cls=voice_client.VoiceRecvClient) # type: ignore shutup it'll work. it conforms
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

DGChatType = DGTextChat | DGVoiceChat | DGChat