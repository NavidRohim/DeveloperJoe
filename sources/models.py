import tiktoken
import json
import tiktoken
import openai
import vertexai

from vertexai.language_models import ChatModel, ChatMessage
from httpx import ReadTimeout

from google.api_core.exceptions import PermissionDenied
from google.auth.exceptions import DefaultCredentialsError

from typing import (
    Any,
    AsyncGenerator
)

from .chat import GPTConversationContext
from .common import (
    developerconfig,
    types
)
from .exceptions import GPTContentFilter, GPTReachedLimit, DGException, GPTTimeoutError
from sources import confighandler

v_api_key = confighandler.get_api_key("vertex_project_id")
vertex_enabled = False

if " " not in v_api_key:
    vertexai.init(project=confighandler.get_api_key("vertex_project_id"))
    vertex_enabled = True

__all__ = [
    "AIModel",
    "GPT3Turbo",
    "GPT4",
    "PaLM2",
    "GPTModelType",
    "registered_models"
]
# TODO (Not important): add __repr__ and __str__ to Response classes


class AIResponse:

    def __init__(self, data: str | dict[Any, Any] = {}) -> None:
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
        return True


class AIQueryResponse(AIResponse):

    def __init__(self, data: str | dict[Any, Any] = {}) -> None:
        super().__init__(data)

        if not self.raw.get("id", None):
            raise ValueError("Incorrect data response.")

    def __str__(self) -> str:
        return self.response

    @property
    def response_id(self) -> str | None:
        return self._data.get("id", None)

    @property
    def timestamp(self) -> int:
        return self._data.get("created", 0)

    @property
    def completion_tokens(self) -> int:
        return dict(self._data.get("usage", {})).get("completion_tokens", 0)

    @property
    def prompt_tokens(self) -> int:
        return dict(self._data.get("usage", {})).get("prompt_tokens", 0)

    @property
    def total_tokens(self) -> int:
        return self.completion_tokens + self.prompt_tokens

    @property
    def response(self) -> str:
        return self.raw["choices"][0]["message"]["content"]

    @property
    def finish_reason(self) -> str:
        return self.raw["choices"][0]["finish_reason"]


class AIErrorResponse(AIResponse):
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


class AIImageResponse(AIResponse):

    def __init__(self, data: str | dict[Any, Any] = {}) -> None:
        super().__init__(data)

        if not self.raw.get("data", None):
            raise ValueError("Incorrect data response.")

    @property
    def timestamp(self) -> int:
        return self._data.get("created", 0)

    @property
    def is_image(self) -> bool:
        return bool(self.raw.get("data", False))

    @property
    def image_url(self) -> str | None:
        if self.is_image:
            return self.raw["data"][0]["url"]


class AIQueryResponseChunk(AIResponse):

    def __init__(self, data: str | dict[Any, Any] = {}) -> None:
        super().__init__(data)

        if self.raw.get("object", None) != "chat.completion.chunk":
            raise ValueError("Incorrect chunk data response.")

    @property
    def response_id(self) -> str | None:
        return self._data.get("id", None)

    @property
    def timestamp(self) -> int:
        return self._data.get("created", 0)

    @property
    def response(self) -> str:
        return self.raw["choices"][0]["delta"]["content"]

    @property
    def finish_reason(self) -> str:
        return self.raw["choices"][0]["finish_reason"]


Response = AIResponse | AIQueryResponse | AIErrorResponse | AIImageResponse


def _response_factory(data: str | dict[Any, Any] = {}) -> Response:
    actual_data: dict = data if isinstance(data, dict) else json.loads(data)

    if actual_data.get("error", False):  #  If the response is an error
        return AIErrorResponse(data)
    elif actual_data.get("data", False):  #  If the response is an image
        return AIImageResponse(data)
    elif actual_data.get("object", False) == "chat.completion.chunk":
        return AIQueryResponseChunk(data)
    elif actual_data.get("id", False):  #  If the response is a query
        return AIQueryResponse(data)
    else:
        return AIResponse(data)


