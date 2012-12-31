#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""Dopy.

Usage:
  do.py
  do.py add <name> [<tag>] [<status>] [--reminder=<reminder>]
  do.py ls [--tag=<tag>] [--status=<status>] [--search=<term>] [--date=<date>] [--month=<month>] [--day=<day>] [--year=<year>]
  do.py rm <id>
  do.py get <id>
  do.py set <id>
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
from dal import DAL, Field
import os
import sys
import datetime

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
    )
    return _db, tasks

def shell():
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

def ls(tag=None, search=None, date=None,
       month=None, day=None, year=None):
    query = tasks

    rows = db(query).select()
    return rows

def rm(did):
    pass

def get(did):
    pass

def set(did):
    pass

#########################################################################
#    STARTUP
#########################################################################

if __name__ == '__main__':
    arguments = docopt(__doc__, version='Dopy 0.1')
    main(arguments)
