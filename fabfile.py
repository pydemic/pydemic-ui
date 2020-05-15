import sys
from pathlib import Path

from fabric import task
from patchwork import info, packages


@task
def configure(ctx):
    """
    Configure host with Docker, docker-compose, etc.
    """
    print("Warning! This command is still under development!")

    # Check distro
    distro = info.distro_family(ctx)
    if distro != "debian":
        print(f"Only supports Debian-based distros, got '{distro}'", file=sys.stderr)
        return

    distro = info.distro_name(ctx)
    print(f"Installing packages on {distro} machine...")
    print("This recipe was tested on Ubuntu.")

    # Install required packages
    packages.package(ctx, "python3-pip")
    ctx.run("pip3 install docker-compose")
    git_clone(ctx)


@task
def git_clone(ctx):
    """
    Clone repository.
    """
    ctx.run("git clone https://github.com/pydemic/pydemic-ui.git app")


@task
def git_pull(ctx):
    """
    Update repository.
    """
    ctx.run("cd app && git pull -f")


@task
def download(ctx, file, name=None):
    """
    Download file from server.
    """
    data = ctx.get(file)
    if name is None:
        name = Path(file).name

    with open(name, "bw") as fd:
        fd.write(data)


@task
def update(ctx):
    """
    Update server
    """
    git_pull(ctx)
    ctx.sudo("cd app && docker-compose build")
    ctx.sudo("cd app && docker-compose down")
    ctx.sudo("cd app && docker-compose up")
