# sphinx-docs

Write and update Sphinx documentation for this project.

## Usage

When adding new features, updating architecture, or maintaining project docs.

## Instructions

1. **Source files** are in `docs/` as reStructuredText (`.rst`):
   - `docs/index.rst` — main table of contents
   - `docs/installation.rst` — setup instructions
   - `docs/quickstart.rst` — getting started guide
   - `docs/architecture.rst` — project layout and patterns
   - `docs/configuration.rst` — environment variables reference
   - `docs/adding-modules.rst` — how to add new modules
   - `docs/api/modules.rst` — autodoc for module classes

2. **Add a new page**:
   - Create `docs/{topic}.rst`
   - Add it to the toctree in `docs/index.rst`:
     ```rst
     .. toctree::
        :maxdepth: 2
        :caption: Contents:

        installation
        quickstart
        {topic}
     ```

3. **Write docstrings** in source code (used by autodoc):
   ```python
   def create_user(email: str, password: str) -> User:
       """Create a new user account.

       Args:
           email: User's email address.
           password: Plain text password (will be hashed).

       Returns:
           The created User instance.

       Raises:
           ConflictError: If email already exists.
   """
   ```

4. **Update translations** after changing docs:
   ```bash
   make -C docs gettext        # extract strings
   make -C docs translate      # update .po files
   # Edit docs/locale/fa_IR/LC_MESSAGES/*.po with translations
   make -C docs html           # rebuild all languages
   ```

5. **Build docs locally**:
   ```bash
   make -C docs html
   open docs/_build/en/index.html
   ```

6. **Preview Persian docs**:
   ```bash
   make -C docs html
   open docs/_build/fa_IR/index.html
   ```

## Conventions

- Use reStructuredText (`.rst`), not Markdown
- Code examples use `.. code-block:: language` directive
- Cross-reference with `:ref:`, `:func:`, `:class:` roles
- Keep pages focused: one topic per file
- All translatable strings must be outside code blocks
- Persian translations go in `docs/locale/fa_IR/LC_MESSAGES/`
- GitHub Pages deploys both `en/` and `fa_IR/` subdirectories
