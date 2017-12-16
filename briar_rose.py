#!/usr/bin/env python3

import os
from os.path import basename, dirname
import sys
import subprocess
from pid import PidFile
import re
import atexit
import signal
from datetime import datetime


# ===== CONFIGURATION =====
# Just in case you disagree with some of my choices.

BLANKED_MEANS_STOP = True
PIDOF_INVOKE = ['pidof']
DRY_RUN = True

# With these commands you probably could extend compatibility to
# a different screensaver.
SS_TIME_INVOKE = ['xscreensaver-command', '-time']
SS_WATCH_INVOKE = ['xscreensaver-command', '-watch']
# List of tuples of `(regex, reaction)`, where `reaction` must be one of
# 'STOP', 'CONT', 'IGN'.  If none of the regexes matches, Briar Rose
# sends SIGCONT to all processes and aborts.
SS_TIME_PARSE = [('screen non-blanked', 'CONT'),
                 ('screen blanked', 'STOP' if BLANKED_MEANS_STOP else 'CONT'),
                 ('screen locked', 'STOP')]
SS_WATCH_PARSE = [('^LOCK ', 'STOP'),
                  ('^BLANK ', 'STOP' if BLANKED_MEANS_STOP else 'CONT'),
                  ('^UNBLANK ', 'CONT'),
                  ('^RUN', 'IGN')]


# ===== CODE =====
# You really shouldn't need to change anything beyond here.

RULE_NOOP = (True, set())


def compile_parser(parser):
    accu = []
    for pattern, reaction in parser:
        assert reaction in ['STOP', 'CONT', 'IGN'], \
            'Pattern "{}" has invalid reaction {}!'.format(pattern, reaction)
        accu.append((re.compile(pattern), reaction))
    return accu


SS_TIME_CCRE = compile_parser(SS_TIME_PARSE)
SS_WATCH_CCRE = compile_parser(SS_WATCH_PARSE)


def get_reaction(event, ccre_list):
    for ccre, reaction in ccre_list:
        if ccre.search(event):
            return reaction
    print('Unexpected event "{}"\nAbort!'.format(event))
    exit(1)


def pidof(pname):
    # Thanks to https://stackoverflow.com/a/35938503/3070326
    args = PIDOF_INVOKE + [pname]
    try:
        return set(map(int, subprocess.check_output(args).split()))
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
        print('WARNING: Reserved character {}.  '
              'Might be the config file of a future version!'
              .format(rule[0]), file=err_fd)
        return RULE_NOOP
    if rule[0] == '=':
        try:
            return (not is_exception, {int(rule[1:])})
        except ValueError:
            print('WARNING: Could not parse PID "{}"!'
                  .format(rule[1:]), file=err_fd)
            return RULE_NOOP
    if rule[0] == '!':
        if is_exception:
            print('WARNING: Double-exceptions are a syntax error!',
                  file=err_fd)
            return RULE_NOOP
        return parse_rule(rule[1:], err_fd, is_exception=True)
    if rule[0] == '"':
        rule = rule[1:]
        if rule[-1] == '"':
            print('WARNING: Rule starts and ends with quotation mark.  '
                  'It is possible this line has the wrong syntax!',
                  file=err_fd)
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
            print('{} PIDs added.  PID set is now {}'
                  .format(len_after - len_before, sorted(pids)), file=err_fd)
        elif len_after < len_before:
            print('{} PIDs removed.  PID set is now {}'
                  .format(len_before - len_after, sorted(pids)), file=err_fd)
        else:
            print('PID set unchanged', file=err_fd)
    print('Parsing completed.', file=err_fd)
    return pids


LAST_PIDS = {}


def update_pids(config_path, err_fd):
    global LAST_PIDS
    try:
        fd = open(config_path, 'r')
        # If you really need to stop a program of unknown pid
        # with \r or \n in its name, then you're fucked anyway.
        new_pids = parse_rules([line.rstrip('\r\n')
                                for line in fd.readlines()], err_fd)
        fd.close()  # If this leaks, the program is about to die anyway.
        LAST_PIDS = new_pids
    except OSError as e:
        print('Cannot read config file: {}'.format(e), file=err_fd)


