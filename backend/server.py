"""Local Blindfastener API and frontend server. Run with Python 3.10+."""
import argparse
import json
import math
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import openpyxl

ROOT = Path(__file__).resolve().parents[1]


def norm(value):
    return str(value if value is not None else "").strip().casefold()


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


class Database:
    def __init__(self, path):
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            rows = list(book["Database"].values)
            self.headers = list(rows[1])
            if len(self.headers) < 80:
                raise ValueError("Database must include columns A through CB.")
            self.records = [list(r[:len(self.headers)]) + [None] * max(0, len(self.headers)-len(r))
                            for r in rows[2:] if r and r[0] is not None]
            galvanic_rows = list(book["Galvanic compatability"].values)[1:]
            self.galvanic = [list(r[:5]) for r in galvanic_rows if r and r[0] is not None]
            self.nut_galvanic = [list(r[6:12]) for r in galvanic_rows if len(r)>11 and r[6] is not None]
            self.pair_galvanic = [list(r[13:19]) for r in galvanic_rows if len(r)>18 and r[13] is not None]
            self.bonding_pair_galvanic = [list(r[33:39]) for r in galvanic_rows if len(r)>38 and r[33] is not None]
            self.bonding_galvanic = [list(r[20:25]) for r in galvanic_rows if len(r)>24 and r[20] is not None]
            self.bonding_nut_galvanic = [list(r[26:31]) for r in galvanic_rows if len(r)>30 and r[26] is not None]
        finally:
            book.close()
        self.by_part = {norm(r[0]): r for r in self.records}
        if len(self.by_part) != len(self.records):
            raise ValueError("Duplicate part numbers found in workbook.")
        # Both modes use CC/CD, optional CE/CF, and CG/CH with separate lookup tables.
        self.mapping_ready = True
        self.groups = [
            dict(id="materials", title="Materials, finishes & lubricants", start=9, end=26, columns="J–AA", theme="blue"),
            dict(id="dimensions", title="Dimensions & mass", start=30, end=65, columns="AE–BN", theme="green"),
            dict(id="marking", title="Marking", start=66, end=66, columns="BO", theme="neutral"),
            dict(id="specification", title="Technical specification", start=67, end=67, columns="BP", theme="neutral"),
            dict(id="strength", title="Strength & performance", start=68, end=79, columns="BQ–CB", theme="neutral", layout="rows"),
        ]
        self.labels = [str(h).strip() if h is not None and str(h).strip() else
                       "Column " + openpyxl.utils.get_column_letter(i+1)
                       for i, h in enumerate(self.headers)]
        for start, component in [(9, "Sleeve"), (12, "Stem / Core bolt"),
                                 (15, "Locking collar"), (18, "Nut"),
                                 (21, "Drive Nut"), (24, "Insert")]:
            for i in range(start, start+3):
                self.labels[i] = component + " · " + self.labels[i]

    def metadata(self):
        return dict(headers=self.headers, labels=self.labels, groups=self.groups,
                    count=len(self.records), mappingReady=self.mapping_ready,
                    partNumbers=sorted(str(r[0]) for r in self.records),
                    substrates=sorted({r[2] for r in self.galvanic+self.nut_galvanic+self.bonding_galvanic+self.bonding_nut_galvanic if r[2]}),
                    substrateFinishes=sorted({r[3] for r in self.nut_galvanic+self.bonding_nut_galvanic if r[3]}))

    def search(self, query):
        if query.get("mode", "part") != "part":
            raise ValueError("Only part-number search is supported.")
        key = norm(query.get("part"))
        if not key:
            raise ValueError("Enter a part number.")
        return [self.by_part[key]] if key in self.by_part else []

    def pair_compatibility(self, values, mode):
        result=dict(values=values, comments=[])
        if any(not norm(value) for value in values):
            return dict(result,status="missing_values",result="Missing fastener material or finish")
        table = self.bonding_pair_galvanic if mode == "yes" else self.pair_galvanic
        matches=[r for r in table if all(norm(r[i])==norm(value) for i,value in enumerate(values))]
        if not matches:
            return dict(result,status="no_match",result="No matching record")
        outcomes={norm(r[4]) for r in matches}
        result["comments"]=list(dict.fromkeys(str(r[5]) for r in matches if r[5] is not None))
        if len(outcomes)!=1 or not outcomes <= {"yes","no"}:
            return dict(result,status="conflict",result="Conflicting or unspecified results")
        return dict(result,status="matched",result=next(iter(outcomes)).capitalize())

    def compatibility(self, query):
        if not isinstance(query, dict):
            raise ValueError("Expected a JSON object.")
        part, mode, substrates = query.get("part"), query.get("mode"), query.get("substrates")
        if not isinstance(part, str) or not norm(part):
            raise ValueError("Select a part number.")
        if mode not in ("yes", "no"):
            raise ValueError("Select Yes or No.")
        if not isinstance(substrates, list) or not 1 <= len(substrates) <= 5:
            raise ValueError("Provide between one and five substrates.")
        for item in substrates:
            if not isinstance(item, dict) or any(not isinstance(item.get(k), str) or not norm(item[k]) for k in ("material", "finish")):
                raise ValueError("Select material and finish for every substrate.")
            if type(item.get("nutSide", False)) is not bool:
                raise ValueError("Nut or washer side must be a checkbox value.")
        row = self.by_part.get(norm(part))
        if row is None:
            return 404, dict(message="Fastener not found.")
        bolt_table = self.bonding_galvanic if mode == "yes" else self.galvanic
        nut_table = self.bonding_nut_galvanic if mode == "yes" else self.nut_galvanic
        results=[]
        def lookup(index, item, component, offset, table, use_finish):
            material = row[offset] if len(row)>offset else None
            finish = row[offset+1] if len(row)>offset+1 else None
            result=dict(substrateIndex=index+1, component=component, material=material,
                        finish=finish, substrate=item["material"], substrateFinish=item["finish"],
                        substrateFinishUsed=use_finish, comments=[])
            if not norm(material) or not norm(finish):
                return dict(result, status="missing_values", result="Missing fastener material or finish")
            keys=[material, finish, item["material"]]+([item["finish"]] if use_finish else [])
            matches=[r for r in table if all(norm(r[i])==norm(key) for i,key in enumerate(keys))]
            if not matches:
                return dict(result,status="no_match",result="No matching record")
            result_index=4 if use_finish else 3
            values={norm(r[result_index]) for r in matches}
            result["comments"]=list(dict.fromkeys(str(r[result_index+1]) for r in matches if len(r)>result_index+1 and r[result_index+1] is not None))
            if len(values)!=1 or not values <= {"yes","no"}:
                return dict(result,status="conflict",result="Conflicting or unspecified results")
            return dict(result,status="matched",result=next(iter(values)).capitalize())
        for index,item in enumerate(substrates):
            results.append(lookup(index,item,"Bolt / sleeve (CC, CD)",80,bolt_table,False))
            if item.get("nutSide",False):
                results.append(lookup(index,item,"Nut / washer side (CE, CF)",82,nut_table,True))
            results.append(lookup(index,item,"Additional component (CG, CH)",84,bolt_table,False))
        pair_result = self.pair_compatibility([row[i] if len(row)>i else None for i in (80,81,82,83)], mode)
        return 200, dict(status="complete",results=results,pairResult=pair_result)


