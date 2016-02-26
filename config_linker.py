from os.path import join
import os
import sys
import re


install_platform = sys.platform
config_dir = os.path.split(os.path.abspath(__file__))[0]
home_dir = os.path.expanduser('~')

#Read installer ignore file
ignored = [line.split("#", 1)[0].strip("\n")
            for line in open(join(config_dir, "installer-ignore.yml"))
            if line.split("#", 1)[0] != ""]
ignore_patterns = "(" + ")|(".join(ignored) + ")"

def link_configs(config_dir=config_dir, destination= home_dir):
    """Symlinks configuration files to the destination directory

        Parses the ignore file for regexes and then generates a list of files
        which need to be simulinked"""

    to_link, absent_dirs = find_absences(source=config_dir, destination=destination)


    if len(to_link) == 0:
        print("No files to move")
        return

    print("Preparing to symlink the following files")
    print("\n".join(link[1] for link in to_link))
    if query_yes_no("Are these the correct files?"):
        create_dirs_and_link(links=to_link, dirs=absent_dirs)

def find_absences(source=config_dir, destination=home_dir):
    absent_dirs = []
    to_link = []
    for root, dirs, files in os.walk(source, topdown=True):
        rel_path = os.path.relpath(root, source)
        if rel_path == ".":
            rel_path = ""

        # Remove ignored directories from the walk
        dirs[:] = [dir_name for dir_name in dirs if not re.match(ignore_patterns, dir_name)]
        files[:] = [f for f in files if not re.match(ignore_patterns, f)]

        # Create list of dirs that dont exist
        for dir_name in dirs:
            if not os.path.exists(join(destination, rel_path, dir_name)):
                print "Doesnt Exist"
                absent_dirs.append(join(destination, rel_path, dir_name))

        # Create a list of files to be symlinked
        for f in files:
            if not os.path.exists(join(destination, rel_path,f)):
                # Add the source and destination for the symlink
                to_link.append((join(root, f), join(destination, rel_path, f)))

        return to_link, absent_dirs

def create_dirs_and_link(links=[], dirs=[]):
        for dir_name in dirs:
            os.makedirs(dir_name)
        for link in links:
            os.symlink(link[0], link[1])


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
