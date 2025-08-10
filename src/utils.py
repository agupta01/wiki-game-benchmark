import html
import re
from urllib.parse import unquote

import pandas as pd


class ArticleNotFound(RuntimeError):
    """Exception raised when an article cannot be found or retrieved."""

    pass


class NotImplementedWarning(Warning):
    """Warning raised when a method is not implemented."""

    pass


def get_links_for_entry(content: str) -> list[str]:
    """Takes a page's content and returns a list of links in the content."""
    link_list = re.findall(
        r'<a\s+href=["\'](.*?)["\']>(.*?)</a>',
        html.unescape(unquote(content)),
        re.IGNORECASE | re.DOTALL,
    )
    # link_list is tuples of (link target, highlighted text) so we just want the target
    # also want to remove all section links
    return list(set(filter(lambda x: len(x) > 0, map(lambda x: x[0].split("#", 1)[0], link_list))))


def parse_single_file(path: str, dry_run: bool = False) -> set[str]:
    """Adds links to each entry in the file, returns list of entries with non-null content in the file."""
    df = pd.read_json(path, lines=True).set_index("title")

    entries = set(df.loc[df.text.str.len() > 0].index)

    # Pull links from content
    links = []
    for entry in entries:
        row = df.loc[entry]
        parsed_links = get_links_for_entry(row.text)
        links.append(parsed_links)
        if dry_run:
            print(f"Found {len(parsed_links)} links in {entry} page. {len(row.text)}")

    if not dry_run:
        df.loc[list(entries)].assign(links=links).reset_index().to_json(
            path, orient="records", lines=True
        )

    return entries


def prune_links(
    path: str, all_entries: set[str], dry_run: bool = False
) -> tuple[dict[str, str], int, int]:
    """
    Looks through each entry in file and prunes any links that don't exist in `all_entries`.
    Return total # of links, # pruned, and entry -> filename mapping.
    """
    df = pd.read_json(path, lines=True).set_index("title")

    new_links = []
    total_links = 0
    total_links_pruned = 0
    for entry, row in df.iterrows():
        links = set(row.links)
        pruned_links = links & all_entries
        new_links.append(pruned_links)
        total_links_pruned += len(links) - len(pruned_links)
        total_links += len(pruned_links)
        if dry_run:
            print(
                f"Found {len(links)} links in {entry} page. Pruning to {len(pruned_links)} links."
            )

    # Build mapping
    mapping = dict(zip(df.index, [path] * len(df)))

    if not dry_run:
        df.assign(links=new_links).reset_index().to_json(path, orient="records", lines=True)

    return mapping, total_links, total_links_pruned
