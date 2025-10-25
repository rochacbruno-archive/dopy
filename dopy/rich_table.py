#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Rich table rendering for task display."""

from rich.console import Console
from rich.table import Table
from rich import box
from rich.text import Text
import re


def strip_ansi(text):
    """Remove ANSI escape codes from text."""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', str(text))


def print_table(rows, title=None):
    """
    Print a table using Rich with clean formatting.

    Args:
        rows: List of lists, where first row is headers
        title: Optional title for the table
    """
    if not rows or len(rows) < 1:
        return

    console = Console()

    table = Table(
        title=title,
        box=box.SIMPLE,
        show_header=True,
        header_style="bold cyan",
        show_lines=False,
        pad_edge=True,
    )

    # Strip ANSI codes from headers and add columns
    headers = rows[0]
    for i, header in enumerate(headers):
        clean_header = strip_ansi(header)
        # Only ID column should be strictly no_wrap to prevent weird formatting
        # Let other columns wrap naturally
        if clean_header == 'ID':
            table.add_column(clean_header, style='white', justify='right', no_wrap=True)
        else:
            table.add_column(clean_header, style='white')

    # Add data rows, stripping ANSI codes
    for row in rows[1:]:
        # Strip ANSI codes and convert to strings
        clean_row = [strip_ansi(item) if item is not None else "" for item in row]
        table.add_row(*clean_row)

    console.print(table)
