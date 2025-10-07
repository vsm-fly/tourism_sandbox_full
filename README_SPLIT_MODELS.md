# Split models into modules

## What is included
- `app/models/base.py` — common mixins
- `app/models/user.py` — users & roles
- `app/models/party.py` — clients & suppliers
- `app/models/finance.py` — transactions & bank accounts
- `app/models/tourism.py` — internal/external tours
- `app/models/__init__.py` — re-exports for backward-compatible imports

## How to integrate
1. Copy `app/models/` into your project.
2. In your `create_app`, make sure after `db.init_app(app)` you import models:
   ```python
   from app import models  # noqa: F401
   ```
3. Run migrations:
   ```bash
   flask db migrate -m "refactor: split models into modules (no schema changes)"
   flask db upgrade
   ```
4. Run the app and verify CRUD pages.
