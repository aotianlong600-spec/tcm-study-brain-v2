import unittest

from scripts.validate_curated_batches import validate_all


class CuratedBatchAcceptanceTest(unittest.TestCase):
    def test_every_committed_batch_passes_the_acceptance_gate(self):
        count, errors = validate_all(accepted_only=True)
        self.assertGreater(count, 0)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
