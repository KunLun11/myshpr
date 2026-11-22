"""Migration / schema integrity checks against a live database."""

from sqlalchemy import text

from app.db.base import Base


async def test_all_model_tables_exist(session) -> None:
    result = await session.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    )
    existing = {row[0] for row in result}
    missing = set(Base.metadata.tables) - existing
    assert not missing, f"missing tables: {missing}"


async def test_required_extensions_present(session) -> None:
    result = await session.execute(
        text("SELECT extname FROM pg_extension WHERE extname IN ('citext', 'pg_trgm')")
    )
    assert {row[0] for row in result} == {"citext", "pg_trgm"}


async def test_cross_referencing_fks_present(session) -> None:
    result = await session.execute(
        text(
            "SELECT conname FROM pg_constraint WHERE contype = 'f' AND conname IN ("
            "'fk_topics_source_submission_id_topic_submissions',"
            "'fk_topic_submissions_duplicate_of_topic_id_topics')"
        )
    )
    assert {row[0] for row in result} == {
        "fk_topics_source_submission_id_topic_submissions",
        "fk_topic_submissions_duplicate_of_topic_id_topics",
    }
