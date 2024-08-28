import os
import psycopg2
from psycopg2 import sql

# Get environment variables for database credentials
db_name = os.getenv("POSTGRES_DB")
db_user = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PASSWORD")
db_host = os.getenv("POSTGRES_HOST", "localhost")  # default is localhost

# Database connection string
conn_str = f"dbname={db_name} user={db_user} password={db_password} host={db_host}"

def create_table():
    # SQL query to create the 'robots' table
    create_table_query = """
    CREATE TABLE IF NOT EXISTS test_robots (
        uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        robot_name VARCHAR(100),
        bag_name VARCHAR(10000),
        mileage REAL,
        data_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()

        # Execute the table creation query
        cur.execute(create_table_query)
        conn.commit()

        # Insert initial records (if needed)
        cur.execute("""
        INSERT INTO test_robots (robot_name, bag_name, mileage) 
        VALUES ('robot1', 'bag1', 100)
        ON CONFLICT DO NOTHING;
        """)
        conn.commit()

        print("Table created and initial data inserted.")
        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error creating table: {e}")

if __name__ == "__main__":
    create_table()
