import os
from sqlalchemy import inspect, text
from app.database import sync_engine
from app.models.models import Base

def upgrade_schema():
    inspector = inspect(sync_engine)
    with sync_engine.connect() as conn:
        for table_name, table in Base.metadata.tables.items():
            if inspector.has_table(table_name):
                existing_columns = {c['name'] for c in inspector.get_columns(table_name)}
                for column in table.columns:
                    if column.name not in existing_columns:
                        col_type = column.type.compile(sync_engine.dialect)
                        nullable = "NULL" if column.nullable else "NOT NULL"
                        default = column.server_default.arg if column.server_default else ""
                        if default:
                            default = f"DEFAULT {default}"
                        elif column.default and not callable(column.default.arg):
                            default = f"DEFAULT '{column.default.arg}'" if isinstance(column.default.arg, str) else f"DEFAULT {column.default.arg}"
                        
                        alter_cmd = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type} {default}"
                        print(f"Executing: {alter_cmd}")
                        conn.execute(text(alter_cmd))
                        conn.commit()
    print("Schema upgraded!")

if __name__ == '__main__':
    upgrade_schema()
