from collections import namedtuple
from os.path import exists, join, relpath, expanduser, islink, split, abspath
from os import walk, symlink, makedirs
from filecmp import dircmp
from shutil import move
import os
import sys
import re

INSTALL_PLATFORM = sys.platform
CONFIG_DIR = split(os.path.abspath(__file__))[0]
HOME_DIR = expanduser("~")
MISSING_FILE_MESSAGE = "Please create a {} file in the same" \
                       " directory as the linker python file."

Link = namedtuple('Link', ['src', 'dest'])


class Linker(object):
    """Tyler Stapler's Config Linker

    Attributes:
        src: The location of the configuration to be linked
        dest: The location to be copied to
        folder_links:
        ignore_file:
    """
    def __init__(self,
                 src=CONFIG_DIR,
                 dest=HOME_DIR,
                 folder_links_file=None,
                 ignore_file=None):
        self.src = src
        self.dest = dest

        if folder_links_file is None:
            try:
                self.folder_links_file = join(CONFIG_DIR, ".folderlinks")
                exists(self.folder_links_file)
            except IOError:
                print(MISSING_FILE_MESSAGE.format(".folderlinks"))
                sys.exit(1)
        if ignore_file is None:
            try:
                self.ignore_file = join(CONFIG_DIR, ".linkerignore")
                exists(self.ignore_file)
            except IOError:
                print(MISSING_FILE_MESSAGE.format(".linkerignore"))
                sys.exit(1)

        self.folder_patterns = self._get_lines_from_file(self.folder_links_file)
        self.ignored_patterns = self._parse_regex_file(self.ignore_file)

    def link_configs(self):
        """Symlinks configuration files to the destination directory

        Parses the ignore file for regexes and then generates a list of files
        which need to be simulinked"""

        absent_files, absent_dirs = self.find_absences()

        if len(absent_files) == 0:
            print("No files to move")
            return

        print("Preparing to symlink the following files")
        print("\n".join(link.dest for link in absent_files))
        if self._query_yes_no("Are these the correct files?"):
            self._create_dirs(dirs=absent_dirs)
            self._create_links(links=absent_files)

    def find_absences(self):
        """ Walk the source directory and return a lists of diles and dirs absent
            from the destination directory

        Args:
            source: The path to copy from (Default is the script's location)
            destination The path to copy to (Defaults to home directory)

        Returns:
            absent_files: a list of Links
            absent_dirs: a list of paths to directories
        """
        absent_dirs = []
        absent_files = []
        for root, dirs, files in walk(self.src, topdown=True):
            rel_path = relpath(root, self.src)
            if rel_path == ".":
                rel_path = ""

            # Remove ignored directories from the walk
            dirs[:] = [dir_name for dir_name in dirs
                       if not re.match(self.ignored_patterns, dir_name)]
            files[:] = [f for f in files
                        if not re.match(self.ignored_patterns, f)]

            # Create list of dirs that dont exist
            for dir_name in dirs:
                if not exists(join(self.dest, rel_path, dir_name)):
                    absent_dirs.append(join(self.dest, rel_path, dir_name))

            # Create a list of files to be symlinked
            for f in files:
                if not exists(join(self.dest, rel_path, f)):
                    # Add the source and destination for the symlink
                    absent_files.append(Link(join(root, f),
                                        join(self.dest, rel_path, f)))

        return absent_files, absent_dirs

    def link_folders(self):
        """Link all the files in the folder link file

        Args:
            None

        Returns:
            None
        """

        for folder in self.folder_patterns:
            dest_folder_path = join(self.dest, folder)
            src_folder_path = join(self.src, folder)

            if exists(dest_folder_path) and exists(src_folder_path):
                # Syncronize dirs
                print(dest_folder_path)
                print(src_folder_path)
                dcmp = dircmp(dest_folder_path, src_folder_path)
                print dcmp.left_only
            elif exists(dest_folder_path) and not exists(src_folder_path):
                move(dest_folder_path, src_folder_path)
                symlink(src_folder_path, dest_folder_path)
            elif not exists(dest_folder_path) and exists(src_folder_path):
                symlink(src_folder_path, dest_folder_path)

    def _get_lines_from_file(self, file_path):
        """ Return a list of lines from a file minus comments

        Args:
            file_path (string): The path to the target file

        Returns:
            [string]
        """
        try:
            return [line.split("#", 1)[0].strip("\n")
                    for line in open(file_path)
                    if line.split("#", 1)[0] != ""]
        except IOError:
            return [""]

    def _parse_regex_file(self, file_path):
        """Parse the gitignore style file

        Args:
            file_path (string): The path to the target file

        Returns:
            string: Returns the regexes derived from the file
        """
        lines = self._get_lines_from_file(file_path)
        if lines == []:
            return ""
        else:
            return "(" + ")|(".join(lines) + ")"  # regex from list of regexes

    def _create_dirs(self, dirs=[]):
        """Creates all folders in dirs

        Args:
            dirs ([string]): A list of paths to be linked

        Returns:
            None: Does not return anything
        """
        for dir_name in dirs:
            makedirs(dir_name)

    def _create_links(self, links=[]):
        """Create symlinks for each item in links

        Args:
            links([Link]): a list of Links
        Returns:
            None: Does not return anything
        """
        for link in links:
            symlink(link.src, link.dest)

    def _query_yes_no(self, question, default="yes"):
        """Ask a yes/no question via raw_input() and return their answer.

        Args:
            question (string): a string that is presented to the user.
            default (string): the answer if the user just hits <Enter>.
                It must be "yes" (the default), "no" or None (meaning
                an answer is required of the user).

        Returns "answer" return value is True for "yes" or False for "no".
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

    linker = Linker()

    linker.link_configs()
    linker.link_folders()
