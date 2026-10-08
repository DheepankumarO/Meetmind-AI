from pathlib import Path
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker


STORAGE_DIRECTORY = (
    Path(__file__).resolve().parents[1] / "storage"
)

DATABASE_PATH = STORAGE_DIRECTORY / "meetmind.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

class Base(DeclarativeBase):
    pass


engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def create_db_and_tables() -> None:
    STORAGE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    from backend.app.models import meeting

    Base.metadata.create_all(bind=engine)

    segment_columns = {
        column["name"]
        for column in inspect(engine).get_columns(
            "transcript_segments",
        )
    }

    if "speaker" not in segment_columns:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE transcript_segments "
                "ADD COLUMN speaker VARCHAR(50) "
                "NOT NULL DEFAULT 'Speaker 1'"
            )
