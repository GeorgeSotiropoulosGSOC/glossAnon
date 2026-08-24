"""Optional FastAPI REST interface for glossanon.

Importing this subpackage requires the ``api`` extra::

    pip install "glossanon[api]"

The app is created with :func:`glossanon.api.app.create_app` and exposed as the
module-level ``app`` for ``uvicorn glossanon.api.app:app``.
"""
