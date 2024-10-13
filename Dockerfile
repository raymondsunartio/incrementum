FROM python:3.12

WORKDIR /app

RUN apt-get update &&\
    rm -rf /var/lib/apt/lists*

RUN wget https://dot.net/v1/dotnet-install.sh -O dotnet-install.sh
RUN chmod +x ./dotnet-install.sh
RUN ./dotnet-install.sh --version latest

RUN pip install pipenv
COPY Pipfile Pipfile.lock /app/
ARG PIPENV_INSTALL_ARGS="--system --deploy"
RUN pipenv install ${PIPENV_INSTALL_ARGS}

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONIOENCODING=UTF-8
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV DOTNET_ROOT="/root/.dotnet"

COPY . /app/
