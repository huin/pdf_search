"""
PDF research tool for LLM use.

Provides search, folder listing, browsing, and full-text retrieval
against the local PDF search API. Use this script for all research
operations — do not write new scripts.

\b
Search syntax:
    "exact phrase"            phrase match
    -word                     exclude term
    word1 OR word2            either term
    word*                     prefix match
    path:"Folder Name"        restrict to folder
    filename:term             match filename only
    word1 NEAR/5 word2        proximity match

\b
Research workflow:
    1. Run `folders` to discover available collections
    2. Run `research "topic"` or `research "topic" --path "Folder"` for a survey
    3. Paginate with --offset and --passage-offset to read more
    4. Use `browse "Folder"` to see specific files by ID

\b
Usage:
  pdf-search pdf_research search "query" [options]
  pdf-search pdf_research folders [path]
  pdf-search pdf_research browse [path]
  pdf-search pdf_research text <doc_id> [--query "terms"]
  pdf-search pdf_research stats
"""

import functools
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, NotRequired, TypedDict, cast

import click

# Use config for port/host if available
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from pdf_search import config

    _PORT = config.PORT
    _HOST = "localhost"
except ImportError:
    _PORT = 5000
    _HOST = "localhost"

BASE_URL = f"http://{_HOST}:{_PORT}"


def _get(
    endpoint: str,
    params: dict[str, str | int | list[str | int]] | None = None,
) -> object:
    url = BASE_URL + endpoint
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read())


# --- API calls ---


class _ResearchDataItem(TypedDict):
    id: int
    path: str
    passages: list[str]
    total_passages: int
    passage_offset: int


class _ResearchData(TypedDict):
    query: str
    total: int
    offset: int
    limit: int
    results: list[_ResearchDataItem]


def _research(
    query: str,
    limit: int = 20,
    offset: int = 0,
    passages: int = 10,
    passage_offset: int = 0,
) -> _ResearchData:
    """Full-text search returning documents with extracted passages."""
    return cast(
        _ResearchData,
        _get(
            "/api/research",
            {
                "q": query,
                "limit": limit,
                "offset": offset,
                "passages": passages,
                "passage_offset": passage_offset,
            },
        ),
    )


class _SearchDataItem(TypedDict):
    id: int
    path: str
    size: int
    snippet: str


class _SearchData(TypedDict):
    query: str
    count: int
    results: list[_SearchDataItem]


def _search(query: str, limit: int = 20, offset: int = 0) -> _SearchData:
    """Search returning document metadata and snippets (no full passages)."""
    return cast(_SearchData, _get("/search", {"q": query, "limit": limit, "offset": offset}))


class _FoldersDataItem(TypedDict):
    name: str
    count: int


class _FoldersData(TypedDict):
    current_path: NotRequired[str]
    folders: list[_FoldersDataItem]


def _folders(path: str | None = "") -> _FoldersData:
    """List subdirectories at the given path with file counts."""
    params = {}
    if path:
        params["path"] = path
    return cast(_FoldersData, _get("/folders", params))


class _BrowseDataItem(TypedDict):
    id: int
    filename: str
    size: int
    modified: str


class _BrowseData(TypedDict):
    path: NotRequired[str]
    count: int
    results: list[_BrowseDataItem]


def _browse(path: str | None = "") -> _BrowseData:
    """List PDF files directly in the given folder path."""
    params = {}
    if path:
        params["path"] = path
    return cast(_BrowseData, _get("/browse", params))


class _StatsData(TypedDict):
    total_documents: int
    total_size: int


def _stats() -> _StatsData:
    """Return database statistics (total documents, total size)."""
    return cast(_StatsData, _get("/stats"))


def text(doc_id: int) -> object:
    """Return the full extracted text of a document by ID."""
    return _get(f"/text/{doc_id}", {"raw": "1"})


# --- Output formatters ---


def print_research(data: _ResearchData) -> None:
    total = data["total"]
    offset = data["offset"]
    limit = data["limit"]
    shown = len(data["results"])
    print(f"Query: {data['query']}")
    print(f"Total matching documents: {total}  (offset={offset}, limit={limit}, showing {shown})")
    if total > offset + limit:
        print(f"  -> More results available: use --offset {offset + limit}")
    print()
    for doc in data["results"]:
        tp = doc["total_passages"]
        po = doc["passage_offset"]
        shown_p = len(doc["passages"])
        print(f"=== {doc['path']}  [id={doc['id']}, passages={tp}] ===")
        if tp > po + shown_p:
            print(f"  -> More passages: use --passage-offset {po + shown_p}")
        for i, passage in enumerate(doc["passages"], po + 1):
            print(f"  [{i}] {passage.strip()}")
            print()


