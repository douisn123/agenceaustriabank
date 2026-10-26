"""Tiny document store on Turso/libSQL. Mimics the small part of the pymongo API used by the app."""
import json
import re
import threading
import libsql_client


class ReturnDocument:
    BEFORE, AFTER = False, True


def _get(doc, key):
    for part in key.split("."):
        doc = doc.get(part) if isinstance(doc, dict) else None
    return doc


def _match_value(val, cond):
    if isinstance(cond, dict) and any(k.startswith("$") for k in cond):
        for op, arg in cond.items():
            if op == "$regex":
                flags = re.I if "i" in cond.get("$options", "") else 0
                if not isinstance(val, str) or not re.search(arg, val, flags):
                    return False
            elif op == "$options":
                continue
            elif op == "$in":
                if val not in arg:
                    return False
            elif val is None:
                return False
            elif op == "$gt" and not val > arg:
                return False
            elif op == "$gte" and not val >= arg:
                return False
            elif op == "$lt" and not val < arg:
                return False
            elif op == "$lte" and not val <= arg:
                return False
        return True
    return val == cond


def _matches(doc, flt):
    for key, cond in (flt or {}).items():
        if key == "$or":
            if not any(_matches(doc, sub) for sub in cond):
                return False
        elif not _match_value(_get(doc, key), cond):
            return False
    return True


def _project(doc, projection):
    hidden = {k for k, v in (projection or {}).items() if not v}
    return {k: v for k, v in doc.items() if k not in hidden}


def _apply(doc, update):
    for k, v in update.get("$set", {}).items():
        doc[k] = v
    for k, v in update.get("$inc", {}).items():
        doc[k] = doc.get(k, 0) + v
    return doc


class Cursor:
    def __init__(self, docs):
        self._docs = docs

    def sort(self, key, direction=1):
        self._docs.sort(key=lambda d: (d.get(key) is None, d.get(key)), reverse=direction < 0)
        return self

    def limit(self, n):
        self._docs = self._docs[:n] if n else self._docs
        return self

    def __iter__(self):
        return iter(self._docs)


class Collection:
    def __init__(self, db, name):
        self.db, self.name = db, name

    def _rows(self, flt=None):
        rs = self.db.client.execute("SELECT rowid, data FROM docs WHERE col = ?", [self.name])
        return [(row[0], d) for row, d in ((r, json.loads(r[1])) for r in rs.rows) if _matches(d, flt)]

    def _save(self, rid, doc):
        self.db.client.execute("UPDATE docs SET data = ? WHERE rowid = ?", [json.dumps(doc), rid])

    def find(self, flt=None, projection=None):
        with self.db.lock:
            return Cursor([_project(d, projection) for _, d in self._rows(flt)])

    def find_one(self, flt=None, projection=None):
        return next(iter(self.find(flt, projection)), None)

    def insert_one(self, doc):
        self.insert_many([doc])

    def insert_many(self, docs):
        if not docs:
            return
        with self.db.lock:
            self.db.client.batch([
                ("INSERT INTO docs (col, data) VALUES (?, ?)", [self.name, json.dumps(d)]) for d in docs
            ])

    def _update(self, flt, update, many):
        with self.db.lock:
            rows = self._rows(flt)
            for rid, d in rows if many else rows[:1]:
                self._save(rid, _apply(d, update))

    def update_one(self, flt, update):
        self._update(flt, update, False)

    def update_many(self, flt, update):
        self._update(flt, update, True)

    def find_one_and_update(self, flt, update, projection=None, return_document=ReturnDocument.BEFORE):
        with self.db.lock:
            rows = self._rows(flt)
            if not rows:
                return None
            rid, d = rows[0]
            before = dict(d)
            self._save(rid, _apply(d, update))
            return _project(d if return_document else before, projection)

    def _delete(self, flt, many):
        with self.db.lock:
            rows = self._rows(flt)
            for rid, _ in rows if many else rows[:1]:
                self.db.client.execute("DELETE FROM docs WHERE rowid = ?", [rid])

    def delete_one(self, flt):
        self._delete(flt, False)

    def delete_many(self, flt):
        self._delete(flt, True)

    def count_documents(self, flt):
        with self.db.lock:
            return len(self._rows(flt))

    def distinct(self, field, flt=None):
        out = []
        for d in self.find(flt):
            v = _get(d, field)
            if v not in out:
                out.append(v)
        return out

    def aggregate(self, pipeline):
        docs = list(self.find())
        for stage in pipeline:
            if "$match" in stage:
                docs = [d for d in docs if _matches(d, stage["$match"])]
            elif "$group" in stage:
                spec = stage["$group"]
                if not docs:
                    return []
                out = {"_id": None}
                for name, acc in spec.items():
                    if name != "_id":
                        out[name] = sum(_get(d, acc["$sum"].lstrip("$")) or 0 for d in docs)
                docs = [out]
        return docs


class Database:
    def __init__(self, url, auth_token=None):
        self.client = libsql_client.create_client_sync(url, auth_token=auth_token)
        self.client.execute("CREATE TABLE IF NOT EXISTS docs (col TEXT NOT NULL, data TEXT NOT NULL)")
        self.client.execute("CREATE INDEX IF NOT EXISTS docs_col ON docs (col)")
        self.lock = threading.RLock()

    def __getitem__(self, name):
        return Collection(self, name)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return Collection(self, name)
