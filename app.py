import os
import sys
from pathlib import Path

import responder
import yaml

import db
import models

api = responder.API(secret_key=os.environ["SECRET_KEY"])
engine = db.create_engine(dialect="postgresql",
                          password=os.environ["DBPASS"],
                          host=os.environ["HOST"],
                          username=os.environ["DBUSER"],
                          port=os.environ["PORT"],
                          dbname=os.environ["DBNAME"])

project_root = Path(__file__).resolve().parent
with open(str(project_root / "categories.yml")) as f:
    category_list = {k: i for i, k in enumerate(yaml.safe_load(f))}

aws_config = {
    "access_id": os.environ["AWS_ACCESS_ID"],
    "access_key": os.environ["AWS_ACCESS_KEY"],
    "region": os.environ["AWS_REGION"],
    "bucket_name": os.environ["AWS_BUCKET_NAME"],
}


def is_authenticated(username: str, password: str) -> bool:
    return username == os.environ["USERNAME"] and password == os.environ["PASSWORD"]


@api.route(before_request=True)
def prepare(req, resp):
    if req.url.path.startswith("/static/"):
        return
    if req.url.path == "/" or req.url.path == "/login":
        return
    if req.session.get("username", None) is not None:
        return
    api.redirect(resp, "/login")


@api.route("/")
async def login(req, resp):
    api.redirect(resp, "/login")


@api.route("/login")
class Login:
    async def on_get(self, req, resp):
        resp.content = api.template("login.html", login_url=api.url_for("Login"))

    async def on_post(self, req, resp):
        data = await req.media()
        username = data.get("username")
        password = data.get("password")
        if not is_authenticated(username, password):
            errmsg = ["invalid username or password"]
            resp.content = api.template("login.html", errmessages=errmsg)
            return
        resp.session["username"] = username
        api.redirect(resp, "/items")


@api.route("/items")
def items(req, resp):
    session = db.session(engine)
    resp.content = api.template("userpage.html",
                                name=req.session["username"],
                                logout_url=api.url_for("delete_session"))


@api.route("/items/{id:int}")
class Item:
    async def on_get(self, req, resp, *, id):
        session = db.session(engine)
        item = session.query(models.Item).filter(models.Item.id == id).first()
        images = session.query(
            models.Picture).filter(models.Picture.item_id == id).all()
        print(f"{item=}", f"{images=}")
        resp.content = api.template("item.html",
                                    item=item,
                                    images=images,
                                    category=category_list)

    async def on_post(self, req, resp, *, id: int):
        data = await req.media(format="files")
        print(data)
        if str(data["_method"], "utf-8") == "put":

            @api.background.task
            def update_data(item_id, d, config):
                db.update_item(db.session(engine), item_id, d, config)

            update_data(id, data,aws_config)
            resp.text = "update now"
        else:
            api.redirect(resp, f"/items/{id}")


@api.route("/category/{id}")
async def categories(req, resp, *, id):
    session = db.session(engine)
    cats = session.query(models.Item).filter(models.Item.category == id).all()


@api.route("/deleteSession")
async def delete_session(req, resp):
    del resp.session["username"]
    api.redirect(resp, "/login")


@api.route("/post")
class Post:
    async def on_get(self, req, resp):
        resp.content = api.template("image_post.html", category=category_list)
        # post page
    async def on_post(self, req, resp):
        # store S3
        data = await req.media(format="files")

        @api.background.task
        def store_data(d, config):
            db.post_item(db.session(engine), d, config)

        store_data(data, aws_config)
        resp.text = "store now"


if __name__ == "__main__":
    if sys.argv[-1] != "noinit":
        db.initialize(engine, category_list)
    api.run()
