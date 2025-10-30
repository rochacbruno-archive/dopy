#!/usr/bin/env python
# -*- coding:utf-8 -*-

from termcolor import colored


def HEAD(s):
    return colored(s, attrs=["bold"])


def FOOTER(s):
    return colored(s, "green", attrs=["bold"])


def REDBOLD(s):
    return colored(s, "red", attrs=["bold"])


def BOLD(s):
    return colored(s, attrs=["bold"])


def ID(s):
    return colored(s, None, "on_cyan", attrs=["bold"])


def NAME(s):
    return colored(s, "white")


def TAG(s):
    return colored(s, "yellow")


def NOTE(s, i):
    return colored(s, "yellow" if i % 2 == 0 else "blue", attrs=["bold"])


def STATUS(s):
    if s == "new":
        return colored(s, "white", "on_green", attrs=["bold"])
    elif s == "cancel":
        return colored(s, "white", "on_red", attrs=["bold"])
    elif s == "done":
        return colored(s, "white", "on_magenta", attrs=["bold"])
    elif s == "post":
        return colored(s, "grey", "on_white", attrs=["bold"])
    elif s == "in-progress":
        return colored(s, "white", "on_yellow", attrs=["bold"])
    else:
        return colored(s, "white", "on_cyan", attrs=["bold"])
