from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from infrastructure.database.postgres.base import Base, engine
from infrastructure.database.postgres.demo_seed import ensure_demo_data


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_demo_data()
    print("Seed completed. Demo users: senol@example.com / ayse@example.com / mehmet@example.com (password: 1234)")


if __name__ == "__main__":
    seed()
