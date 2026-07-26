"""
Reset (or create) an admin account's password.

Usage:
    python reset_admin_password.py <username> [new_password]

If <new_password> is omitted you'll be prompted for it (hidden input),
so it never lands in your shell history. Runs against whatever DATABASE_URL
your .env points at.
"""

import sys
import getpass

from database import SessionLocal
from models import AdminUser
from auth import hash_password


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python reset_admin_password.py <username> [new_password]")
        sys.exit(1)

    username = sys.argv[1]

    if len(sys.argv) >= 3:
        new_password = sys.argv[2]
    else:
        new_password = getpass.getpass("New password: ")
        confirm = getpass.getpass("Confirm password: ")
        if new_password != confirm:
            print("Passwords do not match. Aborting.")
            sys.exit(1)

    if not new_password.strip():
        print("Password cannot be empty. Aborting.")
        sys.exit(1)

    db = SessionLocal()
    try:
        user = db.query(AdminUser).filter(AdminUser.username == username).first()
        if user:
            user.password_hash = hash_password(new_password)
            action = "reset"
        else:
            user = AdminUser(username=username, password_hash=hash_password(new_password))
            db.add(user)
            action = "created"
        db.commit()
        print(f"Password {action} for admin '{username}'.")
    except Exception as e:
        db.rollback()
        print(f"Failed: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
