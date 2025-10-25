#!/usr/bin/env python
# -*- coding: utf-8 -*-
#Copyright (c) 2011, Reiner Rottmann
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification,
#are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#    * Neither the name of the  nor the names of its contributors
#      may be used to endorse or promote products derived from this software
#      without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
#FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
#DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
Print table module. Draws ASCII boxes to pretty print lists.
"""
import math

__author__ = "rottmrei"
__date__ = "$28.01.2011 19:43:01$"

def print_table_row(row, top_border=False, bottom_border=False):
    """Prints columns of a single table row with ascii cell seperator and
    an optional top and/or bottom border line.
    """
    if not isinstance(row, list):
        print("ERROR: A line has to be of the type list.")
        return 1
    cc = "+"
    """corner char"""
    hc = "-"
    """horizontal char"""
    vc = "|"
    """vertical char"""
    # create seperator line and output row
    sep = ""
    """seperator line"""
    out = ""
    """output row"""
    sep = cc
    out = vc
    c = 0
    for col in row:

        lencol = len(cleaned(col)) if any([top_border, bottom_border]) else len(col)

        sep = sep + hc * lencol + cc

        out = out + row[c] + vc
        c += 1
    # now print table row
    if top_border:
        print(sep)
    print(out)
    if bottom_border:
        print(sep)
    return 0

def print_table(rows):
    """Prints the rows of a table by calling print_table_row function.
    The first row is assumed to be the heading line. The heading line
    and the last line of the table are printed with seperator lines.
    """
    if not isinstance(rows, list):
        print("ERROR: Table rows have to be of the type list.")
        return 1
    r = 0
    """row counter"""
    # space-pad the cells and right align the contents
    c = 0
    """column number"""
    while c < len(rows[0]):
        col = get_column(rows, c)
        cell_width = max_cell_length(col)
        for row in rows:
            if row[c]:
                row[c] = align_cell_content(row[c], cell_width, 1, False)
        c+=1
    for row in rows:
        if r == 0 and len(rows) > 0:
            print_table_row(row, True, True)
        else:
            if r == len(rows)-1:
                print_table_row(row, False, True)
            else:
                print_table_row(row)
        r += 1
    return 0

def get_column(matrix=[], column=0):
    """Returns one column from the given matrix."""
    col = []
    for row in matrix:
        cell=""
        if len(row) >= column:
            cell = row[column]
        col.append(cell)
    return col


def cleaned(c):
    colors = [
     '\x1b[0m',
     '\x1b[33m',
     '\x1b[32m',
     '\x1b[31m',
     '\x1b[30m',
     '\x1b[37m',
     '\x1b[36m',
     '\x1b[35m',
     '\x1b[34m',
     '\x1b[8m',
     '\x1b[5m',
     '\x1b[4m',
     '\x1b[7m',
     '\x1b[1m',
     '\x1b[0m',
     '\x1b[2m',
     '\x1b[42m',
     '\x1b[43m',
     '\x1b[40m',
     '\x1b[41m',
     '\x1b[46m',
     '\x1b[0m',
     '\x1b[44m',
     '\x1b[47m',
     '\x1b[45m']
    for color in colors:
        c = c.replace(color, '')

    return c

def max_cell_length(cells):
    """Returns the length of the longest cell from all the given cells."""
    max_len=0
    for c in cells:
        cur_len=len( cleaned(c) )
        if cur_len > max_len:
            max_len = cur_len
    return max_len

def align_cell_content(cell, max_cell_length=0, alignment=0, truncate=True):
    """Returns the given cell padded with spaces to the max_cell_length.
    You may choose the alignment of the cell contents:

    0 : align left
    1 : align right
    2 : center

    In case the cell contents is longer than max_cell_length, the contents
    gets truncated. You may choose to not truncate any cell data.
    """

    if max_cell_length == 0:
        return cell
    cur_cell_length=len( cleaned(cell) )
    padding=max_cell_length-cur_cell_length
    if padding == 0: return cell
    if padding < 0:
        if truncate:
            return cell[:max_cell_length]
        else:
            return cell
    else:
        if alignment == 0:
            # align left
            return cell + " " * padding
        if alignment == 1:
            # align right:
            return " " * padding + cell
        else:
            # center
            pl = int(math.ceil(padding / 2.0))
            pr = padding -pl
            return " " * pl + cell + " " * pr

def test_print_table():
    """Test function for print_table().

    Produces the following output:

    +----+----+---------------+
    |some|test|           data|
    +----+----+---------------+
    |   1|   2|              3|
    |   2|   4|              6|
    |   3|   8|             12|
    |   4|  16|             24|
    |   5|  32|look here--->48|
    +----+----+---------------+

    """
    test_table = []
    test_table.append(["some", "test", "data"])
    test_table.append(["1", "2", "3"])
    test_table.append(["2", "4", "6"])
    test_table.append(["3", "8", "12"])
    test_table.append(["4", "16", "24"])
    test_table.append(["5", "32", "look here--->48"])
    print_table(test_table)

if __name__ == "__main__":
    test_print_table()
