import glob, os, sys, click, subprocess
from yaml import load, dump
from plumbum import local, FG
from plumbum.cmd import sudo

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
def apps():
    apt_get = sudo[local["apt-get"]]
    apps = load(open(os.path.join(config_dir, "apps.yml"), "r"))
    for app in apps["standalone"]:
        print(apt_get("install", app))
        
@cli.command()
def node_packages():
    npm = local["npm"]
    pass

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
