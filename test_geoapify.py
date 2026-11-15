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
            get.assert_called_once()
            self.assertEqual(get.call_args.kwargs["params"]["limit"], 20)

    def test_two_full_pages_stop_at_cap_and_deduplicate(self):
        def response(ids):
            return Mock(status_code=200, **{"json.return_value": {
                "type": "FeatureCollection",
                "features": [{"properties": {"place_id": str(i)}} for i in ids],
            }})

        with tempfile.TemporaryDirectory() as tmp, patch.object(app, "ROOT", Path(tmp)), patch.dict(
            app.os.environ, {"GEOAPIFY_API_KEY": "test-only-secret"}
        ), patch.object(app.requests, "get", side_effect=[
            response(range(20)), response(range(19, 39))
        ]) as get, contextlib.redirect_stdout(io.StringIO()):
            app.main(max_pages=2)
            offsets = [call.kwargs["params"]["offset"] for call in get.call_args_list]
            self.assertEqual(offsets, [0, 20])
            data = json.loads((Path(tmp) / "data/geoapify_response.json").read_text())
            ids = [place["properties"]["place_id"] for place in data["features"]]
            self.assertEqual(ids, [str(i) for i in range(39)])

    def test_rate_limit_honors_retry_after(self):
        limited = Mock(status_code=429, headers={"Retry-After": "4"})
        success = Mock(status_code=200)
        with patch.object(app.requests, "get", side_effect=[limited, success]) as get, patch.object(
            app.time, "sleep"
        ) as sleep:
            self.assertIs(app.request_page({"offset": 20}), success)
            self.assertEqual(get.call_count, 2)
            self.assertEqual(get.call_args_list[0], get.call_args_list[1])
            sleep.assert_called_once_with(4)

    def test_server_failure_stops_after_three_attempts(self):
        unavailable = Mock(status_code=503, headers={})
        with patch.object(app.requests, "get", return_value=unavailable) as get, patch.object(
            app.time, "sleep"
        ) as sleep:
            with self.assertRaisesRegex(SystemExit, "503"):
                app.fetch_page({})
            self.assertEqual(get.call_count, 3)
            self.assertEqual([call.args[0] for call in sleep.call_args_list], [1, 2])


if __name__ == "__main__":
    unittest.main()
