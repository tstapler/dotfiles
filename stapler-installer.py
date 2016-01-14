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
@click.argument('groups', nargs=-1)
def apps(groups):
    apt_get = sudo[local["apt-get"]]
    apps = load(open(os.path.join(config_dir, "apps.yml"), "r"))
    if len(groups) == 0:
        for app in apps["standalone"]:
            print(apt_get("install", app))
    else:
        for group in groups:
            if group in apps:
                for app in apps[group]:
                    print(apt_get("install", app))
            else:
                print("There is no group called " + group)
        
@cli.command()
@click.argument('groups', nargs=-1)
def node_packages(groups):
    print("Node Packages")
    npm = local["npm"]
    node_packages = load(open(os.path.join(config_dir, "node_packages.yml"), "r"))
    print(node_packages)
    if len(groups) == 0:
        for gen_type in node_packages["standalone"]:
            if gen_type is not None:
                print("Gen Type: " + gen_type)
                for node_package in node_packages["standalone"][gen_type]:
                    print(npm("install", node_package))
    else:
        for group in groups:
            if group in node_packages:
                for gen_type in node_packages[group]:
                    if gen_type == "generate":
                        npm = sudo[npm]
                    for node_package in node_packages[group][gen_type]:
                        print(npm("install", gen_type, node_package))
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
