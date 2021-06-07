from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.schema import Column

Base = declarative_base()


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False)
    category = Column(String, ForeignKey="categories.id", nullable=False)
    price = Column(Integer, nullable=False)
    visiable = Column(Boolean, nullable=False)
    description = Column(String(128))

    @property
    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "price": self.price,
            "visiable": self.visiable,
            "description": self.description,
        }
