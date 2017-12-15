#!/usr/bin/env python3

from os import environ
from sys import stdout, stderr
import subprocess
#from pid import Pidfile


RULE_NOOP = (True, set())


def pidof(pname):
    # Thanks to https://stackoverflow.com/a/35938503/3070326
    try:
        return set(map(int, subprocess.check_output(["pidof", pname]).split()))
    except subprocess.CalledProcessError:
        return set()


def parse_rule(rule, err_fd, is_exception=False):
    if rule == '':
        if is_exception:
            print('WARNING: Empty exception rule!', file=err_fd)
        return RULE_NOOP

    if rule[0] == '#':
        if is_exception:
            print('WARNING: Comment exception!', file=err_fd)
        return RULE_NOOP
    if rule[0] in '§$&^?.+-*@':
        print('WARNING: Reserved character {}.  Might be the config file of a future version!'.format(rule[0]), file=err_fd)
        return RULE_NOOP
    if rule[0] == '=':
        try:
            return (not is_exception, {int(rule[1:])})
        except ValueError:
            print('WARNING: Could not parse PID "{}"!'.format(rule[1:]), file=err_fd)
            return RULE_NOOP
    if rule[0] == '!':
        if is_exception:
            print('WARNING: Double-exceptions are a syntax error!'.format(rule[1:]), file=err_fd)
            return RULE_NOOP
        return parse_rule(rule[1:], err_fd, is_exception=True)
    if rule[0] == '"':
        rule = rule[1:]
        if rule[-1] == '"':
            print('WARNING: Rule starts and ends with quotation mark.  It is possible this line has the wrong syntax!'.format(rule[1:]), file=err_fd)
    return (not is_exception, pidof(rule))


def parse_rules(rules, err_fd):
    pids = set()
    print('Starting with empty PID set.', file=err_fd)
    for rule in rules:
        print('Considering rule "{}" …'.format(rule), file=err_fd)
        sub_sign, sub_set = parse_rule(rule, err_fd)
        if sub_set == set():
            continue
        len_before = len(pids)
        if sub_sign:
            pids.update(sub_set)
        else:
            pids.difference_update(sub_set)
        len_after = len(pids)
        if len_after > len_before:
            print('{} PIDs added.  PID set is now {}'.format(len_after - len_before, sorted(pids)), file=err_fd)
        elif len_after < len_before:
            print('{} PIDs removed.  PID set is now {}'.format(len_before - len_after, sorted(pids)), file=err_fd)
        else:
            print('PID set unchanged', file=err_fd)
    print('Parsing completed.', file=err_fd)
    # return pids


if __name__ == '__main__':
    print('Nothing implemented yet!')
    exit(1)