def _handle_error(response: AIErrorResponse) -> None:
    raise DGException(response.error_message, response.error_code)


async def _gpt_ask_base(query: str, context: GPTConversationContext | None, api_key: str, role: str = "user", save_message: bool = True, model: types.AIModels = "gpt-3.5-turbo-16k") -> AIQueryResponse:
    temp_context: list = context.get_temporary_context(query, role) if context else [
        {"role": role, "content": query}]

    if not isinstance(context, GPTConversationContext | None):
        raise TypeError(
            "context should be of type GPTConversationContext or None, not {}".format(type(context)))

    try:
        async with openai.AsyncOpenAI(api_key=api_key, timeout=developerconfig.GPT_REQUEST_TIMEOUT) as async_openai_client:
            _reply = await async_openai_client.chat.completions.create(model=model, messages=temp_context)
            response = _response_factory(_reply.model_dump_json())

            if isinstance(response, AIErrorResponse):
                _handle_error(response)
            elif isinstance(response, AIQueryResponse):
                if save_message and context:
                    context.add_conversation_entry(
                        query, str(response.response), "user")

                return response

    except (TimeoutError, ReadTimeout):
        raise GPTTimeoutError()

    raise TypeError(
        "Expected AIErrorResponse or AIQueryResponse, got {}".format(type(response)))


async def _gpt_ask_stream_base(query: str, context: GPTConversationContext, api_key: str, role: str, tokenizer: tiktoken.Encoding, model: str, **kwargs) -> AsyncGenerator[tuple[str, int], None]:
    total_tokens = len(tokenizer.encode(query))
    replied_content = ""

    add_history = True

    history: list = context.get_temporary_context(query, role)

    def _is_valid_chunk(chunk_data: str) -> bool:
        try:
            # NOTE: json.loads can take byte array
            if chunk_data not in ['', '[DONE]'] and bool(json.loads(chunk_data)):
                return True
            else:
                return False
        except:
            return False

    async def _get_streamed_response() -> AsyncGenerator[AIQueryResponseChunk | AIErrorResponse, None]:
        async with openai.AsyncOpenAI(api_key=api_key) as async_openai_client:
            _reply = await async_openai_client.chat.completions.create(messages=history, model=model, stream=True)

            async for raw_chunk in _reply.response.aiter_text():
                readable_chunks = filter(
                    _is_valid_chunk, raw_chunk.replace("data: ", "").split("\n\n"))
                for chunk_text in readable_chunks:
                    chunk = _response_factory(chunk_text)

                    if isinstance(chunk, AIQueryResponseChunk | AIErrorResponse):
                        yield chunk
                    else:
                        raise TypeError(
                            "Expected AIErrorResponse or AIQueryResponseChunk, got {}".format(type(chunk)))

    readable_chunks = _get_streamed_response()

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
                raise GPTContentFilter(kwargs["content"])

    if add_history == True:
        context.add_conversation_entry(query, replied_content, role)


async def _gpt_image_base(prompt: str, resolution: types.Resolution, image_engine: types.ImageEngine, api_key: str) -> AIImageResponse:
    async with openai.AsyncOpenAI(api_key=api_key) as async_openai_client:
        _image_reply = await async_openai_client.images.generate(prompt=prompt, size=resolution, model=image_engine)
        response = _response_factory(_image_reply.model_dump_json())

        if isinstance(response, AIErrorResponse):
            _handle_error(response)
        elif isinstance(response, AIImageResponse):
            return response

    raise TypeError(
        "Expected AIImageResponse or AIErrorResponse, got {}".format(type(response)))


