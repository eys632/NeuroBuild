"""Five new pure saved-metadata controls; no corpus/native/producer execution."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path('/home/a202192020/NeuroBuild_v2')
PRODUCER = ROOT / 'var/research/produce_gemma12_cpu_carry_forward.py'
PRODUCER_SHA = '4653f4e09a6d52bb9d04a6d3d2579bdd6d3d12c1588289d0465e7717ad227281'


class SavedMetadataControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if hashlib.sha256(PRODUCER.read_bytes()).hexdigest() != PRODUCER_SHA:
            raise RuntimeError('PRODUCER_PIN_CHANGED')
        spec = importlib.util.spec_from_file_location('gemma12_saved_carry', PRODUCER)
        cls.producer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.producer)
        cls.documents = {}
        for key, (relative, pin) in cls.producer.REFS.items():
            if key not in ('tokenizer_fixture', 'historical_cpp'):
                cls.documents[key] = json.loads(cls.producer.read_bound(relative, pin))

    def test_01_pinned_saved_metadata_baseline(self):
        self.producer.validate_saved(copy.deepcopy(self.documents))

    def test_02_new_header_comparison_link_tamper(self):
        docs = copy.deepcopy(self.documents)
        docs['tokenizer_comparison']['new_header_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, '^COMPARISON_HEADER_LINK$'):
            self.producer.validate_saved(docs)

    def test_03_hidden_typed_tokenizer_difference(self):
        docs = copy.deepcopy(self.documents)
        docs['new_header']['header']['metadata']['tokenizer.ggml.add_space_prefix']['value'] = True
        with self.assertRaisesRegex(ValueError, '^TOKENIZER_TYPED_VALUES$'):
            self.producer.validate_saved(docs)

    def test_04_false_complete_sampling_equivalence(self):
        docs = copy.deepcopy(self.documents)
        docs['tokenizer_comparison']['sampling_difference']['complete_effective_sampling_equivalent'] = True
        with self.assertRaisesRegex(ValueError, '^SAMPLING_FALSE_EQUIVALENCE$'):
            self.producer.validate_saved(docs)

    def test_05_historical_counts_tampered_in_both_linked_records(self):
        docs = copy.deepcopy(self.documents)
        # Matching false counts in both linked records must still fail the
        # fixed historical denominator, not merely a cross-record comparison.
        for name in ('vocab_context', 'historical_aggregate'):
            docs[name]['splits']['exposed120']['input_count'] = 119
        with self.assertRaisesRegex(ValueError, '^CONTEXT_COUNTS$'):
            self.producer.validate_saved(docs)


if __name__ == '__main__':
    unittest.main(verbosity=2)
