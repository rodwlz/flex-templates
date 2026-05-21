"""AbstractRepository[T] CRUD contract.

Read this file as the spec for what every repository in the project does:

    get(id)           -> T | None
    list(**filters)   -> list[T]            (equality filters by field name)
    create(data)      -> T                  (id is set after flush)
    update(id, data)  -> T | None           (None means id not found)
    delete(id)        -> bool               (False means id not found)

UserRepository in tests/test_repositories.py exercises the same contract
through a real domain model. Here we use a minimal Pet model so the contract
is the only thing on the page.
"""
import pytest
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from lib.database.session import SessionFactory
from lib.repositories.base import AbstractRepository


# ── A minimal model defined just for these tests ──────────────────────────
# Using its own DeclarativeBase keeps it isolated from the application's
# lib.database.base.Base — no risk of leaking the table into other tests.
class _Base(DeclarativeBase):
    pass


class Pet(_Base):
    __tablename__ = "pets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String)
    species: Mapped[str] = mapped_column(String)


class PetRepository(AbstractRepository[Pet]):
    model = Pet


@pytest.fixture
def repo():
    factory = SessionFactory("sqlite:///:memory:")
    factory.create_tables(_Base)
    return PetRepository(factory)


# ── create() ──────────────────────────────────────────────────────────────

def test_create_returns_object_with_id_populated(repo):
    pet = repo.create({"name": "Mochi", "species": "cat"})
    assert pet.id is not None
    assert pet.name == "Mochi"


def test_create_persists_for_subsequent_reads(repo):
    repo.create({"name": "Rex", "species": "dog"})
    found = repo.list(name="Rex")
    assert len(found) == 1


# ── get() ─────────────────────────────────────────────────────────────────

def test_get_returns_object_when_id_exists(repo):
    pet = repo.create({"name": "Whiskers", "species": "cat"})
    assert repo.get(pet.id).name == "Whiskers"


def test_get_returns_none_when_id_missing(repo):
    assert repo.get(99999) is None


# ── list() ────────────────────────────────────────────────────────────────

def test_list_returns_all_when_no_filters(repo):
    repo.create({"name": "A", "species": "cat"})
    repo.create({"name": "B", "species": "dog"})
    assert len(repo.list()) == 2


def test_list_filters_by_field_equality(repo):
    repo.create({"name": "A", "species": "cat"})
    repo.create({"name": "B", "species": "cat"})
    repo.create({"name": "C", "species": "dog"})
    cats = repo.list(species="cat")
    assert {p.name for p in cats} == {"A", "B"}


def test_list_supports_multiple_filters(repo):
    repo.create({"name": "A", "species": "cat"})
    repo.create({"name": "B", "species": "cat"})
    result = repo.list(species="cat", name="A")
    assert len(result) == 1
    assert result[0].name == "A"


def test_list_returns_empty_when_no_matches(repo):
    repo.create({"name": "A", "species": "cat"})
    assert repo.list(species="fish") == []


# ── update() ──────────────────────────────────────────────────────────────

def test_update_modifies_fields_and_returns_object(repo):
    pet = repo.create({"name": "Buddy", "species": "dog"})
    updated = repo.update(pet.id, {"name": "Buddy II"})
    assert updated.name == "Buddy II"
    # Persisted on the next read.
    assert repo.get(pet.id).name == "Buddy II"


def test_update_returns_none_when_id_missing(repo):
    assert repo.update(99999, {"name": "ghost"}) is None


# ── delete() ──────────────────────────────────────────────────────────────

def test_delete_returns_true_and_removes_when_found(repo):
    pet = repo.create({"name": "Goner", "species": "cat"})
    assert repo.delete(pet.id) is True
    assert repo.get(pet.id) is None


def test_delete_returns_false_when_id_missing(repo):
    assert repo.delete(99999) is False


# ── paginate() ────────────────────────────────────────────────────────────────

def test_paginate_returns_correct_structure(repo):
    for i in range(5):
        repo.create({"name": f"pgpet{i}", "species": f"species{i}"})
    result = repo.paginate(page=1, page_size=2)
    assert result["total"] == 5
    assert result["pages"] == 3
    assert result["page"] == 1
    assert result["page_size"] == 2
    assert len(result["items"]) == 2


def test_paginate_last_page_has_remainder(repo):
    for i in range(5):
        repo.create({"name": f"pgpet2_{i}", "species": f"species{i}"})
    result = repo.paginate(page=3, page_size=2)
    assert len(result["items"]) == 1  # 5 items, pages: [2, 2, 1]


def test_paginate_page_beyond_total_returns_empty(repo):
    repo.create({"name": "pgpet3_0", "species": "species0"})
    result = repo.paginate(page=10, page_size=20)
    assert result["items"] == []
    assert result["total"] == 1


def test_paginate_with_filter(repo):
    repo.create({"name": "pgactive1", "species": "active"})
    repo.create({"name": "pgactive2", "species": "suspended"})
    result = repo.paginate(page=1, page_size=10, species="active")
    assert result["total"] == 1
    assert result["items"][0]["name"] == "pgactive1"


# ── filter_by() ───────────────────────────────────────────────────────────────

