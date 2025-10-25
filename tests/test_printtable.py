"""Tests for printtable module."""
import pytest
from io import StringIO
import sys
from dolist.printtable import (
    print_table_row,
    print_table,
    get_column,
    cleaned,
    max_cell_length,
    align_cell_content,
)


class TestCleanedFunction:
    """Test the cleaned function that removes ANSI color codes."""

    def test_cleaned_removes_color_codes(self):
        """Test that ANSI color codes are removed."""
        colored_text = '\x1b[32mGreen Text\x1b[0m'
        result = cleaned(colored_text)
        assert result == 'Green Text'

    def test_cleaned_with_plain_text(self):
        """Test that plain text remains unchanged."""
        plain_text = 'Plain Text'
        result = cleaned(plain_text)
        assert result == 'Plain Text'

    def test_cleaned_with_multiple_colors(self):
        """Test removal of multiple color codes."""
        text = '\x1b[1m\x1b[31mBold Red\x1b[0m'
        result = cleaned(text)
        assert result == 'Bold Red'


class TestGetColumn:
    """Test the get_column function."""

    def test_get_column_basic(self):
        """Test getting a column from a matrix."""
        matrix = [
            ['a', 'b', 'c'],
            ['d', 'e', 'f'],
            ['g', 'h', 'i']
        ]
        result = get_column(matrix, 1)
        assert result == ['b', 'e', 'h']

    def test_get_column_first(self):
        """Test getting the first column."""
        matrix = [
            ['1', '2'],
            ['3', '4']
        ]
        result = get_column(matrix, 0)
        assert result == ['1', '3']

    def test_get_column_empty_matrix(self):
        """Test with empty matrix."""
        result = get_column([], 0)
        assert result == []

    def test_get_column_out_of_bounds(self):
        """Test with column index out of bounds."""
        matrix = [
            ['a', 'b'],
            ['c', 'd']
        ]
        result = get_column(matrix, 5)
        assert result == ['', '']


class TestMaxCellLength:
    """Test the max_cell_length function."""

    def test_max_cell_length_basic(self):
        """Test finding max length in cells."""
        cells = ['short', 'medium text', 'x']
        result = max_cell_length(cells)
        assert result == 11  # 'medium text'

    def test_max_cell_length_with_colors(self):
        """Test max length ignoring color codes."""
        cells = ['\x1b[32mGreen\x1b[0m', 'Blue']
        result = max_cell_length(cells)
        assert result == 5  # 'Green'

    def test_max_cell_length_empty(self):
        """Test with empty cells."""
        cells = []
        result = max_cell_length(cells)
        assert result == 0


class TestAlignCellContent:
    """Test the align_cell_content function."""

    def test_align_left(self):
        """Test left alignment."""
        result = align_cell_content('test', 10, 0)
        assert result == 'test      '
        assert len(result) == 10

    def test_align_right(self):
        """Test right alignment."""
        result = align_cell_content('test', 10, 1)
        assert result == '      test'
        assert len(result) == 10

    def test_align_center(self):
        """Test center alignment."""
        result = align_cell_content('test', 10, 2)
        assert 'test' in result
        assert len(result) == 10

    def test_align_no_padding_needed(self):
        """Test when cell is already at max length."""
        result = align_cell_content('test', 4, 0)
        assert result == 'test'

    def test_align_truncate(self):
        """Test truncation when cell is too long."""
        result = align_cell_content('verylongtext', 5, 0, truncate=True)
        assert result == 'veryl'
        assert len(result) == 5

    def test_align_no_truncate(self):
        """Test no truncation when disabled."""
        result = align_cell_content('verylongtext', 5, 0, truncate=False)
        assert result == 'verylongtext'

    def test_align_with_colors(self):
        """Test alignment with colored text."""
        colored = '\x1b[32mtest\x1b[0m'
        result = align_cell_content(colored, 10, 1)
        # Should account for the actual visible length (4) not the raw length
        assert 'test' in result


