from enum import Enum, EnumMeta

from pydantic import BaseModel


class StrEnumMeta(EnumMeta):
    def __contains__(cls, item):
        return any(item == member.value for member in cls)


class Provider(str, Enum, metaclass=StrEnumMeta):
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"


class SupportedModel(str, Enum, metaclass=StrEnumMeta):
    pass


class OpenRouterSupportedModel(SupportedModel):
    QWEN3_DEEPSEEK_8B = "deepseek/deepseek-r1-0528-qwen3-8b:free"


class OllamaSupportedModel(SupportedModel):
    QWEN3_0_6B = "qwen3:0.6b"


class Page(BaseModel):
    title: str
    content: str
    links: list[str]


class StepInput(BaseModel):
    current_page: Page
    goal_page_title: str


class StepOutput(BaseModel):
    selected_link: str
