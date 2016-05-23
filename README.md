[![Build Status](https://travis-ci.org/FAForever/api.svg?branch=develop)](https://travis-ci.org/FAForever/api)
[![Coverage Status](https://coveralls.io/repos/github/FAForever/api/badge.svg?branch=develop)](https://coveralls.io/github/FAForever/api?branch=develop)

# FAForever Python Web API
This repository holds the web api (written in python) that is run on the server to
provide required REST services to clients.

# Documentation

Currently documentation is sparse. Please help us out!

## Installation From GIT
When downloading from git be sure to run `git clone --recurse-submodules` on initial install, or if it is already cloned then run `git submodule update --init`.

## Installation - Docker

Get [docker](http://docker.com).

Quick overview of Docker can be found:
[Docker Quick Start Guide](https://docs.docker.com/engine/quickstart/)

First you must install and configure the database component [faf-db](https://github.com/FAForever/db)
You can either manually install the component and follow the instructions on the Github page or run init_and_wait_for_db.sh (Linux and OS X only).

Now you can run the script by typing (You will need netcat installed on the computer)

    ./init_and_wait_for_db.sh

**You will need to modify config.example.py with the correct database parameters OR update environment variables.**

Build the container using

    docker build -t faf-api .

Run using

    docker run -d --name faf-api --link faf-db:db -p 8080:8080 faf-api

Check to see if running by looking at the container and netstat

    docker ps

If using linux, you can now access the api at http://localhost:8080, otherwise follow below instructions.

Find containers IP (Container ID can be found under docker ps)

    docker inspect <container_id> (IP is under IPAddress in NetworkSettings)

With the containers IP you can access the API by going to http://IP:8080/ranked1v1

If you would like to access the IP through an easy URL, then modify yours hosts file /etc/hosts

    IP dev.faforever.com

You can then access the API by going to http://dev.faforever.com:8080

Logs are viewable by

    docker logs faf-api

If you want to view the raw JSON on the website, then you will need to allow 'Allow-Control-Allow-Origin'' in the browser.
Here is an example extension for Chrome - (https://chrome.google.com/webstore/detail/allow-control-allow-origi/nlfbmbojpeacfghkpbjhddihlkkiljbi?hl=en)

## Compiling and Building the Documentation
Documentation is currently handled by Sphinx until there is a more solid API. The documentation can be built using the following command:

    ./create_documentation.sh
