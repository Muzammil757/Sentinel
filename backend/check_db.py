from database.connection import engine

with engine.connect() as connection:
    result = connection.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )

    tables = result.fetchall()

    print("Tables in Sentinel database:")
    for table in tables:
        print("-", table[0])