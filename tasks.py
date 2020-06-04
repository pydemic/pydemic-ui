import os
import sys

import click
from invoke import task


@task
def run(
    ctx, app="app_menu", lang=None, debug=False, keep_cache=False, clear_cache_all=False
):
    """
    Run the selected app.
    """
    from streamlit.cli import main

    if not keep_cache:
        clear_cache(ctx, clear_cache_all)

    sys.argv = ["streamlit", "run", f"pydemic_ui/apps/{app}.py"]
    os.environ.update(
        {
            "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
            "STREAMLIT_SERVER_FILE_WATCHER_TYPE": "none",
            "DEBUG": str(debug).lower(),
            "LANG": lang or os.environ.get("LANG", "C"),
        }
    )
    main()


@task
def run_production(ctx):
    """
    Run calculator in production servers.
    """
    run(ctx, "calc")


@task
def i18n(ctx, edit=False, lang="pt_BR"):
    ctx.run("pybabel extract -k __ -o pydemic_ui/locale/messages.pot pydemic_ui")
    ctx.run("pybabel update -i pydemic_ui/locale/messages.pot -d pydemic_ui/locale")
    if edit:
        ctx.run(f"poedit pydemic_ui/locale/{lang}/LC_MESSAGES/messages.po")
    ctx.run("pybabel compile -d pydemic_ui/locale")


@task
def test(ctx, all=False, report_xml=False, verbose=False, clear_cache=False):
    if clear_cache:
        ctx.run("rm -rf .pytest_cache")
    suffix = " -vv " if verbose else ""
    if not all:
        ctx.run(f'pytest --maxfail=2 --lf -m "not slow" {suffix}', pty=True)
    if all:
        suffix += " --cov-report xml" if report_xml else ""
        ctx.run(f"pytest --cov {suffix}", pty=True)
        style(ctx)


@task
def style(ctx):
    ctx.run("black --check .")
    ctx.run("flake8 pydemic")


@task
def cov(ctx, report=True):
    ctx.run("pytest --cov --cov-report=html --cov-report=term", pty=True)


@task
def build(ctx, tag=None):
    ctx.run("sudo docker-compose build")


@task
def deploy(ctx, inventory="deploy-pydemic-ui/inventory.yml", restart=False):
    if restart:
        ctx.run(f"ansible-playbook -i {inventory} deploy-pydemic-ui/playbook-restart.yml")
    else:
        ctx.run(f"git push")
        ctx.run(f"ansible-playbook -i {inventory} deploy-pydemic-ui/playbook-update.yml")


@task
def publish(ctx):
    ctx.run("flit publish")


@task
def clear_cache(ctx, all=False):
    extra = ("pydemic",) if all else ()
    for dir in ("ui", "ui.info", "ui.app.calc", *extra):
        ctx.run(f"rm ~/.local/pydemic/cache/{dir} -rfv")


@task
def git(ctx, push=False):
    """
    Recommended git workflow
    """

    if not push:
        res = ctx.run("git status", pty=True)

        cmd = click.style("git add", fg="red", bold=True)
        add = click.prompt("$ " + cmd, prompt_suffix=" ")

        ctx.run(f"git add {add}", pty=True)

        cmd = click.style("git commit -m", fg="red", bold=True)
        msg = click.prompt("$ " + cmd, prompt_suffix=" ")

        result = ctx.run(f'git commit -m "{msg}"', pty=True)
        if result.exited != 0:
            ctx.run(f"git add {add}", hide=True)
            ctx.run(f'git commit -m "{msg}"', hide=True)
