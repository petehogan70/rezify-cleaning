import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from backend.tables import sessions_table, sessions_data_table

"""
database.py contains the credentials and functions to connect to the Heroku PostgresSQL database. It creates a 
Session that can be used to query and make changes to teh database. This Session should be imported into other files.
Any function to do with the sessions table should be in this file.

Any new functions or updates to the database or sessions table should be added here.
"""

sessions_name = sessions_table
sessions_data_name = sessions_data_table

load_dotenv()

# Initialize database connection to postgress database in heroku
DATABASE_URL = os.getenv('SQL_DATABASE_URL')
engine = create_engine(DATABASE_URL, pool_size=30, max_overflow=35, pool_pre_ping=True)
# IMPORTANT: READ
# (Optional): Replace DATABASE_URL with 'sqlite:////tmp/session.db' when running locally to save money and data space
# BEFORE PUSHING - MAKE SURE TO USE SQL_ DATABASE_URL
Session = scoped_session(sessionmaker(bind=engine))