"""Tiny document store on Turso/libSQL, via the plain HTTP API. Mimics the small part of the pymongo API used by the app."""
import base64
import json
import re
import threading
import requests


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


def _to_arg(v):
    if v is None:
        return {"type": "null"}
    if isinstance(v, bool):
        return {"type": "integer", "value": str(int(v))}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": v}
    if isinstance(v, bytes):
        return {"type": "blob", "base64": base64.b64encode(v).decode()}
    return {"type": "text", "value": str(v)}


def _from_cell(cell):
    t = cell.get("type")
    if t == "null":
        return None
    if t == "integer":
        return int(cell["value"])
    if t == "float":
        return float(cell["value"])
    if t == "blob":
        return base64.b64decode(cell.get("base64", ""))
    return cell.get("value")


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
        rows = self.db._query("SELECT rowid, data FROM docs WHERE col = ?", [self.name])
        return [(r[0], d) for r, d in ((row, json.loads(row[1])) for row in rows) if _matches(d, flt)]

    def _save(self, rid, doc):
        self.db._exec("UPDATE docs SET data = ? WHERE rowid = ?", [json.dumps(doc), rid])

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
            self.db._batch([("INSERT INTO docs (col, data) VALUES (?, ?)", [self.name, json.dumps(d)]) for d in docs])

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
            if not rows:
                return
            targets = rows if many else rows[:1]
            self.db._batch([("DELETE FROM docs WHERE rowid = ?", [rid]) for rid, _ in targets])

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
        base = url.strip().replace("libsql://", "https://").rstrip("/")
        self.pipeline_url = base + "/v2/pipeline"
        self.auth_token = auth_token.strip() if auth_token else auth_token
        self.lock = threading.RLock()
        self._pipeline([
            ("CREATE TABLE IF NOT EXISTS docs (col TEXT NOT NULL, data TEXT NOT NULL)", None),
            ("CREATE INDEX IF NOT EXISTS docs_col ON docs (col)", None),
        ])

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.auth_token:
            h["Authorization"] = f"Bearer {self.auth_token}"
        return h

    def _pipeline(self, stmts):
        body = {"requests": []}
        for sql, args in stmts:
            stmt = {"sql": sql}
            if args:
                stmt["args"] = [_to_arg(a) for a in args]
            body["requests"].append({"type": "execute", "stmt": stmt})
        body["requests"].append({"type": "close"})

        resp = requests.post(self.pipeline_url, json=body, headers=self._headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data["results"][:-1]:  # last entry is the "close" ack
            if item["type"] == "error":
                raise RuntimeError(item["error"].get("message", "Turso query failed"))
            result = item["response"]["result"]
            rows = [[_from_cell(c) for c in row] for row in result.get("rows", [])]
            results.append(rows)
        return results

    def _exec(self, sql, args=None):
        self._pipeline([(sql, args)])

    def _query(self, sql, args=None):
        return self._pipeline([(sql, args)])[0]

    def _batch(self, stmts):
        if stmts:
            self._pipeline(stmts)

    def __getitem__(self, name):
        return Collection(self, name)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return Collection(self, name)