class AIModel:

    _model: types.AIModels = 'gpt-3.5-turbo'
    _display_name: str = ""
    _description: str = ""
    _api_key: str = "openai_api_key"
    _enabled: bool = True

    @classmethod
    @property
    def model(cls) -> types.AIModels:
        """Returns the actual model name that is used to send communication requests."""
        return cls._model

    @classmethod
    @property
    def tokeniser(cls) -> tiktoken.Encoding:
        """The encoding used to calculate the amount of tokens used."""
        return tiktoken.encoding_for_model(cls.model)

    @classmethod
    @property
    def description(cls) -> str:
        """The description for the model."""
        return cls._description

    @classmethod
    @property
    def display_name(cls) -> str:
        """User-readable display name for the model."""
        return cls._display_name

    @classmethod
    @property
    def enabled(cls) -> bool:
        """If the model is enabled."""
        return cls._enabled

    @classmethod
    def __repr__(cls):
        return f"<{cls.__name__} display_name={cls.display_name}, model={cls.model}>"

    @classmethod
    def __str__(cls) -> str:
        return cls._model

    @classmethod
    async def __askmodel__(cls, query: str, context: GPTConversationContext | None, role: str = "user", save_message: bool = True, **kwargs) -> AIQueryResponse:
        raise DGException("This model does not support text generation.")

    @classmethod
    def __askmodelstream__(cls, query: str, context: GPTConversationContext, role: str = "user", **kwargs) -> AsyncGenerator[tuple[str, int], None]:
        raise DGException(
            "This model does not support streaming text generation.")

    @classmethod
    async def __imagegenerate__(cls, prompt: str, resolution: types.Resolution = "256x256", image_engine: types.ImageEngine = "dall-e-2") -> AIImageResponse:
        raise DGException("This model does not support image generation.")


class GPT3Turbo(AIModel):
    """Generative Pre-Trained Transformer 3.5 Turbo (gpt-3.5-turbo)"""

    _model: types.AIModels = "gpt-3.5-turbo-16k"
    _display_name: str = "GPT 3.5 Turbo"
    _description: str = "Good for generating text and general usage. Cost-effective."
    _api_key: str = "openai_api_key"

    @classmethod
    def __eq__(cls, __value: AIModel) -> bool:
        return cls.model == __value.model

    @classmethod
    async def __askmodel__(cls, query: str, context: GPTConversationContext | None, role: str = "user", save_message: bool = True, **kwargs) -> AIQueryResponse:
        return await _gpt_ask_base(query, context, confighandler.get_api_key(cls._api_key), role, save_message, cls.model, **kwargs)

    @classmethod
    def __askmodelstream__(cls, query: str, context: GPTConversationContext, role: str = "user", **kwargs) -> AsyncGenerator[tuple[str, int], None]:
        return _gpt_ask_stream_base(query, context, confighandler.get_api_key(cls._api_key), role, cls.tokeniser, cls.model, **kwargs)

    @classmethod
    async def __imagegenerate__(cls, prompt: str, resolution: types.Resolution = "256x256", image_engine: types.ImageEngine = "dall-e-2",) -> AIImageResponse:
        return await _gpt_image_base(prompt, resolution, image_engine, confighandler.get_api_key(cls._api_key))


class GPT4(AIModel):
    """Generative Pre-Trained Transformer 4 (gpt-4)"""

    _model: str = "gpt-4"
    _display_name: str = "GPT 4"
    _description: str = "Better than GPT 3 Turbo at everything. Would stay with GPT 3 for most purposes-- Can get expensive."
    _api_key = "openai_api_key"

    @classmethod
    def __eq__(cls, __value: AIModel) -> bool:
        return cls.model == __value.model

    @classmethod
    async def __askmodel__(cls, query: str, context: GPTConversationContext | None, role: str = "user", save_message: bool = True, **kwargs) -> AIQueryResponse:
        return await _gpt_ask_base(query, context, confighandler.get_api_key(cls._api_key), role, save_message, cls.model, **kwargs)

    @classmethod
    def __askmodelstream__(cls, query: str, context: GPTConversationContext, role: str = "user", **kwargs) -> AsyncGenerator[tuple[str, int], None]:
        return _gpt_ask_stream_base(query, context, confighandler.get_api_key(cls._api_key), role, cls.tokeniser, cls.model, **kwargs)

    @classmethod
    async def __imagegenerate__(cls, prompt: str, resolution: types.Resolution = "256x256", image_engine: types.ImageEngine = "dall-e-2",) -> AIImageResponse:
        return await _gpt_image_base(prompt, resolution, image_engine, confighandler.get_api_key(cls._api_key))


