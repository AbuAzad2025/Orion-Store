#!/bin/sh
set -e
flask db upgrade
exec gunicorn -b 0.0.0.0:5000 -w 2 --timeout 60 orion.wsgi:app
