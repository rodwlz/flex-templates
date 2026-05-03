"""Unit of Work transaction tests."""
import pytest
from lib.database.uow import UnitOfWork
from lib.models.user import User
from lib.repositories.user_repository import UserRepository
from lib.core.interfaces import StagingService
from lib.contracts.base import ActionRequest


def test_stage_shows_new_objects(db_factory):
    with db_factory.unit_of_work() as uow:
        repo = uow.repo(UserRepository)
        repo.create({"username": "alice", "email": "a@ex.com", "password_hash": "h1", "salt": "s1"})
        diff = uow.stage()
        assert len(diff["new"]) == 1
        assert diff["new"][0]["username"] == "alice"


def test_stage_shows_modified_objects(user_repo, db_factory):
    user = user_repo.create({"username": "bob", "email": "b@ex.com", "password_hash": "h2", "salt": "s2"})
    with db_factory.unit_of_work() as uow:
        repo = uow.repo(UserRepository)
        repo.update(user.id, {"status": "admin"})
        diff = uow.stage()
        assert len(diff["modified"]) == 1
        assert diff["modified"][0]["status"] == "admin"


def test_stage_shows_deleted_objects(user_repo, db_factory):
    user = user_repo.create({"username": "charlie", "email": "c@ex.com", "password_hash": "h3", "salt": "s3"})
    with db_factory.unit_of_work() as uow:
        repo = uow.repo(UserRepository)
        repo.delete(user.id)
        diff = uow.stage()
        assert len(diff["deleted"]) == 1
        assert diff["deleted"][0]["id"] == user.id
        assert diff["deleted"][0]["type"] == "User"


def test_commit_persists_changes(db_factory):
    with db_factory.unit_of_work() as uow:
        repo = uow.repo(UserRepository)
        user = repo.create({"username": "diana", "email": "d@ex.com", "password_hash": "h4", "salt": "s4"})
        uow.commit()
    fetched = UserRepository(db_factory).get(user.id)
    assert fetched is not None
    assert fetched.username == "diana"


def test_rollback_discards_changes(db_factory):
    with db_factory.unit_of_work() as uow:
        repo = uow.repo(UserRepository)
        repo.create({"username": "eve", "email": "e@ex.com", "password_hash": "h5", "salt": "s5"})
        uow.rollback()
    assert len(UserRepository(db_factory).list(username="eve")) == 0


def test_context_manager_auto_rollback_on_exception(db_factory):
    try:
        with db_factory.unit_of_work() as uow:
            repo = uow.repo(UserRepository)
            repo.create({"username": "frank", "email": "f@ex.com", "password_hash": "h6", "salt": "s6"})
            raise RuntimeError("Oops")
    except RuntimeError:
        pass
    assert len(UserRepository(db_factory).list(username="frank")) == 0


class OrderServiceExample(StagingService):
    def _stage_impl(self, uow, data: dict) -> dict:
        repo = uow.repo(UserRepository)
        user = repo.create(data)
        return {"user_id": user.id, "username": user.username}


def test_staging_service_full_flow(db_factory):
    service = OrderServiceExample(db_factory)
    result = service.execute(ActionRequest(
        action="stage",
        data={"username": "grace", "email": "g@ex.com", "password_hash": "h7", "salt": "s7"}
    ))
    assert result.success
    assert "preview" in result.data
    assert "user_id" in result.data
    assert len(result.data["preview"]["new"]) == 1

    confirm_result = service.execute(ActionRequest(action="confirm", data={}))
    assert confirm_result.success
    fetched = UserRepository(db_factory).get(result.data["user_id"])
    assert fetched.username == "grace"


def test_confirm_without_stage_fails(db_factory):
    service = OrderServiceExample(db_factory)
    result = service.execute(ActionRequest(action="confirm", data={}))
    assert not result.success
    assert "Nothing to confirm" in result.error


def test_staging_service_cancel(db_factory):
    service = OrderServiceExample(db_factory)
    result = service.execute(ActionRequest(
        action="stage",
        data={"username": "henry", "email": "h@ex.com", "password_hash": "h8", "salt": "s8"}
    ))
    assert result.success

    cancel_result = service.execute(ActionRequest(action="cancel", data={}))
    assert cancel_result.success
    fetched = UserRepository(db_factory).get(result.data["user_id"])
    assert fetched is None


def test_second_stage_cancels_previous(db_factory):
    service = OrderServiceExample(db_factory)
    result1 = service.execute(ActionRequest(
        action="stage",
        data={"username": "ivan", "email": "i@ex.com", "password_hash": "h9", "salt": "s9"}
    ))
    result2 = service.execute(ActionRequest(
        action="stage",
        data={"username": "jane", "email": "j@ex.com", "password_hash": "h10", "salt": "s10"}
    ))
    confirm_result = service.execute(ActionRequest(action="confirm", data={}))
    assert confirm_result.success
    # SQLite reuses IDs after rollback, so check by username rather than by ID.
    # The invariant is: only jane's data was committed; ivan's was rolled back.
    all_usernames = {u.username for u in UserRepository(db_factory).list()}
    assert "ivan" not in all_usernames
    assert "jane" in all_usernames


def test_cancel_idempotent(db_factory):
    service = OrderServiceExample(db_factory)
    service.execute(ActionRequest(action="stage", data={"username": "kate", "email": "k@ex.com", "password_hash": "h11", "salt": "s11"}))
    result1 = service.execute(ActionRequest(action="cancel", data={}))
    result2 = service.execute(ActionRequest(action="cancel", data={}))
    assert result1.success
    assert result2.success
