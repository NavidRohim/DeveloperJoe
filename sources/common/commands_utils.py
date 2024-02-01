"""Utils that commands use."""

from __future__ import annotations
from typing import TYPE_CHECKING

import discord, io, typing

from .. import (
    exceptions,
    models,
    errors
)
from . import (
    developerconfig,
)

if TYPE_CHECKING:
    from .. import (
        chat
    )
    
__all__ = [
    "to_file",
    "to_file_fp",
    "is_voice_conversation",
    "is_correct_channel",
    "assure_class_is_value",
    "get_modeltype_from_name",
    "modeltype_is_in_models",
    "in_correct_channel",
    "get_correct_channel"
]

true_to_yes = lambda text: str(text).replace("True", "Yes")

def to_file_fp(fp: str) -> discord.File:
    """Get `File` object from a filepath.

    Args:
        fp (str): Path of the file (aka a filepath lol)

    Returns:
        _File: The object made from the filepath.
    """
    return discord.File(fp)

def to_file(content: str, name: str) -> discord.File:
    """From `str` to `discord.File`"""
    f = io.BytesIO(content.encode())
    f.name = name
    return discord.File(f)

def is_voice_conversation(conversation: chat.DGChatType | None) -> chat.DGVoiceChat:
    if isinstance(conversation, chat.DGVoiceChat):
        return conversation
    raise exceptions.ConversationError(errors.ConversationErrors.NO_CONVO)

def assure_class_is_value(object, __type: type):
    """For internal use. Exact same as `isinstance` but raises `IncorrectInteractionSetting` if the result is `False`."""
    if type(object) == __type:
        return object
    raise exceptions.ConversationError(errors.ConversationErrors.CONVO_CANNOT_TALK)

def is_correct_channel(channel: typing.Any) -> developerconfig.InteractableChannel:
    if isinstance(channel, developerconfig.InteractableChannel):
        return channel
    raise exceptions.ConversationError(errors.ConversationErrors.CONVO_CANNOT_TALK)

def get_modeltype_from_name(name: str) -> models.AIModelType:
    """Get GPT Model from actual model name. (Get `models.GPT4` from entering `gpt-4`)"""
    if name in list(models.registered_models):
        return models.registered_models[name]
    raise exceptions.DGException(f"Inconfigured GPT model setup. This is a fatal coding error and should be sorted as such. \n\n**Debug Information**\n\nFailed Model: {name}\nModel Map: {models.registered_models}\nName Parameter Type: {type(name)}")

def modeltype_is_in_models(name: str):
    return name in list(models.registered_models)

def in_correct_channel(interaction: discord.Interaction) -> bool:
    return bool(interaction.channel) == True and bool(interaction.channel.guild if interaction.channel else False)


def get_correct_channel(channel: typing.Any | None) -> developerconfig.InteractableChannel:
    if channel and isinstance(channel, developerconfig.InteractableChannel):
        return channel
    raise exceptions.ConversationError(errors.ConversationErrors.CANNOT_CONVO)