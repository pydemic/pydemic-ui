FROM python:3.8.2-slim

ENV PYTHONUNBUFFERED=1 \
    FLIT_ROOT_INSTALL=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_FILE_WATCHER_TYPE=none

COPY assets/locale.gen /etc/locale.gen

RUN apt-get update && \
    apt-get install -y locales && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    locale-gen && \
    pip --no-cache-dir install --upgrade pip && \
    pip --no-cache-dir install flit invoke

RUN pip --no-cache-dir install babel sidekick pandas
RUN pip --no-cache-dir install streamlit
RUN pip --no-cache-dir install altair matplotlib seaborn

WORKDIR /app

COPY pyproject.toml tasks.py ./

RUN mkdir pydemic_ui && \
    echo "README" > README.rst && \
    echo "'''pydemic-ui'''" >> pydemic_ui/__init__.py && \
    echo "__version__ = '0.0.0'" >> pydemic_ui/__init__.py && \
    flit install -s --deps=production

COPY pydemic_ui pydemic_ui
COPY README.rst README.rst

RUN inv i18n

CMD [ "inv", "run" ]
