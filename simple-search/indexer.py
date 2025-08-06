import os
from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, ID, TEXT
from sqlalchemy import event
from config import WHOOSH_INDEX_DIR

schema = Schema(
    doc_id=ID(stored=True, unique=True),
    doctype=ID(stored=True),
    title=TEXT(stored=True),
    content=TEXT(stored=True)
)

def get_or_create_index():
    if not os.path.exists(WHOOSH_INDEX_DIR):
        os.mkdir(WHOOSH_INDEX_DIR)
    if not exists_in(WHOOSH_INDEX_DIR):
        return create_in(WHOOSH_INDEX_DIR, schema)
    return open_dir(WHOOSH_INDEX_DIR)

ix = get_or_create_index()

def add_doc_to_index(doctype, doc_id, title, content):
    writer = ix.writer()
    writer.update_document(
        doc_id=f"{doctype}_{doc_id}",
        doctype=doctype,
        title=title,
        content=content
    )
    writer.commit()

def delete_doc_from_index(doctype, doc_id):
    writer = ix.writer()
    writer.delete_by_term('doc_id', f"{doctype}_{doc_id}")
    writer.commit()

def register_event_listeners(model, doctype, get_data_fn):
    @event.listens_for(model, "after_insert")
    def after_insert(mapper, connection, target):
        data = get_data_fn(target)
        add_doc_to_index(doctype, *data)

    @event.listens_for(model, "after_update")
    def after_update(mapper, connection, target):
        data = get_data_fn(target)
        add_doc_to_index(doctype, *data)

    @event.listens_for(model, "after_delete")
    def after_delete(mapper, connection, target):
        delete_doc_from_index(doctype, target.id)
