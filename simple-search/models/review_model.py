from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

BaseReview = declarative_base()

class Review(BaseReview):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    body = Column(String)
