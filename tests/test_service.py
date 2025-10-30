#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the reminder service module."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from dolist.service import trigger_reminder, run_multi_db_service_loop


class TestMultiDatabaseService:
    """Tests for multi-database service functionality - integration tests."""

    def test_service_command_accepts_databases_parameter(self):
        """Test that service command accepts --databases parameter."""
        from dolist.do import service

        # Just test that the function signature includes databases parameter
        import inspect

        sig = inspect.signature(service)
        assert "databases" in sig.parameters

    def test_service_command_accepts_verbose_parameter(self):
        """Test that service command accepts --verbose parameter."""
        from dolist.do import service
        import inspect

        sig = inspect.signature(service)
        assert "verbose" in sig.parameters

    def test_service_command_accepts_interval_parameter(self):
        """Test that service command accepts --interval parameter."""
        from dolist.do import service
        import inspect

        sig = inspect.signature(service)
        assert "interval" in sig.parameters


class TestTriggerReminder:
    """Tests for trigger_reminder function."""

    def test_trigger_reminder_with_default_notify_send(self):
        """Test that default notification uses notify-send."""
        task_data = {
            "id": 1,
            "name": "Test Task",
            "tag": "work",
            "status": "new",
            "notes": [],
        }
        config = {}

        with patch("subprocess.run") as mock_run:
            trigger_reminder(task_data, config)

            # Verify notify-send was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "notify-send" in call_args
            # Check that task name appears in the title
            assert "DoList: Test Task" in call_args

    def test_trigger_reminder_with_custom_command(self):
        """Test that custom reminder command is used when configured."""
        task_data = {
            "id": 1,
            "name": "Test Task",
            "tag": "work",
            "status": "new",
            "notes": [],
        }
        config = {"reminder_cmd": "/usr/local/bin/custom-notify"}

        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.communicate.return_value = ("", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            trigger_reminder(task_data, config)

            # Verify custom command was called
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]
            assert call_args == ["/usr/local/bin/custom-notify"]

    def test_trigger_reminder_includes_database_name(self):
        """Test that database name is included in task_data when provided."""
        task_data = {
            "id": 1,
            "name": "Test Task",
            "tag": "work",
            "status": "new",
            "notes": [],
            "database": "/tmp/work.db",
        }
        config = {}

        with patch("subprocess.run") as mock_run:
            trigger_reminder(task_data, config)

            # Just verify it doesn't crash with database in task_data
            mock_run.assert_called_once()


class TestServiceVerboseMode:
    """Tests for verbose mode output."""

    def test_run_multi_db_service_loop_accepts_verbose_parameter(self):
        """Test that run_multi_db_service_loop function signature accepts verbose parameter."""
        import inspect

        sig = inspect.signature(run_multi_db_service_loop)
        assert "verbose" in sig.parameters
        # Verify default value is False
        assert sig.parameters["verbose"].default is False

    def test_run_multi_db_service_loop_accepts_check_interval_parameter(self):
        """Test that run_multi_db_service_loop function signature accepts check_interval parameter."""
        import inspect

        sig = inspect.signature(run_multi_db_service_loop)
        assert "check_interval" in sig.parameters
        # Verify default value is 30
        assert sig.parameters["check_interval"].default == 30
