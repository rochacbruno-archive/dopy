#!/usr/bin/env python
#-*- coding:utf-8 -*-

class Task(object):
    """To show the task
>>> print task
To show a field (available name, tag, status, reminder)
>>> task.name
To edit the task assign to a field
>>> task.name = "Other name"
To delete a task
>>> task.delete()
To exit
>>> quit()
######################################
"""
    def __init__(self, db, row):
        self.row = row
        self.db = db

    @property
    def name(self):
        return self.row.name

    @name.setter
    def name(self, value):
        self.row.update_record(name=value)
        self.db.commit()

    @property
    def tag(self):
        return self.row.tag

    @tag.setter
    def tag(self, value):
        self.row.update_record(tag=value)
        self.db.commit()

    @property
    def status(self):
        return self.row.status

    @status.setter
    def status(self, value):
        self.row.update_record(status=value)
        self.db.commit()

    @property
    def reminder(self):
        return self.row.reminder

    @reminder.setter
    def reminder(self, value):
        self.row.update_record(reminder=value)
        self.db.commit()

    @property
    def notes(self):
        return self.row.notes

    @notes.setter
    def notes(self, value):
        self.row.update_record(notes=value)
        self.db.commit()

    def delete(self):
        self.row.delete_record()
        self.db.commit()

    def __str__(self):
        return str(self.row)
