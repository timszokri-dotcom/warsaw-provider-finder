"""Offline checks: no API key or credits needed."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import fetch_geoapify as app


class GeoapifyTests(unittest.TestCase):
    def test_missing_key_makes_no_request(self):
        with patch.dict(app.os.environ, {}, clear=True), patch.object(app.requests, "get") as get:
            with self.assertRaises(SystemExit):
                app.main()
            get.assert_not_called()

    def test_transport_error_does_not_expose_key(self):
        with patch.dict(app.os.environ, {"GEOAPIFY_API_KEY": "test-only-secret"}), patch.object(
            app.requests, "get", side_effect=app.requests.RequestException("test-only-secret")
        ):
            with self.assertRaises(SystemExit) as error:
                app.main()
            self.assertNotIn("test-only-secret", str(error.exception))

    def test_http_error_does_not_save_output(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(app, "ROOT", Path(tmp)), patch.dict(
            app.os.environ, {"GEOAPIFY_API_KEY": "test-only-secret"}
        ), patch.object(app.requests, "get", return_value=Mock(status_code=401)):
            with self.assertRaises(SystemExit) as error:
                app.main()
            self.assertIn("401", str(error.exception))
            self.assertFalse((Path(tmp) / "data").exists())

    def test_success_saves_json_and_prints_names(self):
        payload = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {"name": "Example garage"}}
        ]}
        response = Mock(status_code=200)
        response.json.return_value = payload
        with tempfile.TemporaryDirectory() as tmp, patch.object(app, "ROOT", Path(tmp)), patch.dict(
            app.os.environ, {"GEOAPIFY_API_KEY": "test-only-secret"}
        ), patch.object(app.requests, "get", return_value=response) as get:
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                app.main()
            self.assertIn("Example garage", stdout.getvalue())
            self.assertNotIn("test-only-secret", stdout.getvalue())
            self.assertEqual(json.loads((Path(tmp) / "data/geoapify_response.json").read_text()), payload)
            self.assertEqual(get.call_args.kwargs["params"]["limit"], 20)


if __name__ == "__main__":
    unittest.main()
