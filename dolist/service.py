#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Reminder service for DoList.

This module provides the background service that monitors and triggers reminders.
"""

import time
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from rich.console import Console

console = Console()


def get_systemd_service_template(python_path: str, dolist_path: str, user: str) -> str:
    """Generate systemd service template.

    Args:
        python_path: Path to Python executable
        dolist_path: Path to dolist command
        user: Username to run service as

    Returns:
        Systemd service file content
    """
    return f"""[Unit]
Description=DoList Reminder Service
After=network.target

[Service]
Type=simple
User={user}
ExecStart={python_path} -m dolist service
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""


def install_systemd_service() -> bool:
    """Install and enable systemd service.

    Returns:
        True if successful, False otherwise
    """
    import os
    import shutil

    # Get paths
    python_path = sys.executable
    dolist_path = shutil.which("dolist") or sys.argv[0]
    user = os.environ.get("USER", "root")

    # Generate service file
    service_content = get_systemd_service_template(python_path, dolist_path, user)

    # Determine service file location
    if user == "root":
        service_path = Path("/etc/systemd/system/dolist-reminder.service")
    else:
        # User service
        service_dir = Path.home() / ".config" / "systemd" / "user"
        service_dir.mkdir(parents=True, exist_ok=True)
        service_path = service_dir / "dolist-reminder.service"

    try:
        # Write service file
        console.print(f"[cyan]Writing service file to: {service_path}[/cyan]")
        service_path.write_text(service_content)

        # Reload systemd
        if user == "root":
            subprocess.run(["systemctl", "daemon-reload"], check=True)
            subprocess.run(
                ["systemctl", "enable", "dolist-reminder.service"], check=True
            )
            subprocess.run(
                ["systemctl", "start", "dolist-reminder.service"], check=True
            )
            console.print(
                "[green]✓ Systemd service installed and started (system-wide)[/green]"
            )
            console.print(
                "[yellow]Run: sudo systemctl status dolist-reminder.service[/yellow]"
            )
        else:
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
            subprocess.run(
                ["systemctl", "--user", "enable", "dolist-reminder.service"], check=True
            )
            subprocess.run(
                ["systemctl", "--user", "start", "dolist-reminder.service"], check=True
            )
            console.print(
                "[green]✓ Systemd service installed and started (user service)[/green]"
            )
            console.print(
                "[yellow]Run: systemctl --user status dolist-reminder.service[/yellow]"
            )

        return True

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error installing systemd service: {e}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False


