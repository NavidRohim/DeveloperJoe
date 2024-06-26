from abc import ABC, abstractmethod
import time
from typing import Any
import json

# XXX: Listen to type checker

"""Base Query Responses"""

class BaseAIResponse(ABC):
    """Generic base class for an AI response"""
    
    def __init__(self, data: str | dict[Any, Any]={}) -> None:
        if not isinstance(data, str | dict):
            raise TypeError("data should be of type dict or str, not {}".format(type(data)))
        
        self._data: dict = self._to_dict(data)
    
    def _to_dict(self, json_string: str | dict) -> dict:
        if isinstance(json_string, str):
            return json.loads(json_string)
        return json_string
    
    @property
    def raw(self) -> dict:
        return self._data
    
    @raw.setter
    def raw(self, new_data: dict) -> None:
        self._data = self._to_dict(new_data)
    
    @property
    def is_empty(self) -> bool:
        return self.raw == {}
    
    @property
    def timestamp(self) -> int:
        return int(time.time())

class BaseAIQueryResponse(BaseAIResponse, ABC):
    
    @property
    @abstractmethod
    def response(self) -> str:
        pass

class BaseAIImageResponse(BaseAIResponse, ABC):
    
    @property
    @abstractmethod
    def image_url(self) -> str:
        pass

class BaseAIErrorResponse(BaseAIResponse, ABC):
    
    @property
    @abstractmethod
    def error_message(self) -> str:
        pass
    
    @property
    @abstractmethod
    def error_code(self) -> int:
        pass
    
    @property
    @abstractmethod
    def gateway_code(self) -> int:
        pass
    
    @property
    @abstractmethod
    def other_data(self) -> Any | None:
        pass

class BaseAIQueryResponseChunk(BaseAIResponse, ABC):
    
    @property
    @abstractmethod
    def response(self) -> str:
        pass

"""OpenAI Response Classes"""

class OpenAIQueryResponse(BaseAIQueryResponse):
    
    def __init__(self, data: str | dict[Any, Any] = {}) -> None:
        super().__init__(data)
        
        if not self.raw.get("id", None):
            raise ValueError("Incorrect data response.")
    
    def __str__(self) -> str:
        return self.response
    
    @property
    def timestamp(self) -> int:
        return self._data.get("created", 0)
    
    @property
    def response(self) -> str:
        return self.raw["choices"][0]["message"]["content"]
        
    @property
    def finish_reason(self) -> str:
        return self.raw["choices"][0]["finish_reason"]

class OpenAIErrorResponse(BaseAIErrorResponse):
    def __init__(self, data: str | dict[Any, Any] = {}) -> None:
        super().__init__(data)
        
        if not self.raw.get("error", None):
            raise ValueError("Incorrect data response.")
    
    @property
    def error_message(self) -> str:
        return self.raw["error"]["message"]
    
    @property
    def error_type(self) -> str:
        return self.raw["error"]["type"]
    
    @property
    def error_param(self) -> str:
        return self.raw["error"]["param"]
    
    @property
    def error_code(self) -> str:
        return self.raw["error"]["code"]
    
    @property
    def other_data(self) -> Any | None:
        return None
    
    @property
    def gateway_code(self) -> int:
        return 404 # TODO: Find out how to get gateway code
    
class OpenAIImageResponse(BaseAIImageResponse):
    
    def __init__(self, data: str | dict[Any, Any] = {}) -> None:
        super().__init__(data)
        
        if not self.raw.get("data", None):
            raise ValueError("Incorrect data response.")
    
    @property
    def timestamp(self) -> int:
        return self._data.get("created", 0)
    
    @property
    def image_url(self) -> str | None:
        return self.raw["data"][0]["url"]

class OpenAIQueryResponseChunk(BaseAIQueryResponseChunk):
    
    def __init__(self, data: str | dict[Any, Any] = {}) -> None:
        super().__init__(data)
        
        if self.raw.get("object", None) != "chat.completion.chunk":
            raise ValueError("Incorrect chunk data response.")
    
    @property
    def timestamp(self) -> int:
        return self._data.get("created", 0)
    
    @property
    def response(self) -> str:
        return self.raw["choices"][0]["delta"]["content"]
        
    @property
    def finish_reason(self) -> str:
        return self.raw["choices"][0]["finish_reason"]

type OpenAIResponse = OpenAIErrorResponse | OpenAIImageResponse | OpenAIQueryResponse | OpenAIQueryResponseChunk

"""Google AI Response Classes"""

class GoogleAIQueryResponse(BaseAIResponse):
    ...

type GoogleAIResponse = GoogleAIQueryResponse

"""Other Response Classes"""

class AIEmptyResponseChunk(BaseAIResponse):
    
    @property
    def response(self) -> str:
        return ""
    
    def __bool__(self):
        return False
    
    def __len__(self):
        return 0

type EmptyResponse = AIEmptyResponseChunk

"""Response factories"""

def _gpt_response_factory(data: str | dict[Any, Any] = {}) -> OpenAIResponse | EmptyResponse:
    actual_data: dict = data if isinstance(data, dict) else json.loads(data)
    
    if actual_data.get("error", False): # If the response is an error
        return OpenAIErrorResponse(data)
    elif actual_data.get("data", False): # If the response is an image
        return OpenAIImageResponse(data)
    elif actual_data.get("object", False) == "chat.completion.chunk":
        if actual_data["choices"][0]["delta"] != {}:
            return OpenAIQueryResponseChunk(data)
        return AIEmptyResponseChunk(data)
    
    elif actual_data.get("id", False): # If the response is a query
        return OpenAIQueryResponse(data)
    else:
        raise ValueError("Incorrect GPT response data.")

def _google_response_factory(data: str | dict[Any, Any]) -> GoogleAIResponse | EmptyResponse:
    ...