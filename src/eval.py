from typing import Callable

from src.clients import create_client
from src.models import (  # noqa: F401
    OllamaSupportedModel,
    OpenRouterSupportedModel,
    Page,
    Provider,
    StepInput,
    StepOutput,
)
from src.signatures import get_next_page
from src.utils import ArticleNotFound
from src.wiki_db import WikiData


def get_next_article(
    current_article: Page,
    goal: str,
    invoke: Callable[[Page, str], str],
    wiki_data: WikiData,
    ctrl_f: bool = False,
) -> Page:
    """Get the next article by invoking the function and looking up the result in LMDB.

    Args:
        current_article: The current Page object
        goal: The goal page to get to
        invoke: A callable that takes a Page and returns a link string
        wiki_data: WikiData instance for looking up article locations
        ctrl_f: (Default False) don't run invocation if the goal link is on the page

    Returns:
        Page object for the next article

    Raises:
        ArticleNotFound: If the article is not found in the index or cannot be retrieved
    """
    if ctrl_f and goal in current_article.links:
        # Shortcut if 1 step away
        return wiki_data.get_page(goal)
    # Get the next link from the invoke function
    next_link = invoke(current_article, goal)

    # Validate the invoke result
    if next_link is None:
        raise ArticleNotFound("Invoke function returned None")

    if not next_link or not next_link.strip():
        raise ArticleNotFound("Invoke function returned empty link")

    # Look up the article
    return wiki_data.get_page(next_link)


def invoke(
    page: Page,
    goal_page_title: str,
) -> str:
    """Calls a LM on a page to get next link (str)."""
    model_output = get_next_page(
        input=StepInput(
            current_page=page,
            goal_page_title=goal_page_title,
        ),
    )
    return model_output.output.selected_link


def run_one_game(
    start_page_title: str,
    goal_page_title: str,
    invoke: Callable[[Page, str], str],
    db: WikiData,
    max_steps: int = 10,
    ctrl_f: bool = False,
) -> list[Page]:
    """
    Runs one round of the Wikipedia Game.

    Args:
        start_page_title: Title of the starting page
        goal_page_title: Title of the goal page
        invoke: Function to invoke to get the next link
        db: WikiData object for database access
        max_steps: Maximum number of steps allowed (default 10)
        ctrl_f: (Default False) don't run invocation if the goal link is on the page

    Returns:
        List of Page objects representing the path taken to reach the goal page

    Raises:
        ArticleNotFound: If the article is not found in the index or cannot be retrieved
    """
    curr_article = db.get_page(start_page_title)
    history = [curr_article]
    for step in range(max_steps):
        curr_article = get_next_article(
            curr_article,
            goal_page_title,
            invoke,
            wiki_data=db,
            ctrl_f=ctrl_f,
        )
        if curr_article.title == goal_page_title:
            print("Done!")
            return history
        print(curr_article.title)
        history.append(curr_article)
    print(f"Max Steps of {max_steps} reached, but did not complete.")
    return history


def path_transformer(original_path: str) -> str:
    """Transforms relative path in index so that LMDB can be called anywhere."""
    return original_path.replace("..", ".")


if __name__ == "__main__":
    provider = Provider.OLLAMA
    model = OllamaSupportedModel.QWEN3_0_6B

    # Create client using factory
    client = create_client(provider, model)

    start_page_title = "Alain Connes"
    goal_page_title = "France"

    db = WikiData("./index.lmdb", path_transformer)

    history = run_one_game(start_page_title, goal_page_title, client.invoke, db)