def trigger_reminder(task_data: dict, config: dict) -> None:
    """Trigger a reminder for a task.

    Args:
        task_data: Task data as dictionary
        config: Configuration dictionary
    """
    # Check if custom reminder_cmd is configured
    reminder_cmd = config.get("reminder_cmd")

    if reminder_cmd:
        # Use custom command
        try:
            console.print(f"[cyan]Triggering custom reminder: {reminder_cmd}[/cyan]")
            process = subprocess.Popen(
                [reminder_cmd],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate(input=json.dumps(task_data))

            if process.returncode != 0:
                console.print(f"[red]Custom reminder command failed: {stderr}[/red]")
            else:
                console.print("[green]✓ Custom reminder triggered successfully[/green]")

        except Exception as e:
            console.print(f"[red]Error running custom reminder command: {e}[/red]")
    else:
        # Default: use notify-send
        try:
            title = f"DoList: {task_data.get('name', 'Task Reminder')}"
            body = f"Tag: {task_data.get('tag', 'N/A')}\nStatus: {task_data.get('status', 'N/A')}"

            if task_data.get("notes"):
                notes_count = len(task_data["notes"])
                body += f"\n{notes_count} note(s) attached"

            console.print(f"[cyan]Sending notification: {title}[/cyan]")

            subprocess.run(
                ["notify-send", title, body, "-u", "normal", "-t", "10000"], check=True
            )

            console.print(
                f"[green]✓ Notification sent for task #{task_data.get('id')}[/green]"
            )

        except FileNotFoundError:
            console.print(
                "[red]notify-send not found. Please install libnotify or set a custom reminder_cmd[/red]"
            )
        except Exception as e:
            console.print(f"[red]Error sending notification: {e}[/red]")


def run_service_loop(db, tasks_table, config: dict, check_interval: int = 30) -> None:
    """Run the reminder service loop.

    Args:
        db: Database connection
        tasks_table: Tasks table object
        config: Configuration dictionary
        check_interval: Seconds between checks (default: 30)
    """
    from .reminder_parser import parse_reminder

    console.print("[bold green]DoList Reminder Service Started[/bold green]")
    console.print(f"[cyan]Checking for reminders every {check_interval} seconds[/cyan]")
    console.print("[yellow]Press Ctrl+C to stop[/yellow]\n")

    try:
        while True:
            now = datetime.now()

            # Ensure we have a fresh connection by committing any pending transactions
            # This forces SQLite to refresh its cache
            try:
                db.commit()
            except Exception:
                pass  # Ignore if there's nothing to commit

            # Query for tasks with reminders that are due
            # Exclude done/cancelled tasks
            query = (
                (not tasks_table.deleted)
                & (tasks_table.reminder_timestamp is not None)
                & (tasks_table.reminder_timestamp <= now)
                & ~(tasks_table.status.belongs(["done", "cancel"]))
            )

            due_tasks = db(query).select()

            if due_tasks:
                console.print(
                    f"[yellow]Found {len(due_tasks)} due reminder(s)[/yellow]"
                )

                for task_row in due_tasks:
                    console.print(
                        f"[cyan]Processing reminder for task #{task_row.id}: {task_row.name}[/cyan]"
                    )

                    # Prepare task data
                    task_data = {
                        "id": task_row.id,
                        "name": task_row.name,
                        "tag": task_row.tag,
                        "status": task_row.status,
                        "reminder": task_row.reminder,
                        "notes": task_row.notes or [],
                        "created_on": (
                            task_row.created_on.isoformat()
                            if task_row.created_on
                            else None
                        ),
                    }

                    # Trigger reminder
                    trigger_reminder(task_data, config)

                    # Check if this is a recurring reminder
                    reminder_repeat = getattr(task_row, "reminder_repeat", None)

                    if reminder_repeat:
                        # Reschedule the reminder
                        console.print(
                            f"[cyan]Rescheduling recurring reminder: {reminder_repeat}[/cyan]"
                        )
                        next_dt, error, _ = parse_reminder(reminder_repeat)

                        if next_dt and not error:
                            task_row.update_record(reminder_timestamp=next_dt)
                            db.commit()
                            console.print(
                                f"[green]✓ Reminder rescheduled for {next_dt.strftime('%Y-%m-%d %H:%M:%S')}[/green]\n"
                            )
                        else:
                            console.print(f"[red]Failed to reschedule: {error}[/red]")
                            # Clear the reminder if parsing fails
                            task_row.update_record(reminder_timestamp=None)
                            db.commit()
                            console.print(
                                "[yellow]Reminder cleared due to parsing error[/yellow]\n"
                            )
                    else:
                        # One-time reminder: clear it
                        task_row.update_record(reminder_timestamp=None)
                        db.commit()
                        console.print(
                            f"[green]✓ Reminder cleared for task #{task_row.id}[/green]\n"
                        )

            # Wait before next check
            time.sleep(check_interval)

    except KeyboardInterrupt:
        console.print("\n[yellow]Service stopped by user[/yellow]")
    except Exception as e:
        # Use repr to avoid Rich markup interpretation in error messages
        error_msg = repr(str(e))
        console.print(f"\n[red]Service error: {error_msg}[/red]")
        raise


def run_multi_db_service_loop(
    db_list: list, config: dict, check_interval: int = 30, verbose: bool = False
) -> None:
    """Run the reminder service loop for multiple databases.

    Args:
        db_list: List of tuples (db, tasks_table, db_name)
        config: Configuration dictionary
        check_interval: Seconds between checks (default: 30)
        verbose: Enable verbose logging
    """
    from .reminder_parser import parse_reminder

    console.print(
        "[bold green]DoList Multi-Database Reminder Service Started[/bold green]"
    )
    console.print(f"[cyan]Monitoring {len(db_list)} database(s)[/cyan]")
    for _, _, db_name in db_list:
        console.print(f"  - {db_name}")
    console.print(f"[cyan]Checking for reminders every {check_interval} seconds[/cyan]")
    console.print("[yellow]Press Ctrl+C to stop[/yellow]\n")

    try:
        cycle = 0
        while True:
            cycle += 1
            now = datetime.now()
            total_due_tasks = 0

            if verbose:
                console.print(
                    f"\n[dim]>>> Cycle {cycle} at {now.strftime('%H:%M:%S')}[/dim]"
                )

            # Loop through all databases
            for db, tasks_table, db_name in db_list:
                # Ensure we have a fresh connection by committing any pending transactions
                # This forces SQLite to refresh its cache
                try:
                    db.commit()
                except Exception:
                    pass  # Ignore if there's nothing to commit

                # Query for all tasks to count them in verbose mode
                if verbose:
                    all_tasks_query = not tasks_table.deleted
                    all_tasks = db(all_tasks_query).select()
                    # Use parentheses instead of brackets to avoid Rich markup errors
                    console.print(
                        f"[dim]  ({db_name}) Total tasks: {len(all_tasks)}[/dim]"
                    )

                # Query for tasks with reminders that are due
                # Exclude done/cancelled tasks
                query = (
                    (not tasks_table.deleted)
                    & (tasks_table.reminder_timestamp is not None)
                    & (tasks_table.reminder_timestamp <= now)
                    & ~(tasks_table.status.belongs(["done", "cancel"]))
                )

                due_tasks = db(query).select()

                if verbose:
                    # Count tasks with reminders (even if not due yet)
                    reminder_query = (
                        (not tasks_table.deleted)
                        & (tasks_table.reminder_timestamp is not None)
                        & ~(tasks_table.status.belongs(["done", "cancel"]))
                    )
                    tasks_with_reminders = db(reminder_query).select()
                    # Use parentheses instead of brackets to avoid Rich markup errors
                    console.print(
                        f"[dim]  ({db_name}) Tasks with reminders: {len(tasks_with_reminders)}[/dim]"
                    )
                    console.print(
                        f"[dim]  ({db_name}) Due reminders: {len(due_tasks)}[/dim]"
                    )

                if due_tasks:
                    total_due_tasks += len(due_tasks)
                    console.print(
                        f"[yellow]Database '({db_name})': Found {len(due_tasks)} due reminder(s)[/yellow]"
                    )

                    for task_row in due_tasks:
                        console.print(
                            f"[cyan]  ({db_name}) Processing task #{task_row.id}: {task_row.name}[/cyan]"
                        )

                        # Prepare task data
                        task_data = {
                            "id": task_row.id,
                            "name": task_row.name,
                            "tag": task_row.tag,
                            "status": task_row.status,
                            "reminder": task_row.reminder,
                            "notes": task_row.notes or [],
                            "created_on": (
                                task_row.created_on.isoformat()
                                if task_row.created_on
                                else None
                            ),
                            "database": db_name,  # Include database name in notification
                        }

                        # Trigger reminder
                        trigger_reminder(task_data, config)

                        # Check if this is a recurring reminder
                        reminder_repeat = getattr(task_row, "reminder_repeat", None)

                        if reminder_repeat:
                            # Reschedule the reminder
                            console.print(
                                f"[cyan]  Rescheduling recurring reminder: {reminder_repeat}[/cyan]"
                            )
                            next_dt, error, _ = parse_reminder(reminder_repeat)

                            if next_dt and not error:
                                task_row.update_record(reminder_timestamp=next_dt)
                                db.commit()
                                console.print(
                                    f"[green]  ✓ Reminder rescheduled for {next_dt.strftime('%Y-%m-%d %H:%M:%S')}[/green]\n"
                                )
                            else:
                                console.print(
                                    f"[red]  Failed to reschedule: {error}[/red]"
                                )
                                # Clear the reminder if parsing fails
                                task_row.update_record(reminder_timestamp=None)
                                db.commit()
                                console.print(
                                    "[yellow]  Reminder cleared due to parsing error[/yellow]\n"
                                )
                        else:
                            # One-time reminder: clear it
                            task_row.update_record(reminder_timestamp=None)
                            db.commit()
                            console.print(
                                f"[green]  ✓ Reminder cleared for task #{task_row.id}[/green]\n"
                            )

            if verbose:
                if total_due_tasks == 0:
                    console.print("[dim]  No due reminders this cycle[/dim]")

            # Wait before next check
            if verbose:
                console.print(
                    f"[dim]Waiting {check_interval} seconds until next check...[/dim]"
                )
            time.sleep(check_interval)

    except KeyboardInterrupt:
        console.print("\n[yellow]Service stopped by user[/yellow]")
    except Exception as e:
        # Use repr to avoid Rich markup interpretation in error messages
        error_msg = repr(str(e))
        console.print(f"\n[red]Service error: {error_msg}[/red]")
        raise
