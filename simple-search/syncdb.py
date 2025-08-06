def index_all_users(session):
    writer = ix.writer()
    for user in session.query(User).all():
        add_doc_to_index(writer, "user", user.id, user.name, user.bio)
    writer.commit()

def index_all_products(session):
    writer = ix.writer()
    for product in session.query(Product).all():
        add_doc_to_index(writer, "product", product.id, product.name, product.description)
    writer.commit()

def index_all_reviews(session):
    writer = ix.writer()
    for review in session.query(Review).all():
        add_doc_to_index(writer, "review", review.id, review.title, review.body)
    writer.commit()


def register_listeners_for_model(model, doctype):

    @event.listens_for(model, "after_insert")
    def after_insert(mapper, connection, target):
        writer = ix.writer()
        if doctype == "user":
            writer.update_document(
                doc_id=f"user_{target.id}", doctype="user",
                title=target.name, content=target.bio)
        elif doctype == "product":
            writer.update_document(
                doc_id=f"product_{target.id}", doctype="product",
                title=target.name, content=target.description)
        elif doctype == "review":
            writer.update_document(
                doc_id=f"review_{target.id}", doctype="review",
                title=target.title, content=target.body)
        writer.commit()

    @event.listens_for(model, "after_update")
    def after_update(mapper, connection, target):
        # Same as insert — update the index
        after_insert(mapper, connection, target)

    @event.listens_for(model, "after_delete")
    def after_delete(mapper, connection, target):
        writer = ix.writer()
        writer.delete_by_term('doc_id', f"{doctype}_{target.id}")
        writer.commit()

# Register listeners
register_listeners_for_model(User, "user")
register_listeners_for_model(Product, "product")
register_listeners_for_model(Review, "review")


def initialize_all():
    # Create tables if not exist
    BaseUser.metadata.create_all(engine_user)
    BaseProduct.metadata.create_all(engine_product)
    BaseReview.metadata.create_all(engine_review)

    # Initial full indexing
    index_all_users(SessionUser())
    index_all_products(SessionProduct())
    index_all_reviews(SessionReview())

initialize_all()
