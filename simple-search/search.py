from whoosh.qparser import MultifieldParser
from indexer import ix

def search_all(query):
    with ix.searcher() as searcher:
        parser = MultifieldParser(["title", "content"], schema=ix.schema)
        q = parser.parse(query)
        results = searcher.search(q)
        return [
            {
                "doctype": r["doctype"],
                "doc_id": r["doc_id"],
                "title": r["title"],
                "content": r["content"]
            }
            for r in results
        ]
