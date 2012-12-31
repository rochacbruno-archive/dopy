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

TODO
====

- Sync with google task
- Sync with remember the milk
- Generate HTML  and PDF reports on /tmp