def test_filter_by_exact_match(db_factory):
    from lib.repositories.user_repository import UserRepository
    repo = UserRepository(db_factory)
    repo.create({"username": "fb_alice", "email": "fb_alice@test.com",
                 "password_hash": "", "salt": ""})
    repo.create({"username": "fb_bob", "email": "fb_bob@test.com",
                 "password_hash": "", "salt": ""})
    results = repo.filter_by(username="fb_alice")
    assert len(results) == 1
    assert results[0]["username"] == "fb_alice"


def test_filter_by_like(db_factory):
    from lib.repositories.user_repository import UserRepository
    repo = UserRepository(db_factory)
    repo.create({"username": "fb_carol", "email": "fb_carol@test.com",
                 "password_hash": "", "salt": ""})
    repo.create({"username": "fb_dave", "email": "fb_dave@test.com",
                 "password_hash": "", "salt": ""})
    results = repo.filter_by(username__like="fb_c%")
    assert len(results) == 1
    assert results[0]["username"] == "fb_carol"


def test_filter_by_in(db_factory):
    from lib.repositories.user_repository import UserRepository
    repo = UserRepository(db_factory)
    repo.create({"username": "fb_eve", "email": "fb_eve@test.com",
                 "password_hash": "", "salt": ""})
    repo.create({"username": "fb_frank", "email": "fb_frank@test.com",
                 "password_hash": "", "salt": ""})
    results = repo.filter_by(username__in=["fb_eve", "fb_frank"])
    assert len(results) == 2


def test_filter_by_ne(db_factory):
    from lib.repositories.user_repository import UserRepository
    repo = UserRepository(db_factory)
    repo.create({"username": "fb_grace", "email": "fb_grace@test.com",
                 "password_hash": "", "salt": "", "status": "active"})
    repo.create({"username": "fb_henry", "email": "fb_henry@test.com",
                 "password_hash": "", "salt": "", "status": "suspended"})
    results = repo.filter_by(status__ne="suspended")
    usernames = [u["username"] for u in results]
    assert "fb_grace" in usernames
    assert "fb_henry" not in usernames


def test_filter_by_unknown_operator_raises(db_factory):
    from lib.repositories.user_repository import UserRepository
    import pytest
    repo = UserRepository(db_factory)
    with pytest.raises(ValueError, match="Unknown filter operator"):
        repo.filter_by(username__fuzzy="alice")


# ── _serialize() ──────────────────────────────────────────────────────────────

def test_serialize_returns_scalar_columns_as_dict(repo):
    pet = repo.create({"name": "Suki", "species": "cat"})
    result = repo._serialize(pet)
    assert result == {"id": pet.id, "name": "Suki", "species": "cat"}


def test_serialize_subclass_can_add_extra_fields(repo):
    class ExtendedRepo(PetRepository):
        def _serialize(self, obj):
            d = super()._serialize(obj)
            d["display"] = f"{obj.name} ({obj.species})"
            return d

    extended = ExtendedRepo(repo._factory)
    pet = extended.create({"name": "Mochi", "species": "cat"})
    result = extended._serialize(pet)
    assert result["display"] == "Mochi (cat)"


def test_paginate_items_use_serialize_hook(repo):
    class ExtendedRepo(PetRepository):
        def _serialize(self, obj):
            d = super()._serialize(obj)
            d["tag"] = "tagged"
            return d

    extended = ExtendedRepo(repo._factory)
    extended.create({"name": "A", "species": "dog"})
    result = extended.paginate(page=1, page_size=10)
    assert result["items"][0]["tag"] == "tagged"


def test_filter_by_items_use_serialize_hook(repo):
    class ExtendedRepo(PetRepository):
        def _serialize(self, obj):
            d = super()._serialize(obj)
            d["tag"] = "tagged"
            return d

    extended = ExtendedRepo(repo._factory)
    extended.create({"name": "B", "species": "dog"})
    results = extended.filter_by(species="dog")
    assert results[0]["tag"] == "tagged"


# ── _deserialize() ────────────────────────────────────────────────────────────

def test_deserialize_strips_unknown_keys(repo):
    result = repo._deserialize({"name": "Rex", "species": "dog", "unknown": "ignored"})
    assert "unknown" not in result
    assert result == {"name": "Rex", "species": "dog"}


def test_deserialize_keeps_known_keys(repo):
    result = repo._deserialize({"name": "Rex", "species": "dog"})
    assert result == {"name": "Rex", "species": "dog"}


def test_create_ignores_unknown_fields_via_deserialize(repo):
    # Would raise TypeError without _deserialize stripping "junk"
    pet = repo.create({"name": "Lucky", "species": "hamster", "junk": "ignored"})
    assert pet.name == "Lucky"


def test_update_ignores_unknown_fields_via_deserialize(repo):
    pet = repo.create({"name": "Paws", "species": "cat"})
    updated = repo.update(pet.id, {"name": "Paws II", "nonexistent": "value"})
    assert updated.name == "Paws II"


def test_deserialize_subclass_can_coerce_types(repo):
    class CoercingRepo(PetRepository):
        def _deserialize(self, data: dict) -> dict:
            d = super()._deserialize(data)
            if "id" in d and isinstance(d["id"], str):
                d["id"] = int(d["id"])
            return d

    coercing = CoercingRepo(repo._factory)
    result = coercing._deserialize({"id": "42", "name": "X", "species": "y"})
    assert result["id"] == 42
    assert isinstance(result["id"], int)
