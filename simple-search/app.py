from flask import Flask, request, render_template
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import USER_DB, PRODUCT_DB, REVIEW_DB
from models.user_model import BaseUser, User
from models.product_model import BaseProduct, Product
from models.review_model import BaseReview, Review
from indexer import register_event_listeners
from search import search_all

app = Flask(__name__)

# -----------------------------
# DB Connections
# -----------------------------
engine_user = create_engine(USER_DB)
engine_product = create_engine(PRODUCT_DB)
engine_review = create_engine(REVIEW_DB)

SessionUser = sessionmaker(bind=engine_user)
SessionProduct = sessionmaker(bind=engine_product)
SessionReview = sessionmaker(bind=engine_review)

# -----------------------------
# Create Tables
# -----------------------------
BaseUser.metadata.create_all(engine_user)
BaseProduct.metadata.create_all(engine_product)
BaseReview.metadata.create_all(engine_review)

# -----------------------------
# Register Whoosh Listeners
# -----------------------------
register_event_listeners(User, "user", lambda u: (u.id, u.name, u.bio))
register_event_listeners(Product, "product", lambda p: (p.id, p.name, p.description))
register_event_listeners(Review, "review", lambda r: (r.id, r.title, r.body))

# -----------------------------
# Routes
# -----------------------------
@app.route("/", methods=["GET"])
def home():
    return render_template("search.html")

@app.route("/search", methods=["POST"])
def search():
    query = request.form.get("query", "")
    results = search_all(query)
    return render_template("results.html", query=query, results=results)
