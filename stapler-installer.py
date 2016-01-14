import sys, click

class Installer:
    def __init__(self):
        self.install_platform = sys.platform

    def install_apps():
        pass

    def install_libs():
        pass

    def configure_env():
        """Make changes to existing system configuration"""
        pass

    def link_config_files():
        pass



@click.command()
@click.option('--all', 'install_type', is_flag=True)
@click.option('--apps', 'install_type', is_flag=True)
@click.option('--libs', 'install_type', is_flag=True)
@click.option('--uninstall', 'install_type', is_flag=True)
def cli(all, apps, libs, uninstall):
    """Tyler Stapler's Dev environment installer. Currently for *nix and Windows"""
    pass

if __name__ == '__main__':
    cli()
