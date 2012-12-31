#!/usr/bin/env python
#-*- coding:utf-8 -*-

from termcolor import colored, cprint, COLORS, HIGHLIGHTS, ATTRIBUTES

HEAD = lambda s: colored(s, attrs=['bold'])
FOOTER = lambda s: colored(s, 'green', attrs=['bold'])
REDBOLD = lambda s: colored(s, 'red', attrs=['bold'])
BOLD = lambda s: colored(s, attrs=['bold'])
ID = lambda s: colored(s,None, 'on_cyan', attrs=['bold'])
NAME = lambda s: colored(s, 'white')
TAG = lambda s: colored(s, 'yellow')

def STATUS(s):
    if s == 'new':
        return colored(s, 'white', 'on_green', attrs=['bold'])
    elif s == 'cancel':
        return colored(s, 'white', 'on_red', attrs=['bold'])
    elif s == 'done':
        return colored(s, 'white', 'on_magenta', attrs=['bold'])
    elif s == 'post':
        return colored(s, 'grey', 'on_white', attrs=['bold'])
    elif s == 'working':
        return colored(s, 'white', 'on_yellow', attrs=['bold'])
    else:
        return colored(s, 'white', 'on_cyan', attrs=['bold'])
