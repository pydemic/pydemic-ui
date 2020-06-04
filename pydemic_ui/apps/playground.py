from pydemic_ui import st


def main(**kwargs):
    reg = st.region_input("BR", arbitrary=True)
    st.write(reg)