def make_handler(database):
    class Handler(BaseHTTPRequestHandler):
        def send_body(self, code, body, content_type):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, code, payload):
            self.send_body(code, json.dumps(payload, ensure_ascii=True, allow_nan=False).encode(),
                           "application/json; charset=utf-8")

        def do_POST(self):
            if urlsplit(self.path).path != "/api/compatibility":
                self.send_json(404, dict(message="Not found."))
                return
            try:
                size=int(self.headers.get("Content-Length", "0"))
                if not 0<size<=16384:
                    raise ValueError("Invalid request size.")
                query=json.loads(self.rfile.read(size))
                self.send_json(*database.compatibility(query))
            except (ValueError, UnicodeError) as exc:
                self.send_json(400,dict(message=str(exc)))
            except Exception:
                self.log_error("Compatibility request failed")
                self.send_json(500,dict(message="Could not complete the compatibility check."))

        def do_GET(self):
            url = urlsplit(self.path)
            query = {k: v[0] for k, v in parse_qs(url.query, keep_blank_values=True).items()}
            try:
                if url.path == "/api/metadata":
                    self.send_json(200, database.metadata())
                elif url.path == "/api/fasteners":
                    self.send_json(200, dict(records=database.search(query)))
                elif url.path == "/api/compatibility":
                    self.send_json(405, dict(message="Use POST with substrate selections."))
                elif url.path in {"/", "/index.html", "/app.js", "/styles.css", "/display.js"}:
                    name = "index.html" if url.path == "/" else url.path[1:]
                    mime = {"index.html": "text/html", "app.js": "text/javascript",
                            "display.js": "text/javascript", "styles.css": "text/css"}[name]
                    self.send_body(200, (ROOT / "frontend" / name).read_bytes(), mime+"; charset=utf-8")
                else:
                    self.send_json(404, dict(message="Not found."))
            except ValueError as exc:
                self.send_json(400, dict(message=str(exc)))
            except Exception:
                self.log_error("Request failed")
                self.send_json(500, dict(message="The server could not complete the request."))
    return Handler


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", default=os.environ.get("BLINDFASTENER_WORKBOOK", str(ROOT / "data" / "blindfastener.xlsx")))
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    db = Database(args.workbook)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(db))
    print(f"Blindfastener: http://127.0.0.1:{args.port} ({len(db.records)} parts)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