class PaLM2(AIModel):

    _model: str = "chat-bison@002"
    _display_name: str = "PaLM 2"
    _description: str = f"Very fast, but is costly. Good at general tasks and coding, can appear a bit dumb when treating it like a human. I would recommend using GPT 3 Turbo instead as it can also do the stuff {
        _display_name} can do. Use GPT 4 if enabled."
    _api_key: str = "vertex_project_id"
    _enabled = vertex_enabled

    parameters = {
        "temperature": 0.2,
        "max_output_tokens": 256,
        "top_p": 0.8,
        "top_k": 40
    }
    errors = {
        "CONSUMER_INVALID": "Given Project ID for Vertex AI is invalid. Check Google Cloud Console for correct ID."
    }

    @staticmethod
    def _load_translate_context_from_gpt(context: GPTConversationContext | list[types.AIInteraction]) -> list[ChatMessage]:
        if isinstance(context, GPTConversationContext):
            return [ChatMessage(reply_entry["content"], "user" if reply_entry["role"] == "user" else "bot") for reply_entry in context._context]
        else:
            return [ChatMessage(reply_entry["content"], "user" if reply_entry["role"] == "user" else "bot") for reply_entry in context]

    @staticmethod
    def _dump_translate_context_to_gpt(context: list[ChatMessage]) -> list[dict[str, str]]:
        return [{"role": "user" if message.author != "bot" else "bot", "content": message.content} for message in context]

    @classmethod
    def __eq__(cls, __value: AIModel) -> bool:
        return cls.model == __value.model

    @classmethod
    async def __askmodel__(cls, query: str, context: GPTConversationContext | None, role: str = "user", save_message: bool = True, __model: str | None = None, **kwargs) -> AIQueryResponse:
        try:
            chat_model = ChatModel.from_pretrained(cls._model)
            gpt_temporary_context: list[types.AIInteraction] = context.get_temporary_context(
                query, role) if context else [{"role": role, "content": query}]
            temporary_context = cls._load_translate_context_from_gpt(
                gpt_temporary_context)
            temporary_context.pop()

            chat = chat_model.start_chat(
                message_history=temporary_context, **cls.parameters)
            response = await chat.send_message_async(query, **cls.parameters)

            if save_message and context:
                context.add_conversation_entry(query, response.text, "user")

            emulated_gpt_response = {"id": "PaLM2", "choices": [{"finish_reason": None, "message": {
                "content": response.text}}]}  # Sadly we have to emulate the json response from GPT
            return AIQueryResponse(emulated_gpt_response)

        # PermissionDenied is a class of google.api_core.exceptions
        except PermissionDenied as google_response_error:
            if google_response_error.reason:
                raise DGException(cls.errors.get(
                    google_response_error.reason, google_response_error.message))
            raise DGException(f"Google Cloud Error: {google_response_error}")

        # DefaultCredentialsError is a class of google.auth.exceptions
        except DefaultCredentialsError as google_response_error:
            raise DGException(
                "Host machine not logged into gcloud. The host machine can login by executing `gcloud auth application-default set-quota-project <Project ID>` in the terminal.")


GPTModelType = GPT3Turbo | GPT4 | PaLM2
registered_models = {
    "gpt-4": GPT4,
    "gpt-3.5-turbo-16k": GPT3Turbo,
    "chat-bison@002": PaLM2
}
