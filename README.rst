==========
Pydemic UI
==========
|Build Badge|

.. |Build Badge|  image:: https://img.shields.io/github/workflow/status/GCES-Pydemic/pydemic-ui/Pydemic%20CI?logo=github&style=flat-square   
        :alt: GitHub Workflow Status
        
        
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
=====

Install the dependencies using  the command bellow. More details are available on flit documentation(https://flit.readthedocs.io/en/latest/cmdline.html).

    $ flit install -s --user

After the installation is completed, run streamlit apps using invoke
    
    $ inv run