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
