import os
import tempfile
import unittest
from pathlib import Path

from nblog.publisher import PublishError, check_rate_limit, mark_published


class RateLimitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["NBLOG_DATA_DIR"] = str(Path(self.tmp.name) / "data")
        os.environ["NBLOG_MIN_PUBLISH_HOURS"] = "6"

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("NBLOG_DATA_DIR", None)
        os.environ.pop("NBLOG_MIN_PUBLISH_HOURS", None)

    def test_blocks_inside_window(self):
        check_rate_limit()
        mark_published()
        with self.assertRaises(PublishError):
            check_rate_limit()


if __name__ == "__main__":
    unittest.main()
