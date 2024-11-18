 #!/bin/sh

echo 'Creating Python virtual environment in .venv...'
python3.12 -m venv .venv

echo 'Installing dependencies from "requirements.txt" into virtual environment (in quiet mode)...'
.venv/bin/python -m pip --quiet --disable-pip-version-check install -r requirements-dev.txt
.venv/bin/python -m pip --quiet --disable-pip-version-check install -e src/backend

