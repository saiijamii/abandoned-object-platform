import argparse

from app.phase9.db import session_scope
from app.phase9.models import User
from app.phase9.security import ROLES, password_hash


parser = argparse.ArgumentParser()
parser.add_argument("username")
parser.add_argument("password")
parser.add_argument("--role", choices=sorted(ROLES), default="admin")
args = parser.parse_args()

with session_scope() as session:
    session.add(User(username=args.username, password_hash=password_hash(args.password), role=args.role, enabled=True))

print(f"created Phase 9 user: {args.username}")
