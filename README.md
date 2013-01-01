dopy
====

     ____                     _
    |  _ \  ___   _ __  _   _| |
    | | | |/ _ \ | '_ \| | | | |
    | |_| | (_) || |_) | |_| |_|
    |____/ \___(_) .__/ \__, (_)
                 |_|    |___/


To Do list on Command Line Interface

Manage to-do list on a shell based simple interface and stores your to-do locally on a sqlite database

optionally use your Dropbox to store the database

![image](https://raw.github.com/rochacbruno/dopy/master/dopy.png)

Instalation
====
```pip install dopy```

or

```git clone https://github.com/rochacbruno/dopy```

```cd dopy```

```python setup.py install```

or

```git clone https://github.com/rochacbruno/dopy```

```chmod +x dopy/dopy/do.py```

```sudo ln -s path/to/dopy/dopy/do.py /bin/dopy```

**Maybe the pip option will not be working for a while**

Usage
====

    ____                     _
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


1. to enter in SHELL mode
```python do.py``` or simply ``dopy`` if installed

2. Add a new task
dopy <name> <tag> <status> <reminder>

```dopy add "Pay the telephone bill" personal new --reminder=today```

with default values for tag, status and reminder

```dopy add "Implement new features on my project"```

3. List taks

List all open tasks

```dopy ls```

    $ python do.py ls
    $ dopy ls
    +--+-----------------------------+--------+------+--------+-------------------+
    |ID|                         Name|     Tag|Status|Reminder|            Created|
    +--+-----------------------------+--------+------+--------+-------------------+
    | 3|           Pay telephone bill|personal|   new|   today|2012-12-31 08:03:15|
    | 4|Implement features on project| default|   new|    None|2012-12-31 08:03:41|
    +--+-----------------------------+--------+------+--------+-------------------+
    TOTAL:2 tasks

By tag

```dopy ls --tag=personal``

By name

```dopy ls --search=phone```

By status

```dopy ls --status=done```

All

```dopy ls --all```

3. Mark as done

dopy done <id>

```dopy done 2```

4. Remove a task

```dopy rm 2```

5. Get a task in shell mode for editing

```dopy get 3```

    $ dopy get 3
    To show the task
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

    >>> print task
    <Row {'status': 'new', 'name': 'Pay telephone bill', 'deleted': False, 'created_on': datetime.datetime(2012, 12, 31, 8, 3, 15), 'tag': 'personal', 'reminder': 'today', 'id': 3}>
    >>> task.status
    'new'
    >>> task.status = "working"
    >>> task.status
    'working'
    >>>


NOTES
====

Doing a ```dopy ls``` you can see the ```ID``` of the tasks, using this ```ID``` you can assign notes

1. Including a note

```dopy note 1 "This is the note for the task 1"```

The above command inserts the note and prints the TASK with notes.

    +--+-----+-------+------+--------+-----------+
    |ID| Name|    Tag|Status|Reminder|    Created|
    +--+-----+-------+------+--------+-----------+
    | 1|teste|default|   new|    None|01/01-02:14|
    +--+-----+-------+------+--------+-----------+
    NOTES:
    +------------------------------------+
    0 This is the note fot task 1
    +------------------------------------+
    1 notes

2. Consulting the notes

You can also show all notes for a task using the show command

```dopy show 1```

    +--+-----+-------+------+--------+-----------+
    |ID| Name|    Tag|Status|Reminder|    Created|
    +--+-----+-------+------+--------+-----------+
    | 1|teste|default|   new|    None|01/01-02:14|
    +--+-----+-------+------+--------+-----------+
    NOTES:
    +----------------------------------------+
    0 This is the note fot task 1
    1 This is another note for task 1
    +----------------------------------------+
    2 notes


3. Removing a note

Notes can be removed by its index number.

Example: To remove the latest note

```dopy note 1 --rm=-1```

where ```-1``` is the index for the last element in notes

To remove the first note

```dopy note 1 --rm=0```

Switching DBS
====

It is possible to use more than one database by switching using ```--use``` argument

```dopy add "Including on another db" --use=mynewdb

The above command will use a db called "mynewdb" (it will be created if not exists)

In the same way you have to specify the db for other operations

```dopy ls --all --use=mynewdb```  to list all tasks on the db

--------------
Note, you can also change the default db in .dopyrc file
-----------------


TODO
====

- Sync with google task
- Sync with remember the milk
- Generate HTML  and PDF reports on /tmp
