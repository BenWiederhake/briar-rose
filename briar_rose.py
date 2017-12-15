#!/usr/bin/env python3

from os import environ
import sys
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
    return pids


LAST_PIDS = {}


def load_pids(config_path, err_fd):
    try:
        fd = open(config_path, 'r')
        # If you really need to stop a program of unknown pid
        # with \r or \n in its name, then you're fucked anyway.
        new_pids = parse_rules([line.rstrip('\r\n') for line in fd.readlines()], err_fd)
        fd.close()  # If this leaks, the program is about to die anyway.
        LAST_PIDS = new_pids
    except OSError as e:
        print('Cannot read config file: {}'.format(e), file=err_fd)

    return LAST_PIDS


def run_debug(config_path):
    pids = load_pids(config_path, sys.stdout)
    print('So I would stop {} pids now.'.format(len(pids)))


# def run_daemon(config_path, pidfile_path):


def default_pidfile_path():
    if 'XDG_RUNTIME_DIR' in environ:
        return '{}/briar_rose.pid'.format(environ['XDG_RUNTIME_DIR'])
    if 'USER' in environ:
        return '/tmp/{}-briar_rose.pid'.format(environ['USER'])
    return '/tmp/briar_rose.pid'


def run_args(args):
    config_path = None  # Must be replaced by dynamic default value
    #'briar-rose.config'
    pidfile_path = None  # Must be replaced by dynamic default value
    is_debug = False

    while len(args) > 0:
        if args[0] == '--debug':
            if is_debug:
                print('Duplicate option --debug!', file=sys.stderr)
                exit(1)
            is_debug = True
            args = args[1:]
        elif args[0] == '--pidfile':
            if pidfile_path is not None:
                print('Duplicate option --pidfile!', file=sys.stderr)
                exit(1)
            if len(args) < 2:
                print('Missing argument to --pidfile!', file=sys.stderr)
                exit(1)
            pidfile_path = args[1]
            args = args[2:]
        elif args[0] == '--config':
            if config_path is not None:
                print('Duplicate option --config!', file=sys.stderr)
                exit(1)
            if len(args) < 2:
                print('Missing argument to --config!', file=sys.stderr)
                exit(1)
            config_path = args[1]
            args = args[2:]
        # TODO: How about '--help'?
        else:
            print('Unknown option {}!'.format(args[0]), file=sys.stderr)
            exit(1)

    if config_path is None:
        config_path = 'briar_rose.config'

    if pidfile_path is None:
        pidfile_path = default_pidfile_path()

    if is_debug:
        print('Would use pidfile at {}'.format(pidfile_path))
        print('Loading configuration from {}'.format(config_path))
        run_debug(config_path)
    else:
        raise NotImplementedError()
        # run_daemon(config_path, pidfile_path)


if __name__ == '__main__':
    run_args(sys.argv[1:])
