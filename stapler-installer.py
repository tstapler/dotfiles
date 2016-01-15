import glob, os, sys, click, subprocess
from yaml import load, dump
from plumbum import local, FG
from plumbum.cmd import sudo
from itertools import chain

install_platform = sys.platform
config_dir = os.path.dirname(os.path.realpath(__file__))
os.chdir(config_dir)

@click.group()
@click.option('--install_all', is_flag=True)
@click.option('--uninstall', is_flag=True)
def cli(install_all, uninstall):
    """Tyler Stapler's Dev environment installer. Currently for *nix and soon for Windows"""

    if install_all :
        pass
    elif uninstall:
        pass
    else:
        pass

@cli.command()
@click.argument('groups', nargs=-1)
def apps(groups):
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
        
@cli.command()
@click.argument('groups', nargs=-1)
def node_packages(groups):
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

@cli.command()
def perl_packages():
    pass

@cli.command()
def ruby_gems():
    pass


def libs():
    pass

if __name__ == '__main__':
    cli()
