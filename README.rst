==========
Pydemic UI
==========
|Build Badge| |Coverage Badge|

.. |Build Badge|  image:: https://img.shields.io/github/workflow/status/GCES-Pydemic/pydemic-ui/Pydemic%20CI?logo=github&style=flat-square   
        :alt: GitHub Workflow Status

.. |Coverage Badge|  image:: https://codecov.io/gh/GCES-Pydemic/pydemic-ui/branch/master/graph/badge.svg
        :alt: Code Coverage
        :target: https://codecov.io/gh/GCES-Pydemic/pydemic-ui
        
        
A set of streamlit apps and utilities used in creating the UI for Pydemic apps.

Usage
=====

Install it using ``pip install pydemic-ui`` or your method of choice. Now, you can just import
it and load the desired functions. You can use pydemic-ui as a drop-in replacement for streamlit
by using

>>> from pydemic_ui import st
>>> st.pydemic(locale="pt-BR")

Apps
====

Pydemic-ui comes with a few Streamlit apps ready to deploy. Just execute the app module
specifying the desired app::

    $ python -m pydemic_ui.apps calc

Currently, only the calc app is available, but other apps should arrive soon. For more
options, execute it with the "--help" flag.

Development Usage
=================

Install the dependencies using the command bellow. More details are available on flit documentation(https://flit.readthedocs.io/en/latest/cmdline.html)::

    $ flit install -s --user

After the installation is completed, run streamlit apps using invoke::
    
    $ inv run

Development in Docker
=====================

The project has been containerized in Docker in order to speed up the setup of the development environment. You can run the containers using the methods below:

Docker Compose
--------------

You can run the project using Docker Compose by having it installed and running the following command::

    $ docker-compose up pydemic-ui

VSCode Remote - Containers
--------------------------

The project has a ``devcontainer.json``, so you can open it inside a container using Visual Studio Code by having the "Remote - Containers" ``ms-vscode-remote.remote-containers`` extension installed.

