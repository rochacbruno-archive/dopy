#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""Dopy.

Usage:
  do.py
  do.py add <name> [<tag>] [<status>] [--reminder=<reminder>]
  do.py done <id>
  do.py ls [--all] [--tag=<tag>] [--status=<status>] [--search=<term>] [--date=<date>] [--month=<month>] [--day=<day>] [--year=<year>]
  do.py rm <id>
  do.py get <id>
  do.py export <path> [--format=<format>]
  do.py setpath <path>
  do.py use <db>
  do.py -h | --help
  do.py --version
  do.py --args

Options:
  -h --help      Show this screen.
  --version     Show version.
  --args          Show args.
"""
# NOTE
"""
  --speed=<kn>  Speed in knots [default: 10].
  --moored      Moored (anchored) mine.
  --drifting    Drifting mine.
"""
#########################################################################
#    IMPORTS AND CONSTANTS
#########################################################################
from docopt import docopt
from padnums import pprint_table
from printtable import print_table
from dal import DAL, Field
import os
import sys
import datetime
from taskmodel import Task

try:
    from win32com.shell import shellcon, shell
    homedir = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)
except ImportError:
    homedir = os.path.expanduser("~")

BASEDIR = os.path.join(homedir, '.dopy')

if not os.path.exists(BASEDIR):
    os.mkdir(BASEDIR)

CONFIGFILE = os.path.join(homedir, '.dopyrc')

if not os.path.exists(CONFIGFILE):
    default = dict(
        dbdir=BASEDIR,
        dburi="sqlite://dopy.db"
    )
    with open(CONFIGFILE, 'w') as conf:
        conf.write(str(default))

    CONFIG = default
else:
    CONFIG = eval(open(CONFIGFILE).read())

DBDIR = CONFIG['dbdir']
DBURI = CONFIG['dburi']

SHELLDOC = (
  "USAGE:\n"
  ">>> add('taskname', tag='', status='new|working|cancel|done|post', reminder='')\n"
  "tasklist is a list of all tasks\n"
  ">>> tasklist[0].name shows the name for task 1\n"
  "" + Task.__doc__
)
#########################################################################
#    MAIN PROGRAM
#########################################################################

def main(arguments):
    global db, tasks
    db, tasks = database()

    if not any(arguments.values()):
        shell()
    elif arguments['add']:
        print add(arguments)
    elif arguments['ls']:
        print ls(arguments)
    elif arguments['rm']:
        print rm(arguments)
    elif arguments['done']:
        print done(arguments)
    elif arguments['get']:
        print get(arguments)
    elif arguments['--args']:
        print arguments
    else:
        print arguments

def database():
    _db = DAL(DBURI, folder=DBDIR)
    tasks = _db.define_table("dopy_tasks",
        Field("name", "string"),
        Field("tag", "string"),
        Field("status", "string"),
        Field("reminder", "string"),
        Field("created_on", "datetime"),
        Field("deleted", "boolean", default=False),
    )
    return _db, tasks

def shell():
    global tasklist
    tasklist = []
    for task in db(tasks.deleted != True).select():
        tasklist.append(Task(db, task))
    import code
    code.interact(local=globals(), banner=SHELLDOC)

def add(arguments):
    #name, tag='default', status='new', reminder=None
    created_on = datetime.datetime.now()
    task = tasks.insert(name=arguments['<name>'],
                tag=arguments.get('<tag>', 'default') or 'default',
                status=arguments.get('<status>', 'new') or 'new',
                reminder=arguments.get('--reminder', None),
                created_on=created_on)
    db.commit()
    return "Task %d inserted" % task

def ls(arguments):
    # --all
    #tag=None, search=None, date=None,
    #month=None, day=None, year=None
    query = tasks.deleted != True
    query &= tasks.status != 'done' if not arguments['--all'] and not arguments['--status'] else tasks.id > 0
    if arguments['--tag']:
        query &= tasks.tag == arguments['--tag']
    if arguments['--status']:
        query &= tasks.status == arguments['--status']
    if arguments['--search']:
        query &= tasks.name.like('%%%s%%' % arguments['--search'].lower())


    rows = db(query).select()

    table = [['ID','Name','Tag','Status','Reminder','Created']]
    for row in rows:
        table.append([str(row.id), str(row.name), str(row.tag), str(row.status), str(row.reminder), str(row.created_on)])
    #pprint_table(sys.stdout, table)
    print_table(table)

    return "TOTAL:%s tasks" % len(rows) if rows else "NO TASKS FOUND\nUse --help to see the usage tips"

def rm(arguments):
    task = tasks[arguments['<id>']]
    if task:
        task.update_record(deleted=True)
        db.commit()
        return "%s deleted" % arguments['<id>']
    else:
        return "Task not found"

def done(arguments):
    task = tasks[arguments['<id>']]
    if task:
        task.update_record(status='done')
        db.commit()
        return "%s marked as done" % arguments['<id>']
    else:
        return "Task not found"

def get(arguments):
    row = tasks[arguments['<id>']]
    if row:
        task = Task(db, row)
        import code
        code.interact(local=dict(task=task), banner=Task.__doc__)
    else:
        return "Not found"

#########################################################################
#    STARTUP
#########################################################################

if __name__ == '__main__':
    arguments = docopt(__doc__, version='Dopy 0.1')
    main(arguments)
