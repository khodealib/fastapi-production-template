Installation
============

Requirements
------------

- Python {{ cookiecutter.python_version }}+
- PostgreSQL 16+
- Redis 7+

Using uv (recommended)
----------------------

.. code-block:: bash

   git clone https://github.com/youruser/{{ cookiecutter.project_slug }}.git
   cd {{ cookiecutter.project_slug }}
   uv sync
   cp .env.example .env
   make up
   make migrate
   make dev

Using Docker
------------

.. code-block:: bash

   git clone https://github.com/youruser/{{ cookiecutter.project_slug }}.git
   cd {{ cookiecutter.project_slug }}
   make docker-up

The API will be available at ``http://localhost:8000``.
