import glob, os, inspect, sys, click, subprocess, re
from yaml import load, dump
from plumbum import local, FG
from plumbum.cmd import sudo
from itertools import chain

install_platform = sys.platform
config_dir = local.path(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
local.cwd.chdir(config_dir)

@click.group()
@click.option('--install_all', is_flag=True)
@click.option('--uninstall', is_flag=True)
def installer(install_all, uninstall):
    """Tyler Stapler's Dev environment installer. Currently for *nix and soon for Windows

        Installs various dev tools, namely vim and supporting apps

        The intent is to be able to run this anywhere python is installed
        and forget about the rest
    """

    if install_all :
        pass
    elif uninstall:
        pass
    else:
        pass

@installer.command()
@click.argument('groups', nargs=-1)
def apps(groups):
    """Installs applications using apt-get on debian"""
    npm = local["npm"]
    apt_get = sudo[local["apt-get"]]
    apps = load(open(os.path.join(config_dir, "apps.yml"), "r"))
    if len(groups) == 0:
        print(apt_get("install", *[app for app in apps["standalone"]]))
    else:
        for group in groups:
            if group in apps:
                print(apt_get("install", *[app for app in apps[group]]))
            else:
                print("There is no group called " + group)

@installer.command()
@click.argument('groups', nargs=-1)
def node_packages(groups):
    """Installs nodejs packages using npm"""
    npm = local["npm"]
    node_packages = load(open(os.path.join(config_dir, "node_packages.yml"), "r"))
    print(groups)
    if len(groups) == 0:
        for gen_type in node_packages["standalone"]:
            if gen_type == "generators":
                npm = sudo[npm["-g"]]
            else:
                npm = local["npm"]
            npm["install", [package for package in node_packages["standalone"][gen_type]]] & FG
    else:
        for group in groups:
            if group in node_packages:
                for gen_type in node_packages[group]:
                    print(npm)
                    if gen_type == "generators":
                        npm = sudo[npm["-g"]]
                    else:
                        npm = local["npm"]
                    npm["install", [package for package in node_packages[group][gen_type]]] & FG
            else:
                print("There is no group called " + group)

@installer.command()
def perl_packages():
    """Installs perl packages using cpan (Not Implemented)"""
    pass

@installer.command()
def ruby_gems():
    """Installs ruby gems using gem install (Not Implemented)"""
    pass

@installer.command()
def link_configs():
    """Symlinks configuration files to the home directory

        Parses the ignore file for regexes and then generates a list of files
        which need to be simulinked"""
    local.cwd.chdir(local.env.home)
    ignored = load(open(config_dir.join("installer-ignore.yml")))
    ignore_patterns = "(" + ")|(".join(ignored) + ")"
    to_link = [path for path in local.path(config_dir).list()
               if not local.path(local.env.home.join(path.name)).exists()
               and not re.match(ignore_patterns, path.name)
               or path.is_dir() and not re.match(ignore_patterns, path.name)]

    if len(to_link) == 0:
        print("No files to move")
        return
    print("Preparing to symlink the following files")

    print("\n".join(path.name for path in to_link ))
    if click.confirm("Are these the correct files?"):
        symlink_paths(to_link)

def symlink_paths(to_link, prefix=local.env.home):
        for item in to_link:
            #If the file doesnt on the home directory
            target = local.path(prefix.join(item.name))
            if not target.exists():
                print("Copying " + target)
                local.path(item).symlink(target)
            elif item.is_dir:
                print("Directory: " + target)
                symlink_paths(item, prefix=target)


@installer.command()
def uninstall():
    "Uninstall parts or all of the config"
    pass

if __name__ == '__main__':
    installer()
