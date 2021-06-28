from io import BytesIO
from typing import Any, Dict, Iterable, List, Optional, Union

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import aws
from models import Base, Category, Item, Picture


def create_engine(dialect: str,
                  password: str,
                  host: str,
                  username: str,
                  port: Union[str, int],
                  dbname: str,
                  driver: str = "",
                  echo: Optional[bool] = None):
    if driver != "":
        driver = "+" + driver
    url = f"{dialect}{driver}://{username}:{password}@{host}:{port}/{dbname}"
    return sqlalchemy.create_engine(url, echo=echo)


def initialize(engine, categories: Dict[str, int]) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    sess = session(engine)
    for k, v in categories.items():
        category = Category()
        category.id = v
        category.name = k
        sess.add(category)
    sess.commit()


def session(engine):
    return sessionmaker(bind=engine)()


def post_item(
    sess,
    data: Dict[str, Union[bytes, Dict[str, bytes]]],
    aws_config: Dict[str, str],
):
    pictures = tuple(
        filter(lambda x: x["filename"] != "",
               map(lambda i: data[f"img_file[{i}]"], range(3))))
    n_pictures = len(pictures)
    category_id = int(data["category"])
    # store item
    item = Item()
    item.name = str(data["name"], "utf-8")
    item.category = category_id
    item.price = int(data["price"])
    item.visiable = True
    item.n_pictures = n_pictures
    item.description = str(data["description"], "utf-8")

    sess.add(item)
    sess.flush()

    s3 = aws.load_resource(
        name="s3",
        access_id=aws_config["access_id"],
        access_key=aws_config["access_key"],
        region_name=aws_config["region"],
    )
    bucket = s3.Bucket(aws_config["bucket_name"])
    # count_ = sqlalchemy.func.count("*")
    # n_item = sess.query(Item, count_).first()
    n_item = item.id
    for i, pic in enumerate(pictures):
        filename = f"{category_id}_{n_item}.{pic['filename'].split('.')[-1]}"
        with BytesIO() as received:
            received.write(pic["content"])
            received.seek(0)
            bucket.upload_fileobj(received, filename)
        picture = Picture()
        picture.url = f"https://{aws_config['bucket_name']}.s3.{aws_config['region']}.amazonaws.com/{filename}"
        picture.item_id = item.id
        sess.add(picture)
    sess.commit()


def update_item(
    sess,
    id: int,
    data: Dict[str, Union[int, bytes, Dict[str, bytes]]],
    aws_config: Dict[str, str],
):
    item = sess.query(Item).filter(Item.id == id).first()
    category_id = int(data["category"])

    item.name = str(data["name"], "utf-8")
    item.category = category_id
    item.price = int(data["price"])
    item.visiable = str(data["name"], "utf-8") == "true"
    item.description = str(data["description"], "utf-8")
    sess.commit()