def print_folders(data: _FoldersData) -> None:
    path = data.get("current_path", "")
    label = f"/{path}" if path else "(root)"
    print(f"Folders in {label}:")
    for f in data["folders"]:
        print(f"  {f['name']}/  ({f['count']} files)")
    if not data["folders"]:
        print("  (none)")


def print_browse(data: _BrowseData) -> None:
    path = data.get("path", "")
    label = f"/{path}" if path else "(root)"
    print(f"Files in {label}:  ({data['count']} total)")
    for doc in data["results"]:
        print(f"  [{doc['id']}] {doc['filename']}  {doc['size']}  {doc['modified']}")


def print_stats(data: _StatsData) -> None:
    print(f"Total documents: {data['total_documents']}")
    print(f"Total size:      {data['total_size']}")


# --- CLI ---


@click.group(help=__doc__)
def command() -> None:
    pass


def _handle_urlerror[T, **P](f: Callable[P, T]) -> Callable[P, T]:
    @functools.wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return f(*args, **kwargs)
        except urllib.error.URLError as e:
            print(
                f"Error: cannot reach API at {BASE_URL} — is the server running?",
                file=sys.stderr,
            )
            print(f"  {e}", file=sys.stderr)
            sys.exit(1)

    return wrapper


_arg_query = click.argument("query")
_opt_json_out = click.option(
    "--json",
    "json_out",
    flag_value=True,
    default=False,
    help="Output raw JSON instead of formatted text",
)


@click.command
@_arg_query
@click.option(
    "--path",
    default=None,
    help="Folder filter for search/research (e.g. 'Shadow of the Weird Wizard')",
)
@_opt_json_out
@_handle_urlerror
def search(query: str, path: str | None, json_out: bool) -> None:
    """QUERY            Keyword/phrase search with short snippets"""
    q = query
    if path:
        q = f'{q} path:"{path}"'
    data = _search(q)
    if json_out:
        print(json.dumps(data, indent=2))
    else:
        print(f"Query: {data['query']}")
        print(f"Total: {data['count']}\n")
        for r in data["results"]:
            print(f"  [{r['id']}] {r['path']}  {r['size']}")
            if r.get("snippet"):
                print(f"       {r['snippet']}")
            print()


@click.command
@_arg_query
@click.option(
    "--path",
    default=None,
    help="Folder filter for search/research (e.g. 'Shadow of the Weird Wizard')",
)
@_opt_json_out
@click.option(
    "--passage-offset",
    type=int,
    default=0,
    help="Passage offset for pagination within a document",
)
@click.option("--limit", type=int, default=20, help="Max documents to return (default: 20)")
@click.option("--offset", type=int, default=0, help="Document offset for pagination")
@click.option(
    "--passages",
    type=int,
    default=10,
    help="Max passages per document (default: 10)",
)
@_handle_urlerror
def research(
    query: str,
    path: str | None,
    json_out: bool,
    passage_offset: int,
    limit: int,
    offset: int,
    passages: int,
) -> None:
    """Deep search with full passage extraction (use for research)"""
    q = query
    if path:
        q = f'{q} path:"{path}"'
    data = _research(
        q,
        limit=limit,
        offset=offset,
        passages=passages,
        passage_offset=passage_offset,
    )
    if json_out:
        print(json.dumps(data, indent=2))
    else:
        print_research(data)


@click.command
@click.option("--path")
@_opt_json_out
@_handle_urlerror
def folders(
    path: str | None,
    json_out: bool,
) -> None:
    """[PATH]           List subdirectories at PATH (default: root)"""
    data = _folders(path)
    if json_out:
        print(json.dumps(data, indent=2))
    else:
        print_folders(data)


@click.command
@click.option("--path", help="Path")
@_opt_json_out
@_handle_urlerror
def browse(
    path: str | None,
    json_out: bool,
) -> None:
    """[PATH]           List PDF files in PATH (default: root)"""
    data = _browse(path)
    if json_out:
        print(json.dumps(data, indent=2))
    else:
        print_browse(data)


@click.command
@_opt_json_out
@_handle_urlerror
def stats(json_out: bool) -> None:
    """Database statistics"""
    data = _stats()
    if json_out:
        print(json.dumps(data, indent=2))
    else:
        print_stats(data)