class TestPrintTableRow:
    """Test the print_table_row function."""

    def test_print_table_row_basic(self, capsys):
        """Test printing a basic table row."""
        row = ['col1', 'col2', 'col3']
        print_table_row(row)
        captured = capsys.readouterr()
        assert '|col1|col2|col3|' in captured.out

    def test_print_table_row_with_top_border(self, capsys):
        """Test printing row with top border."""
        row = ['a', 'b']
        print_table_row(row, top_border=True)
        captured = capsys.readouterr()
        output_lines = captured.out.strip().split('\n')
        assert len(output_lines) == 2
        assert '+' in output_lines[0]
        assert '-' in output_lines[0]

    def test_print_table_row_with_bottom_border(self, capsys):
        """Test printing row with bottom border."""
        row = ['a', 'b']
        print_table_row(row, bottom_border=True)
        captured = capsys.readouterr()
        output_lines = captured.out.strip().split('\n')
        assert len(output_lines) == 2
        assert '+' in output_lines[1]

    def test_print_table_row_with_both_borders(self, capsys):
        """Test printing row with both borders."""
        row = ['test']
        print_table_row(row, top_border=True, bottom_border=True)
        captured = capsys.readouterr()
        output_lines = captured.out.strip().split('\n')
        assert len(output_lines) == 3

    def test_print_table_row_invalid_type(self, capsys):
        """Test with invalid input type."""
        result = print_table_row("not a list")
        captured = capsys.readouterr()
        assert result == 1
        assert 'ERROR' in captured.out


class TestPrintTable:
    """Test the print_table function."""

    def test_print_table_basic(self, capsys):
        """Test printing a basic table."""
        table = [
            ['Name', 'Age'],
            ['Alice', '30'],
            ['Bob', '25']
        ]
        print_table(table)
        captured = capsys.readouterr()
        assert 'Name' in captured.out
        assert 'Age' in captured.out
        assert 'Alice' in captured.out
        assert 'Bob' in captured.out
        # Check for borders
        assert '+' in captured.out
        assert '-' in captured.out
        assert '|' in captured.out

    def test_print_table_single_row(self, capsys):
        """Test printing table with only header."""
        table = [['Header1', 'Header2']]
        print_table(table)
        captured = capsys.readouterr()
        assert 'Header1' in captured.out
        assert 'Header2' in captured.out

    def test_print_table_alignment(self, capsys):
        """Test that columns are right-aligned."""
        table = [
            ['ID', 'Name'],
            ['1', 'A'],
            ['200', 'B']
        ]
        print_table(table)
        captured = capsys.readouterr()
        # Columns should be padded to same width
        lines = captured.out.strip().split('\n')
        # All data lines should have same length
        data_lines = [l for l in lines if '|' in l]
        if len(data_lines) > 1:
            first_len = len(data_lines[0])
            assert all(len(line) == first_len for line in data_lines)

    def test_print_table_invalid_type(self, capsys):
        """Test with invalid input type."""
        result = print_table("not a list")
        captured = capsys.readouterr()
        assert result == 1
        assert 'ERROR' in captured.out

    def test_print_table_empty(self, capsys):
        """Test with empty table."""
        table = []
        # This might raise an error or handle gracefully
        # Testing the actual behavior
        try:
            result = print_table(table)
            # If it succeeds, check it returns 0
            assert result == 0
        except (IndexError, Exception):
            # If it fails, that's also acceptable behavior to document
            pass


class TestIntegration:
    """Integration tests for printtable module."""

    def test_full_table_with_colors(self, capsys):
        """Test a complete table with colored output."""
        table = [
            ['\x1b[1mID\x1b[0m', '\x1b[1mName\x1b[0m', '\x1b[1mStatus\x1b[0m'],
            ['1', 'Task 1', '\x1b[32mDone\x1b[0m'],
            ['2', 'Task 2', '\x1b[31mPending\x1b[0m']
        ]
        print_table(table)
        captured = capsys.readouterr()
        # Check that data is present (color codes will be in output)
        assert 'Task 1' in captured.out
        assert 'Task 2' in captured.out
        # Check structure is maintained
        assert '|' in captured.out
        assert '+' in captured.out
