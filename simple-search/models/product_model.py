from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

BaseProduct = declarative_base()

class Product(BaseProduct):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
