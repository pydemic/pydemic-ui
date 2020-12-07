FROM python:3.8.5-slim

ENV PYTHONUNBUFFERED=1 \
    FLIT_ROOT_INSTALL=1 

COPY assets/locale.gen /etc/locale.gen

RUN apt update && \
    apt install -y git locales wkhtmltopdf && \
    locale-gen

WORKDIR /app

RUN pip --no-cache-dir install flit invoke

COPY . .

RUN flit install

RUN pip uninstall -y pydemic-models
RUN pip install git+https://github.com/GCES-Pydemic/pydemic.git

RUN inv i18n

CMD [ "inv", "run" ]