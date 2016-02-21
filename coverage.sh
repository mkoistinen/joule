#!/bin/bash

coverage run manage.py test && coverage report -m

