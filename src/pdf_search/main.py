import click

from pdf_search import extractor, pdf_research, search


@click.group()
def main() -> None:
    pass


main.add_command(extractor.command, name="extractor")
main.add_command(pdf_research.command, name="pdf_research")
main.add_command(search.command, name="search")


if __name__ == "__main__":
    main()
