from backend.app.api.routes_webhook import CLEANUP_SQL


def test_cleanup_sql_interval_format():
    sql = str(CLEANUP_SQL)
    assert "|| ' days'" not in sql
    assert "INTERVAL '1 day'" in sql
