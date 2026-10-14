"""Developer CLI.

Usage (from the repository root):

    python -m backend.manage serve            # run the dev server with reload
    python -m backend.manage init-db          # create the schema
    python -m backend.manage seed             # seed catalogue + demo accounts
    python -m backend.manage reset-db         # drop, recreate and re-seed
    python -m backend.manage create-admin EMAIL PASSWORD "Full Name"
    python -m backend.manage routes           # list every registered route
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from .app.config import settings
from .app.database import SessionLocal, create_all, dispose_engine, drop_all
from .app.security import hash_password


async def _init_db() -> None:
    await create_all()
    print(f"✓ Schema ready ({'sqlite' if settings.is_sqlite else 'postgres'})")


async def _seed() -> None:
    from .app.seed import seed_all

    await create_all()
    await seed_all()
    print("✓ Seed complete")


async def _reset_db() -> None:
    await drop_all()
    print("✓ Tables dropped")
    await create_all()
    print("✓ Tables created")
    if settings.seed_demo_data:
        from .app.seed import seed_all

        await seed_all()
        print("✓ Data seeded")


async def _create_admin(email: str, password: str, full_name: str) -> None:
    from sqlalchemy import select

    from .app import models

    await create_all()
    async with SessionLocal() as session:
        email = email.lower()
        user = await session.scalar(select(models.User).where(models.User.email == email))
        if user is None:
            user = models.User(
                email=email,
                full_name=full_name,
                password_hash=hash_password(password),
                role="admin",
                is_verified=True,
            )
            session.add(user)
            print(f"✓ Admin created: {email}")
        else:
            user.role = "admin"
            user.password_hash = hash_password(password)
            print(f"✓ Existing user promoted to admin: {email}")
        await session.commit()


def _serve(host: str, port: int, reload: bool) -> None:
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="debug" if settings.debug else "info",
    )


def _routes() -> None:
    from .app.main import app

    for route in app.routes:
        methods = ",".join(sorted(getattr(route, "methods", []) or ["WS"]))
        print(f"{methods:<22} {getattr(route, 'path', route)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m backend.manage", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="run the development server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--no-reload", action="store_true")

    sub.add_parser("init-db", help="create database tables")
    sub.add_parser("seed", help="seed catalogue and demo data")
    sub.add_parser("reset-db", help="drop, recreate and re-seed")
    sub.add_parser("routes", help="list registered routes")

    admin = sub.add_parser("create-admin", help="create or promote an admin user")
    admin.add_argument("email")
    admin.add_argument("password")
    admin.add_argument("full_name", nargs="?", default="Administrator")

    args = parser.parse_args(argv)

    try:
        if args.command == "serve":
            _serve(args.host, args.port, not args.no_reload)
        elif args.command == "init-db":
            asyncio.run(_init_db())
        elif args.command == "seed":
            asyncio.run(_seed())
        elif args.command == "reset-db":
            asyncio.run(_reset_db())
        elif args.command == "create-admin":
            asyncio.run(_create_admin(args.email, args.password, args.full_name))
        elif args.command == "routes":
            _routes()
    except KeyboardInterrupt:
        return 130
    finally:
        if args.command in {"init-db", "seed", "reset-db", "create-admin"}:
            asyncio.run(dispose_engine())
    return 0


if __name__ == "__main__":
    sys.exit(main())
