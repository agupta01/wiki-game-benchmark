from pydantic import BaseModel


class Page(BaseModel):
    title: str
    content: str
    links: list[str]


class StepInput(BaseModel):
    current_page: Page
    goal_page_title: str


class StepOutput(BaseModel):
    selected_link: str


def construct_page(title: str, content: str) -> Page:
    """Extracts the links from the page to construct a page object."""
    return Page(title="", content="", links=[])
