import json
import os
import sys

from invoke import task


@task
def run(ctx, app="calc", lang=None, debug=False):
    """
    Run the selected app.
    """
    from streamlit.cli import main

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
def i18n(ctx, edit=False, lang="pt_BR"):
    ctx.run("pybabel extract -k __ -o pydemic_ui/locale/messages.pot pydemic_ui")
    ctx.run("pybabel update -i pydemic_ui/locale/messages.pot -d pydemic_ui/locale")
    if edit:
        ctx.run(f"poedit pydemic_ui/locale/{lang}/LC_MESSAGES/messages.po")
    ctx.run("pybabel compile -d pydemic_ui/locale")


@task
def test(ctx):
    ctx.run("pytest tests/ --cov")
    ctx.run("black --check .")
    ctx.run("pycodestyle")


@task
def build(ctx, tag=None):
    ctx.run("sudo docker-compose build")


@task
def deploy(ctx, user=None, server=None, opts=None):
    ctx.run("git push")

    try:
        with open(".deploy.json") as fd:
            data = json.load(fd)
    except FileNotFoundError:
        data = {}

    user = user or data.get("user", os.environ.get("USER", "user"))
    server = server or data.get("server", "localhost")
    opts = opts or data.get("opts") or ""
    ctx.run(f"fab -eH {user}@{server} {opts} update")


@task
def publish(ctx):
    ctx.run("flit publish")


@task
def clear_cache(ctx, all=False):
    extra = ("pydemic",) if all else ()
    for dir in ("ui", "ui.info", "ui.app.calc", *extra):
        ctx.run(f"rm ~/.local/pydemic/cache/{dir} -rfv")
