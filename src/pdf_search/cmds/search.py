"""
Command-line full-text search over indexed PDFs.

Example: pdf-search search 'magic items' 20
"""

import sqlite3

import click

from pdf_search import config


def format_size(size_bytes: int | float | None) -> str:
    """Format bytes to human-readable size."""
    if size_bytes is None:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def search(query: str, limit: int = 10) -> None:
    """Run an FTS5 search and print results."""
    if not config.DB_PATH.exists():
        print(f"Error: database not found at {config.DB_PATH}")
        return

    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute(
        """
        SELECT
            d.id, d.filename, d.pdf_path, d.file_size,
            snippet(documents_fts, 1, '**', '**', '...', 50) as snippet,
            bm25(documents_fts, 500.0, 1.0) as score
        FROM documents_fts
        JOIN documents d ON d.id = documents_fts.rowid
        WHERE documents_fts MATCH ?
        ORDER BY score
        LIMIT ?
    """,
        (query, limit),
    )

    results = c.fetchall()
    conn.close()

    if not results:
        print(f"No results found for: {query}")
        return

    print(f"\nFound {len(results)} result(s) for: {query}\n")
    print("=" * 80)

    for i, row in enumerate(results, 1):
        print(f"\n{i}. {row['filename']}")
        print(f"   Path: {row['pdf_path']}")
        print(f"   Size: {format_size(row['file_size'])}")
        print(f"   Match: {row['snippet']}")
        print("-" * 80)


@click.command(help=__doc__)
@click.argument("query")
@click.option("--limit", type=int, default=10)
def command(query: str, limit: int) -> None:
    search(query, limit)
