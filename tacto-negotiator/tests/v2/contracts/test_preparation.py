import json

import pytest

from tests.v2.support import inputs, require


def codec_and_data(request, p10):
    codec = require(request, "evidence.prepare").PreparedArtifactCodec()
    return codec, inputs(request, p10)


def decode(codec, data, blob, **overrides):
    arguments = {
        "expected_base_hash": data.prepared.base_manifest.content_hash,
        "expected_release_hash": (data.prepared.release_manifest.content_hash
                                  if data.prepared.release_manifest else None),
        "expected_parser_versions": data.prepared.parser_versions,
    }
    return codec.decode(blob, **{**arguments, **overrides})


def test_prepared_artifact_roundtrip_and_warm_context_match(request, p10):
    codec, data = codec_and_data(request, p10)
    encoded = codec.encode(data.prepared)
    restored = decode(codec, data, encoded)
    assert restored == data.prepared
    builder = require(request, "evidence.context").LayeredContextBuilder()
    cold = builder.build_context(data.prepared, data.case, data.server, data.documents, data.as_of)
    warm = builder.build_context(restored, data.case, data.server, data.documents, data.as_of)
    assert warm == cold


@pytest.mark.parametrize("fault", ["base", "release", "parser", "corrupt_json", "changed_record"])
def test_prepared_artifact_rejects_mismatch_instead_of_rebuilding_silently(request, p10, fault):
    codec, data = codec_and_data(request, p10)
    encoded = codec.encode(data.prepared)
    overrides = {}
    if fault in {"base", "release"}:
        overrides["expected_" + fault + "_hash"] = "0" * 64
    elif fault == "parser":
        overrides["expected_parser_versions"] = ("unsupported-parser/999",)
    elif fault == "corrupt_json":
        encoded = b"{"
    else:
        raw = json.loads(encoded)
        raw["records"][0]["canonical_id"] = "cost:tampered"
        encoded = json.dumps(raw).encode()
    with pytest.raises(ValueError):
        decode(codec, data, encoded, **overrides)
