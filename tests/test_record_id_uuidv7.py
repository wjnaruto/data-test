import uuid

from db.models import generate_record_id


def test_generate_record_id_is_uuid_v7_hex_string():
    rid = generate_record_id()
    assert isinstance(rid, str)
    assert len(rid) == 32
    u = uuid.UUID(hex=rid)
    assert u.version == 7

