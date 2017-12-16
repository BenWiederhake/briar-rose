# briar-rose

> "Does nothing, successfully." – Briar Rose.  Or was it `man true`?

When I lock my screen, the computer is supposed to do nothing much.
I don't use Stand-By because servers for git, ssh, irc, and other things are supposed to continue.
But they *do* nothing.

But many browsers, IM clients, mail clients, Electron-based things, … they just don't care.
No user in sight?  Alright, let's use the CPU full-throttle for hours on end!

And I don't like that.  That's why I wrote this daemon-like thing to `SIGSTOP`
these programs whenever xscreensaver is active, which usually means I'm away.
On unlock, it issues a `SIGCONT`, and things get rolling again.

Note that some programs like Slack don't like this, and will do a full reload on wakeup.
I prefer this small delay over the wasted power, because sometimes I'm away for long stretches of time.

## Install

Configure `briar-rose.config`, and do `pip3 install pid`.
If you feel fancy, do your virtualenv stuff.

You *can* also copy the python file to `/usr/local/bin/briar-rose`,
put your config file somewhere like `$HOME/.config/briar-rose.config`
and invoke it on session start with the path to the config file as argument.

## Run

`./briar_rose.py [--debug]  [--pidfile PATH_TO_PIDFILE] [--config PATH_TO_CONFIG_FILE]`

The default config file is `briar_rose.config` of the current working directory.

The default pidfile is `${XDG_RUNTIME_DIR}/briar_rose.pid`,
or if that environment variable is not defined, then `/tmp/${USER}-briar_rose.pid`,
or if that environment variable *also* is not defined, then just `/tmp/briar_rose.pid`.

The option `--debug` shows how the config file would currently be interpreted, and exit immediately.
Does not interact with the lock at all.

Briar Rose attempts to load the config file on start and every time it is about to stop processes – and *only* then.
So if you lock your screen which stops Firefox, and then uncomment the rule for Firefox,
and then unlock the screen, then Briar Rose will still remember to wake up Firefox.
Briar Rose will also wake up processes which it couldn't stop.

Should Briar Rose ever have problems to reload the config file (deleted, read error, invalid syntax(?)),
then the old config is kept, and an error message is printed to STDERR.
The inital config is empty, i.e., no processes would be stopped.

If the xscreensaver watch dies or produces unexpected output,
Briar Rose will wake up all processes and exit with non-zero error code.

<!-- Fail-SIGCONT, eh? -->

## Syntax

The config file describes the set of processes that need to be stopped.
The order matters only if you use exclusion rules: the rules are applies sequentially.

- Empty lines and rules that start with the octothorpe `#` are comments and get ignored.
- The characters `§$&^?.+-*@` are reserved for future use and are currently ignored.
- Rules that start with the equals sign `=` are taken to be PIDs.
- Rules that start with the double quotation mark `"` are taken to be process names.
  Note that there should not be a matching quotation mark, so `"firefox"` would be interpreted as the process name `firefox"`,
  including the trailing quotation mark.
  All processes with this name are included.
  Process names are **NOT** checked for sanity!
  It is not an error if no such process is running, as this is supposed to be a fire-and-forget daemon.
  This rule exists so we can handle the edge case where a process name begins with a special character.
- If rule starts with none of the above characters and not the exclamation mark `!`, it is taken as a process name.
  This is the common scenario.
- If a rule start with an exclamation mark, the rest of the rule is interpreted according to the
  previous lines, and taken as exclusion.  It is an error (reated as a comment) to begin a rule with two exclamation marks `!!`.

Example:

    firefox
    "asd_sd^asd  üüÜ↓→
    =2543
    !=9876

This means that process called "firefox", any process with the name `asd_sd^asd  üüÜ↓→`,
and process 2543 are stopped, but not process 9876 (even if it is called "firefox", or that weird `asd_sd^asd  üüÜ↓→` thing.)

<!-- Me, in two years, on the syntax: "It seemed like a good idea at the time." -->

## TODOs

- Commit and include a CC0 image of Briar Rose.
- Integration with systemd?
- Proper `--help` and Usage message.
- Include other browsers, mail clients, electron apps, etc.
- Check whether it builds on other OSes, make it more portable.
- Modularization.  Currently, if the user disagrees with a "section" of the config,
  they have to comment out each line individually.
- Come up with a good way to manage the logs.
  Current solution: Run it in a terminal, read it when there are any problems.

PRs welcome!

## Why "Briar Rose"?

Because it's the main protagonist of the story Sleeping Beauty.
I do recognize that it might have been more appropriate to use the names of the witch and the prince, and combine them somehow.

Other good names would have been
partial-suspend (because it's like suspend for only some of the programs), and
heisenberg-desktop (because the desktop is only there when you observe it).

Fork it, rename it, it's MIT licensed after all.

## License

MIT, so do whatever you want with it.  
Mentioning me as the original author would be nice.
