from inspect import getmodule
from os.path import isfile, isdir, join
import os
import sys
import re


install_platform = sys.platform
config_dir = os.path.split(os.path.abspath(__file__))[0]
home_dir = os.path.expanduser('~')
os.chdir(config_dir)


def link_configs():
    """Symlinks configuration files to the home directory

        Parses the ignore file for regexes and then generates a list of files
        which need to be simulinked"""
    os.chdir(home_dir)
    ignored = open(join(config_dir, "installer-ignore.yml"))
    ignore_patterns = "(" + ")|(".join(ignored) + ")"
    # Find all of the files in the config dir which
    to_link = [path for path in os.listdir()
               if not isfile(join(home_dir, path))
               and not re.match(ignore_patterns, path)
               or isdir(path) and not re.match(ignore_patterns, path.name)]

    if len(to_link) == 0:
        print("No files to move")
        return

    print("Preparing to symlink the following files")
    print("\n".join(path.name for path in to_link ))
    if query_yes_no("Are these the correct files?"):
        symlink_paths(to_link)

def symlink_paths(files_to_link, prefix=home_dir):
        # TODO: Convert to use portable native functions
        for f in files_to_link:
            # If the file doesnt on the home directory
            target = join(prefix, f)
            if not os.path.exists(target):
                print("Copying " + target)
                os.symlink(join(config_dir, f), target)
            elif isdir(f):
                symlink_paths(f, prefix=target)


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")

if __name__ == '__main__':
    link_configs()
