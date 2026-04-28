from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db

DEMO_ACCOUNTS = [
    {"role": "Pet Owner",       "name": "Ella Mendoza",    "email": "owner@tinpet.local",   "password": "owner123"},
    {"role": "Pet Owner",       "name": "Paolo Cruz",      "email": "owner2@tinpet.local",  "password": "owner123"},
    {"role": "Pet Owner",       "name": "Maria Garcia",    "email": "owner3@tinpet.local",  "password": "owner123"},
    {"role": "Pet Owner",       "name": "Jose Reyes",      "email": "owner4@tinpet.local",  "password": "owner123"},
    {"role": "Staff / Groomer", "name": "Mika Santos",     "email": "groomer@tinpet.local", "password": "groomer123"},
    {"role": "Staff / Groomer", "name": "Ana Lim",         "email": "staff2@tinpet.local",  "password": "staff123"},
    {"role": "Admin",           "name": "Tin Pet Admin",   "email": "admin@tinpet.local",   "password": "admin123"},
]


def _save_accounts_file() -> None:
    lines = [
        "TIN PET GROOMING — DEMO ACCOUNTS",
        "=" * 42,
        "",
    ]
    current_role = None
    for acc in DEMO_ACCOUNTS:
        if acc["role"] != current_role:
            current_role = acc["role"]
            lines.append(f"[ {current_role} ]")
        lines.append(f"  Name     : {acc['name']}")
        lines.append(f"  Email    : {acc['email']}")
        lines.append(f"  Password : {acc['password']}")
        lines.append("")
    out = Path(__file__).resolve().parent / "demo_accounts.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved: {out}")


def main() -> None:
    print("Initializing database...")
    db.init_db()
    print("Seeding demo data...")
    db.seed_demo_data()
    _save_accounts_file()
    print("\nDemo accounts:")
    for acc in DEMO_ACCOUNTS:
        print(f"  [{acc['role']}] {acc['email']} / {acc['password']}")
    print("\nRun: python app.py")


if __name__ == "__main__":
    main()
