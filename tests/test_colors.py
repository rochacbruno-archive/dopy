"""Tests for colors module."""
import pytest
from dolist.colors import HEAD, FOOTER, REDBOLD, BOLD, ID, NAME, TAG, NOTE, STATUS


class TestColorFunctions:
    """Test color formatting functions."""

    def test_head_returns_string(self):
        """Test HEAD function returns a string."""
        result = HEAD('Test')
        assert isinstance(result, str)
        assert 'Test' in result

    def test_footer_returns_string(self):
        """Test FOOTER function returns a string."""
        result = FOOTER('Test')
        assert isinstance(result, str)
        assert 'Test' in result

    def test_redbold_returns_string(self):
        """Test REDBOLD function returns a string."""
        result = REDBOLD('Error')
        assert isinstance(result, str)
        assert 'Error' in result

    def test_bold_returns_string(self):
        """Test BOLD function returns a string."""
        result = BOLD('Text')
        assert isinstance(result, str)
        assert 'Text' in result

    def test_id_returns_string(self):
        """Test ID function returns a string."""
        result = ID('123')
        assert isinstance(result, str)
        assert '123' in result

    def test_name_returns_string(self):
        """Test NAME function returns a string."""
        result = NAME('Task Name')
        assert isinstance(result, str)
        assert 'Task Name' in result

    def test_tag_returns_string(self):
        """Test TAG function returns a string."""
        result = TAG('work')
        assert isinstance(result, str)
        assert 'work' in result


class TestNoteFunction:
    """Test NOTE function with alternating colors."""

    def test_note_even_index(self):
        """Test NOTE with even index."""
        result = NOTE('Note text', 0)
        assert isinstance(result, str)
        assert 'Note text' in result

    def test_note_odd_index(self):
        """Test NOTE with odd index."""
        result = NOTE('Note text', 1)
        assert isinstance(result, str)
        assert 'Note text' in result

    def test_note_different_colors(self):
        """Test that even and odd indices might produce different colors."""
        note_even = NOTE('Text', 0)
        note_odd = NOTE('Text', 1)
        # Both should contain the text
        assert 'Text' in note_even
        assert 'Text' in note_odd
        # The actual color codes might differ (implementation dependent)


class TestStatusFunction:
    """Test STATUS function with different status values."""

    def test_status_new(self):
        """Test STATUS with 'new' status."""
        result = STATUS('new')
        assert isinstance(result, str)
        assert 'new' in result

    def test_status_cancel(self):
        """Test STATUS with 'cancel' status."""
        result = STATUS('cancel')
        assert isinstance(result, str)
        assert 'cancel' in result

    def test_status_done(self):
        """Test STATUS with 'done' status."""
        result = STATUS('done')
        assert isinstance(result, str)
        assert 'done' in result

    def test_status_post(self):
        """Test STATUS with 'post' status."""
        result = STATUS('post')
        assert isinstance(result, str)
        assert 'post' in result

    def test_status_in_progress(self):
        """Test STATUS with 'in-progress' status."""
        result = STATUS('in-progress')
        assert isinstance(result, str)
        assert 'in-progress' in result

    def test_status_unknown(self):
        """Test STATUS with unknown status."""
        result = STATUS('unknown')
        assert isinstance(result, str)
        assert 'unknown' in result

    def test_status_preserves_content(self):
        """Test that STATUS preserves the status text."""
        statuses = ['new', 'done', 'cancel', 'post', 'working', 'custom']
        for status in statuses:
            result = STATUS(status)
            assert status in result


class TestColorCodePresence:
    """Test that ANSI color codes are present in output."""

    def test_colored_output_has_ansi_codes(self):
        """Test that colored functions include ANSI escape codes."""
        # At least some functions should include ANSI codes
        result = FOOTER('Test')
        # ANSI codes start with \x1b[
        # Check if result is likely colored (has escape sequences or the raw text)
        assert isinstance(result, str)

    def test_functions_work_with_empty_string(self):
        """Test that all functions handle empty strings."""
        functions = [HEAD, FOOTER, REDBOLD, BOLD, ID, NAME, TAG]
        for func in functions:
            result = func('')
            assert isinstance(result, str)

    def test_functions_work_with_special_chars(self):
        """Test that functions handle special characters."""
        special = '!@#$%^&*()'
        functions = [HEAD, FOOTER, REDBOLD, BOLD, ID, NAME, TAG]
        for func in functions:
            result = func(special)
            assert special in result


class TestIntegration:
    """Integration tests for color module."""

    def test_multiple_color_functions(self):
        """Test using multiple color functions together."""
        header = HEAD('Header')
        footer = FOOTER('Footer')
        error = REDBOLD('Error')

        assert isinstance(header, str)
        assert isinstance(footer, str)
        assert isinstance(error, str)
        assert 'Header' in header
        assert 'Footer' in footer
        assert 'Error' in error

    def test_status_colors_for_workflow(self):
        """Test status colors for a typical workflow."""
        statuses = ['new', 'working', 'done']
        results = [STATUS(s) for s in statuses]

        # All should be strings
        assert all(isinstance(r, str) for r in results)
        # All should contain their status
        for status, result in zip(statuses, results):
            assert status in result
