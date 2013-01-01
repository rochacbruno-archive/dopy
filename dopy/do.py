#!/usr/bin/env python
#-*- coding:utf-8 -*-

""" ____                     _
|  _ \  ___   _ __  _   _| |
| | | |/ _ \ | '_ \| | | | |
| |_| | (_) || |_) | |_| |_|
|____/ \___(_) .__/ \__, (_)
             |_|    |___/


Usage:
  do.py [--use=<db>] [--args]
  do.py add <name> [<tag>] [<status>] [--reminder=<reminder>] [--use=<db>] [--args]
  do.py done <id> [--use=<db>] [--args]
  do.py ls [--all] [--tag=<tag>] [--status=<status>] [--search=<term>] [--date=<date>] [--month=<month>] [--day=<day>] [--year=<year>] [--use=<db>] [--args]
  do.py rm <id> [--use=<db>] [--args]
  do.py get <id> [--use=<db>] [--args]
  do.py note <id> [--use=<db>] [--rm=<noteindex>] [--args]
  do.py show <id> [--use=<db>] [--args]
  do.py note <id> <note> [--use=<db>] [--args]
  do.py export <path> [--format=<format>] [--use=<db>] [--args]
  do.py setpath <path> [--args]
  do.py use <db> [--args]
  do.py -h | --help [--args]
  do.py --version [--args]
  do.py --args

Options:
  -h --help      Show this screen.
  --version     Show version.
  --args          Show args.
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
#from termcolor import colored, cprint
from colors import *
from pprint import pprint

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

def main(arguments, DBURI=DBURI):
    if arguments['--args']:
        print arguments
    if arguments['--use']:
        DBURI = DBURI.replace('dopy', arguments['--use'])

    global db, tasks
    db, tasks = database(DBURI)

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
    elif arguments['note'] or arguments['show']:
        print note(arguments)
    else:
        print arguments

def database(DBURI):
    _db = DAL(DBURI, folder=DBDIR)
    tasks = _db.define_table("dopy_tasks",
        Field("name", "string"),
        Field("tag", "string"),
        Field("status", "string"),
        Field("reminder", "string"),
        Field("notes", "list:string"),
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

    headers = [HEAD(s) for s in ['ID','Name','Tag','Status','Reminder','Notes','Created']]
    #if arguments['--n']:
        #headers.append('Notes')

    table = [headers]
    for row in rows:
        fields = [ID(str(row.id)),
                 NAME(str(row.name)),
                 TAG(str(row.tag)),
                 STATUS(str(row.status)),
                 str(row.reminder),
                 str(len(row.notes) if row.notes else 0),
                 str(row.created_on.strftime("%d/%m-%H:%M"))]

        #if arguments['--n']:
            #fields.append(str( '\n'.join(row.notes) ))

        table.append(fields)

    #pprint_table(sys.stdout, table)
    print_table(table)

    return FOOTER("TOTAL:%s tasks" % len(rows) if rows else "NO TASKS FOUND\nUse --help to see the usage tips")

def rm(arguments):
    task = tasks[arguments['<id>']]
    if task:
        task.update_record(deleted=True)
        db.commit()
        return "%s deleted" % arguments['<id>']
    else:
        return "Task not found"

def note(arguments):
    task = tasks[arguments['<id>']]
    if task:
        task.notes = task.notes or []
        if arguments['<note>']:
            #actualnotes = task.notes or []
            task.update_record(notes=task.notes + [arguments['<note>']])
            db.commit()
        if arguments['--rm']:
            try:
                del task.notes[int(arguments['--rm'])]
                task.update_record(notes=task.notes)
            except:
                print REDBOLD("Note not found")
            else:
                db.commit()

        lenmax = max([len(note) for note in task.notes ]) if task.notes else 20
        out = "+----" + "-" * lenmax +  "-----+"

        headers = [HEAD(s) for s in ['ID','Name','Tag','Status','Reminder','Created']]
        fields = [ID(str(task.id)),
                 NAME(str(task.name)),
                 TAG(str(task.tag)),
                 STATUS(str(task.status)),
                 str(task.reminder),
                 str(task.created_on.strftime("%d/%m-%H:%M"))]
        print_table([headers, fields])

        if task.notes:
            print HEAD("NOTES:")
            print out
            cprint("\n".join( [ ID(str(i)) + " " + NOTE(note, i) for i, note in enumerate(task.notes)] ), 'blue', attrs=['bold'])
            out +=    FOOTER("\n%s notes" % len(task.notes))
            return out
        else:
            return ""
    else:
        return FOOTER("Task not found")

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
    arguments = docopt(__doc__, version='Dopy 0.2')
    main(arguments)
