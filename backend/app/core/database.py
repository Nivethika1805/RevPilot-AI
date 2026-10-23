import os
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger("revpilot")

# Configure engine
connect_args = {}
db_url = settings.effective_database_url
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True
)

# Enable pragmas for SQLite
if db_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        if not os.environ.get("VERCEL"):
            cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

_initialized = False

def init_db():
    global _initialized
    if not _initialized:
        try:
            Base.metadata.create_all(bind=engine)
            db = SessionLocal()
            try:
                from app.models.entities import User
                if db.query(User).count() == 0:
                    from app.seed.seed_data import seed_database
                    logger.info("Initializing synthetic seed dataset...")
                    seed_database(db)
                    logger.info("Synthetic seed completed.")
            finally:
                db.close()
            _initialized = True
        except Exception as e:
            logger.error(f"init_db error: {e}", exc_info=True)

def get_db():
    init_db()
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
