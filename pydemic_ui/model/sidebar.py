from .. import st
from .base import UIBaseProperty


class UISidebarProperty(UIBaseProperty):
    """
    Module that binds to streamlit sidebar by default.
    """

    __slots__ = ()
    module = st.sidebar
