[![Build Status](https://travis-ci.org/FAForever/api.svg?branch=develop)](https://travis-ci.org/FAForever/api)
[![Coverage Status](https://coveralls.io/repos/github/FAForever/api/badge.svg?branch=develop)](https://coveralls.io/github/FAForever/api?branch=develop)

# FAForever Python Web API
This repository holds the web api (written in python) that is run on the server to
provide required REST services to clients.

# Documentation

Currently documentation is sparse. Please help us out!

## Installation - Docker

Get [docker](http://docker.com).

Build the container using

    docker build -t faf-api .

Run using

    docker run -d --name faf-api --link faf-db:db faf-api

## Installation - Manual

* Install Python 3.4 or later
* Install LuaJIT (or remove it from requirements.txt and use not the api methods)
* Install Dependencies `pip install -r requirements.txt`
* Install MySql Server
* Create faf database: https://github.com/FAForever/db
* Create `config.py` (you can use `config.example.py` as template) 
