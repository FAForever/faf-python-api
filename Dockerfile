FROM python:3.4.3

RUN pip install --upgrade pip
RUN apt-get update
RUN yes | apt-get install liblua5.1
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY requirements.txt /tmp/requirements.txt

RUN pip install --trusted-host content.dev.faforever.com -r /tmp/requirements.txt

ADD . /code/

COPY config.example.py /code/config.py

WORKDIR /code/

RUN pip install -e db
RUN pip install -e .

RUN cat config.py

CMD python run_local.py
