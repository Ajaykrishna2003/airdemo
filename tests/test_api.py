import importlib.util
import json
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("server", ROOT / "backend/server.py")
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class APITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = server.Database(ROOT / "data/blindfastener.xlsx")
        cls.http = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(cls.db))
        cls.worker = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.worker.start()
        cls.base = f"http://127.0.0.1:{cls.http.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.worker.join()

    def get(self, path):
        try:
            with urlopen(self.base + path) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)

    def test_metadata(self):
        status, data = self.get("/api/metadata")
        self.assertEqual(status, 200)
        self.assertEqual(data["count"], 2640)
        self.assertEqual(len(data["headers"]), 86)
        self.assertEqual([(g['start'],g['end']) for g in data['groups']], [(9,26),(30,65),(66,66),(67,67),(68,79)])
        self.assertEqual(data['groups'][4]['layout'], 'rows')
        self.assertEqual(data['labels'][9], 'Sleeve · Material')
        self.assertNotIn("records", data)
        self.assertTrue(data["mappingReady"])

    def test_search(self):
        status, data = self.get("/api/fasteners?mode=part&part=%20abs0546d402%20")
        self.assertEqual(status, 200)
        self.assertEqual(data["records"][0][0], "ABS0546D402")
        self.assertEqual(data['records'][0][1:3], ['Blind Rivet', 'A'])
        self.assertEqual(len(data['records'][0]), 86)
        self.assertEqual(self.get('/api/fasteners?mode=code&finish=d&diameter=04&grip=02')[0], 400)
        _, data = self.get("/api/fasteners?mode=part&part=UNKNOWN")
        self.assertEqual(data["records"], [])

    def test_bad_inputs(self):
        for path in ["/api/fasteners", "/api/fasteners?mode=invalid",
                     "/api/fasteners?mode=code&finish=D&diameter=nan&grip=2",
                     "/api/fasteners?mode=code&finish=D&diameter=4"]:
            self.assertEqual(self.get(path)[0], 400)

    def test_no_workbook_or_backend_exposure(self):
        for path in ["/data/blindfastener.xlsx", "/backend/server.py", "/../backend/server.py"]:
            self.assertEqual(self.get(path)[0], 404)
        for path in ["/", "/app.js", "/styles.css", "/display.js"]:
            with urlopen(self.base + path) as response:
                text = response.read().decode()
                self.assertEqual(response.status, 200)
                self.assertNotIn('id="workbook-data"', text)



if __name__ == "__main__":
    unittest.main()
