
from enum import Enum
from typing import TYPE_CHECKING, Protocol, Literal

from discord import Member

if TYPE_CHECKING:
    from ..chat import *

class DGChatTypesEnum(Enum):
    """Enums for chat types (text or voice)"""
    TEXT = 1
    VOICE = 2
    
    def __int__(self) -> int:
        return self.value

class HasMember(Protocol):
    member: Member
    
type Empty = None

type ImageEngine = Literal["dall-e-2", "dall-e-3"]
type Resolution = Literal["256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"]
type AIModels = Literal["AIModel", "gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-4", "gpt-4-vision-preview"]
