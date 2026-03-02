"""
Stubs for packages not installed in the test environment.
Import this FIRST before any project imports in each test file.
"""
import sys
from unittest.mock import MagicMock

def install_all_stubs():
    def _stub(name, **attrs):
        mod = MagicMock()
        for k, v in attrs.items():
            setattr(mod, k, v)
        sys.modules.setdefault(name, mod)
        return sys.modules[name]

    # boto3 + botocore (ClientError must be a real Exception so except catches it)
    class _ClientError(Exception):
        def __init__(self, error_response, operation_name):
            self.response = error_response
            super().__init__(f"{operation_name}: {error_response}")

    _stub("botocore")
    _stub("botocore.exceptions", ClientError=_ClientError)
    sys.modules["botocore.exceptions"].ClientError = _ClientError

    boto3_mod = _stub("boto3")
    _stub("boto3.dynamodb")
    cond_mod = _stub("boto3.dynamodb.conditions")
    cond_mod.Key = MagicMock(return_value=MagicMock())

    # twilio
    _stub("twilio"); _stub("twilio.rest", Client=MagicMock); _stub("twilio.http"); _stub("twilio.http.http_client")

    # sarvamai
    _stub("sarvamai", SarvamAI=MagicMock)

    # pinecone
    _stub("pinecone", Pinecone=MagicMock)

    # rapidfuzz — provide real-ish fuzzy logic so mismatch tests pass
    from difflib import SequenceMatcher
    fuzz_mod = MagicMock()
    def _tsr(a, b):
        wa, wb = set(str(a).lower().split()), set(str(b).lower().split())
        if not wa or not wb: return 0
        iou = len(wa & wb) / len(wa | wb) * 100
        char = SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio() * 100
        return round(max(iou, char))
    fuzz_mod.token_sort_ratio = _tsr
    rfuzz = MagicMock(); rfuzz.fuzz = fuzz_mod
    sys.modules["rapidfuzz"] = rfuzz
    sys.modules["rapidfuzz.fuzz"] = fuzz_mod

    # pydub
    _stub("pydub"); _stub("pydub.silence")

    # sentence_transformers (replaced by Titan, just stub)
    _stub("sentence_transformers", SentenceTransformer=MagicMock)

    # requests
    _stub("requests")

install_all_stubs()