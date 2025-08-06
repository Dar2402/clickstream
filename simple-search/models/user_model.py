from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

BaseUser = declarative_base()

class User(BaseUser):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    bio = Column(String)