def run_debug(config_path):
    update_pids(config_path, sys.stdout)
    print('So I would watch over {} pids currently.'.format(len(LAST_PIDS)))


def send_sig_all(sig):
    for pid in LAST_PIDS:
        try:
            if DRY_RUN:
                print('Would send {} to PID {}'.format(sig, pid),
                      file=sys.stderr)
            else:
                print('Sending {} to PID {}'.format(sig, pid), file=sys.stderr)
                os.kill(pid, sig)
        except OSError as e:
            print('Could not send {} to PID {}: {}'.format(sig, pid, e),
                  file=sys.stderr)


def execute_reaction(reaction, config_path=None):
    if reaction == 'IGN':
        pass
    elif reaction == 'STOP':
        if config_path is not None:
            update_pids(config_path, sys.stderr)
        send_sig_all(signal.SIGSTOP)
    elif reaction == 'CONT':
        send_sig_all(signal.SIGCONT)
    else:
        print('Invalid reaction {}?!', file=sys.stderr)
        exit(1)


def run_daemon(config_path):
    print('Booting', file=sys.stderr)
    if DRY_RUN:
        print('IN DRY RUN MODE!  '
              'To change this, change the constant DRY_RUN to false!',
              file=sys.stderr)
    print('SIGSTOP={}, SIGCONT={}'.format(signal.SIGSTOP, signal.SIGCONT),
          file=sys.stderr)
    update_pids(config_path, sys.stderr)
    atexit.register(send_sig_all, signal.SIGCONT)

    # Read `xscreensaver-command -time`, react
    time_output = subprocess.check_output(SS_TIME_INVOKE).decode('UTF-8')
    reaction = get_reaction(time_output, SS_TIME_CCRE)
    del time_output
    execute_reaction(reaction)

    # Set up pipe from `xscreensaver-command -watch`
    # Note: Timing race!  Sadly, there is no way to call
    # `xscreensaver-command -watch` in a way that tells us the current state.
    # So we just have to hope that xscreensaver does not change state in this
    # short timeframe.
    # TODO: Connect to `xscreensaver-command -watch`, run in loop
    watch = subprocess.Popen(SS_WATCH_INVOKE,
                             bufsize=1, universal_newlines=True,
                             stdin=subprocess.DEVNULL, stdout=subprocess.PIPE)
    print('\nStarted watchdog with PID {} on {}'
          .format(watch.pid, datetime.now()), file=sys.stderr)

    try:
        for line in watch.stdout:
            reaction = get_reaction(line, SS_WATCH_CCRE)
            print('\n{} triggered on {}'.format(reaction, datetime.now()),
                  file=sys.stderr)
            execute_reaction(reaction, config_path)
    except KeyboardInterrupt:
        print('\nCtrl-C on {}'.format(datetime.now()), file=sys.stderr)
        # This is the only way of achieving a zero exit-code
        exit(0)
    print('\nWatchdog died unexpectedly on {}!'.format(datetime.now()),
          file=sys.stderr)
    exit(1)


def default_pidfile_path():
    if 'XDG_RUNTIME_DIR' in os.environ:
        return '{}/briar_rose.pid'.format(os.environ['XDG_RUNTIME_DIR'])
    if 'USER' in os.environ:
        return '/tmp/{}-briar_rose.pid'.format(os.environ['USER'])
    return '/tmp/briar_rose.pid'


def run_args(args):
    config_path = None  # Must be replaced by dynamic default value
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
        with PidFile(pidname=basename(pidfile_path),
                     piddir=dirname(pidfile_path),
                     enforce_dotpid_postfix=False):
            run_daemon(config_path)


if __name__ == '__main__':
    run_args(sys.argv[1:])
