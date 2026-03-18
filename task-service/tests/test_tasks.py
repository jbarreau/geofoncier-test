import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.models.task import Task, TaskStatus, TaskStatusHistory
from geofoncier_shared.redis.redis_client import get_redis
from app.routes.tasks import router
from geofoncier_shared.fastapi.schemas.auth import CurrentUser

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token(
    private_key: str,
    user_id: uuid.UUID | None = None,
    roles: list[str] | None = None,
    permissions: list[str] | None = None,
    payload_overrides: dict | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id or uuid.uuid4()),
        "email": "user@example.com",
        "roles": roles if roles is not None else ["editor"],
        "permissions": (
            permissions
            if permissions is not None
            else ["task:create", "task:read", "task:update", "task:delete"]
        ),
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }
    if payload_overrides:
        payload.update(payload_overrides)
    return jwt.encode(payload, private_key, algorithm="RS256")


def _make_task(
    owner_id: uuid.UUID | None = None,
    status: TaskStatus = TaskStatus.todo,
) -> Task:
    task = Task()
    task.id = uuid.uuid4()
    task.title = "Test task"
    task.description = "A test task"
    task.status = status
    task.owner_id = owner_id or uuid.uuid4()
    task.due_date = None
    task.created_at = datetime.now(timezone.utc)
    task.updated_at = datetime.now(timezone.utc)
    return task


def _make_app(mock_db: AsyncMock, mock_redis: AsyncMock) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_redis] = lambda: mock_redis
    return app


# ---------------------------------------------------------------------------
# Service layer tests
# ---------------------------------------------------------------------------


class TestTaskServiceCreate:
    async def test_create_task_adds_history(self):
        from app.schemas.task import TaskCreate
        from app.services import task_service

        db = AsyncMock()
        owner_id = uuid.uuid4()

        task_obj = _make_task(owner_id=owner_id)

        async def fake_refresh(obj):
            pass

        db.flush = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = fake_refresh

        added_objects = []

        def capture_add(obj):
            added_objects.append(obj)
            if isinstance(obj, Task):
                obj.id = task_obj.id
                obj.created_at = task_obj.created_at
                obj.updated_at = task_obj.updated_at

        db.add = capture_add

        data = TaskCreate(title="New task", status=TaskStatus.todo)
        with patch.object(task_service, "task_service", create=True):
            result = await task_service.create_task(db, data, owner_id)

        # Should have added a Task and a TaskStatusHistory
        assert any(isinstance(o, Task) for o in added_objects)
        assert any(isinstance(o, TaskStatusHistory) for o in added_objects)

    async def test_create_task_history_matches_status(self):
        from app.schemas.task import TaskCreate
        from app.services import task_service

        db = AsyncMock()
        owner_id = uuid.uuid4()

        added_objects = []

        def capture_add(obj):
            added_objects.append(obj)
            if isinstance(obj, Task):
                obj.id = uuid.uuid4()
                obj.created_at = datetime.now(timezone.utc)
                obj.updated_at = datetime.now(timezone.utc)

        db.add = capture_add
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        data = TaskCreate(title="Doing task", status=TaskStatus.doing)
        await task_service.create_task(db, data, owner_id)

        history_entries = [o for o in added_objects if isinstance(o, TaskStatusHistory)]
        assert len(history_entries) == 1
        assert history_entries[0].status == TaskStatus.doing


class TestTaskServiceCreateFields:
    async def test_create_sets_owner_and_title(self):
        from app.schemas.task import TaskCreate
        from app.services import task_service

        db = AsyncMock()
        owner_id = uuid.uuid4()
        added_objects = []

        def capture_add(obj):
            added_objects.append(obj)
            if isinstance(obj, Task):
                obj.id = uuid.uuid4()
                obj.created_at = datetime.now(timezone.utc)
                obj.updated_at = datetime.now(timezone.utc)

        db.add = capture_add
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        data = TaskCreate(title="My task", description="Desc", status=TaskStatus.todo)
        await task_service.create_task(db, data, owner_id)

        tasks = [o for o in added_objects if isinstance(o, Task)]
        assert len(tasks) == 1
        assert tasks[0].title == "My task"
        assert tasks[0].description == "Desc"
        assert tasks[0].owner_id == owner_id
        assert tasks[0].status == TaskStatus.todo

    async def test_create_flush_before_history(self):
        """flush must be called before the history row so task.id is set."""
        from app.schemas.task import TaskCreate
        from app.services import task_service

        db = AsyncMock()
        call_order = []

        def capture_add(obj):
            call_order.append(("add", type(obj).__name__))
            if isinstance(obj, Task):
                obj.id = uuid.uuid4()
                obj.created_at = datetime.now(timezone.utc)
                obj.updated_at = datetime.now(timezone.utc)

        async def capture_flush():
            call_order.append(("flush", None))

        db.add = capture_add
        db.flush = capture_flush
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        await task_service.create_task(db, TaskCreate(title="T"), uuid.uuid4())

        add_task_idx = next(
            i for i, (op, cls) in enumerate(call_order) if op == "add" and cls == "Task"
        )
        flush_idx = next(i for i, (op, _) in enumerate(call_order) if op == "flush")
        add_history_idx = next(
            i
            for i, (op, cls) in enumerate(call_order)
            if op == "add" and cls == "TaskStatusHistory"
        )
        assert add_task_idx < flush_idx < add_history_idx

    async def test_create_due_date_propagated(self):
        from datetime import date

        from app.schemas.task import TaskCreate
        from app.services import task_service

        db = AsyncMock()
        due = datetime(2026, 12, 31, tzinfo=timezone.utc)
        added_objects = []

        def capture_add(obj):
            added_objects.append(obj)
            if isinstance(obj, Task):
                obj.id = uuid.uuid4()
                obj.created_at = datetime.now(timezone.utc)
                obj.updated_at = datetime.now(timezone.utc)

        db.add = capture_add
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        await task_service.create_task(
            db, TaskCreate(title="T", due_date=due), uuid.uuid4()
        )

        tasks = [o for o in added_objects if isinstance(o, Task)]
        assert tasks[0].due_date == due

    async def test_create_commits_and_refreshes(self):
        from app.schemas.task import TaskCreate
        from app.services import task_service

        db = AsyncMock()

        def capture_add(obj):
            if isinstance(obj, Task):
                obj.id = uuid.uuid4()
                obj.created_at = datetime.now(timezone.utc)
                obj.updated_at = datetime.now(timezone.utc)

        db.add = capture_add
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        await task_service.create_task(db, TaskCreate(title="T"), uuid.uuid4())

        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()


class TestTaskServiceListTasks:
    async def test_list_all_no_filter(self):
        from app.services import task_service

        db = AsyncMock()
        tasks = [_make_task(), _make_task()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = tasks
        db.execute = AsyncMock(return_value=mock_result)

        result = await task_service.list_tasks(db)

        assert result == tasks
        db.execute.assert_awaited_once()

    async def test_list_filters_by_owner(self):
        from app.services import task_service

        owner_id = uuid.uuid4()
        db = AsyncMock()
        owned = [_make_task(owner_id=owner_id)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = owned
        db.execute = AsyncMock(return_value=mock_result)

        result = await task_service.list_tasks(db, owner_id=owner_id)

        assert result == owned
        db.execute.assert_awaited_once()

    async def test_list_returns_empty_list(self):
        from app.services import task_service

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        result = await task_service.list_tasks(db)

        assert result == []


class TestTaskServiceGetTask:
    async def test_get_existing_task(self):
        from app.services import task_service

        db = AsyncMock()
        task = _make_task()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        db.execute = AsyncMock(return_value=mock_result)

        result = await task_service.get_task(db, task.id)

        assert result is task

    async def test_get_missing_task_returns_none(self):
        from app.services import task_service

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        result = await task_service.get_task(db, uuid.uuid4())

        assert result is None


class TestTaskServiceUpdate:
    async def test_update_status_adds_history(self):
        from app.schemas.task import TaskUpdate
        from app.services import task_service

        db = AsyncMock()
        task = _make_task(status=TaskStatus.todo)

        added_objects = []
        db.add = lambda obj: added_objects.append(obj)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        data = TaskUpdate(status=TaskStatus.doing)
        await task_service.update_task(db, task, data)

        history_entries = [o for o in added_objects if isinstance(o, TaskStatusHistory)]
        assert len(history_entries) == 1
        assert history_entries[0].status == TaskStatus.doing

    async def test_update_same_status_no_history(self):
        from app.schemas.task import TaskUpdate
        from app.services import task_service

        db = AsyncMock()
        task = _make_task(status=TaskStatus.todo)

        added_objects = []
        db.add = lambda obj: added_objects.append(obj)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        data = TaskUpdate(status=TaskStatus.todo)
        await task_service.update_task(db, task, data)

        history_entries = [o for o in added_objects if isinstance(o, TaskStatusHistory)]
        assert len(history_entries) == 0

    async def test_update_no_status_no_history(self):
        from app.schemas.task import TaskUpdate
        from app.services import task_service

        db = AsyncMock()
        task = _make_task(status=TaskStatus.todo)

        added_objects = []
        db.add = lambda obj: added_objects.append(obj)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        data = TaskUpdate(title="New title")
        await task_service.update_task(db, task, data)

        history_entries = [o for o in added_objects if isinstance(o, TaskStatusHistory)]
        assert len(history_entries) == 0

    async def test_update_patches_fields(self):
        from app.schemas.task import TaskUpdate
        from app.services import task_service

        db = AsyncMock()
        task = _make_task(status=TaskStatus.todo)
        task.title = "Original"

        db.add = lambda obj: None
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        data = TaskUpdate(title="Updated", status=TaskStatus.done)
        await task_service.update_task(db, task, data)

        assert task.title == "Updated"
        assert task.status == TaskStatus.done

    async def test_update_description(self):
        from app.schemas.task import TaskUpdate
        from app.services import task_service

        db = AsyncMock()
        task = _make_task()
        task.description = "Old desc"

        db.add = lambda obj: None
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        await task_service.update_task(db, task, TaskUpdate(description="New desc"))

        assert task.description == "New desc"

    async def test_update_due_date(self):
        from app.schemas.task import TaskUpdate
        from app.services import task_service

        db = AsyncMock()
        task = _make_task()
        new_due = datetime(2027, 1, 1, tzinfo=timezone.utc)

        db.add = lambda obj: None
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        await task_service.update_task(db, task, TaskUpdate(due_date=new_due))

        assert task.due_date == new_due

    async def test_update_none_fields_not_overwritten(self):
        from app.schemas.task import TaskUpdate
        from app.services import task_service

        db = AsyncMock()
        task = _make_task(status=TaskStatus.doing)
        task.title = "Keep"
        task.description = "Keep desc"

        db.add = lambda obj: None
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        await task_service.update_task(db, task, TaskUpdate())

        assert task.title == "Keep"
        assert task.description == "Keep desc"
        assert task.status == TaskStatus.doing

    async def test_update_sets_updated_at(self):
        from app.schemas.task import TaskUpdate
        from app.services import task_service

        db = AsyncMock()
        task = _make_task()
        original_updated_at = task.updated_at

        db.add = lambda obj: None
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        await task_service.update_task(db, task, TaskUpdate(title="X"))

        assert task.updated_at >= original_updated_at

    async def test_update_commits_and_refreshes(self):
        from app.schemas.task import TaskUpdate
        from app.services import task_service

        db = AsyncMock()
        task = _make_task()
        db.add = lambda obj: None
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        await task_service.update_task(db, task, TaskUpdate(title="X"))

        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()


class TestTaskServiceDeleteTask:
    async def test_delete_calls_db_delete_and_commit(self):
        from app.services import task_service

        db = AsyncMock()
        task = _make_task()
        db.delete = AsyncMock()
        db.commit = AsyncMock()

        await task_service.delete_task(db, task)

        db.delete.assert_awaited_once_with(task)
        db.commit.assert_awaited_once()

    async def test_delete_correct_task_passed(self):
        from app.services import task_service

        db = AsyncMock()
        task_a = _make_task()
        task_b = _make_task()
        db.delete = AsyncMock()
        db.commit = AsyncMock()

        await task_service.delete_task(db, task_a)

        deleted = db.delete.call_args[0][0]
        assert deleted is task_a
        assert deleted is not task_b


# ---------------------------------------------------------------------------
# Route tests: POST /tasks
# ---------------------------------------------------------------------------


class TestCreateTaskRoute:
    def test_create_requires_permission(self, rsa_key_pair):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        app = _make_app(mock_db, mock_redis)

        token = _make_token(rsa_key_pair["private_key"], permissions=["task:read"])
        with TestClient(app) as client:
            resp = client.post(
                "/api/tasks",
                json={"title": "T"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 403

    def test_create_returns_201(self, rsa_key_pair):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        app = _make_app(mock_db, mock_redis)

        user_id = uuid.uuid4()
        token = _make_token(
            rsa_key_pair["private_key"],
            user_id=user_id,
            permissions=["task:create"],
        )
        task = _make_task(owner_id=user_id)

        with patch("app.routes.tasks.task_service.create_task", return_value=task):
            with TestClient(app) as client:
                resp = client.post(
                    "/api/tasks",
                    json={"title": "New task"},
                    headers={"Authorization": f"Bearer {token}"},
                )
        assert resp.status_code == 201
        assert resp.json()["title"] == "Test task"

    def test_create_unauthenticated(self):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        app = _make_app(mock_db, mock_redis)

        with TestClient(app) as client:
            resp = client.post("/api/tasks", json={"title": "T"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Route tests: GET /tasks
# ---------------------------------------------------------------------------


class TestListTasksRoute:
    def test_list_requires_read_permission(self, rsa_key_pair):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        app = _make_app(mock_db, mock_redis)

        token = _make_token(rsa_key_pair["private_key"], permissions=["task:create"])
        with TestClient(app) as client:
            resp = client.get(
                "/api/tasks", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 403

    def test_viewer_filtered_by_owner(self, rsa_key_pair):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        app = _make_app(mock_db, mock_redis)

        user_id = uuid.uuid4()
        token = _make_token(
            rsa_key_pair["private_key"],
            user_id=user_id,
            roles=["viewer"],
            permissions=["task:read"],
        )
        tasks = [_make_task(owner_id=user_id)]

        captured_owner = {}

        async def fake_list(db, owner_id=None):
            captured_owner["value"] = owner_id
            return tasks

        with patch("app.routes.tasks.task_service.list_tasks", side_effect=fake_list):
            with TestClient(app) as client:
                resp = client.get(
                    "/api/tasks", headers={"Authorization": f"Bearer {token}"}
                )

        assert resp.status_code == 200
        assert captured_owner["value"] == user_id

    def test_admin_sees_all(self, rsa_key_pair):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        app = _make_app(mock_db, mock_redis)

        token = _make_token(
            rsa_key_pair["private_key"],
            roles=["admin"],
            permissions=["task:read"],
        )
        tasks = [_make_task(), _make_task()]

        captured_owner = {}

        async def fake_list(db, owner_id=None):
            captured_owner["value"] = owner_id
            return tasks

        with patch("app.routes.tasks.task_service.list_tasks", side_effect=fake_list):
            with TestClient(app) as client:
                resp = client.get(
                    "/api/tasks", headers={"Authorization": f"Bearer {token}"}
                )

        assert resp.status_code == 200
        assert captured_owner["value"] is None
        assert len(resp.json()) == 2


# ---------------------------------------------------------------------------
# Route tests: GET /tasks/{id}
# ---------------------------------------------------------------------------


class TestGetTaskRoute:
    def test_get_existing_task(self, rsa_key_pair):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        app = _make_app(mock_db, mock_redis)

        task = _make_task()
        token = _make_token(
            rsa_key_pair["private_key"],
            roles=["editor"],
            permissions=["task:read"],
        )

        with patch("app.routes.tasks.task_service.get_task", return_value=task):
            with TestClient(app) as client:
                resp = client.get(
                    f"/api/tasks/{task.id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(task.id)

    def test_get_missing_task_returns_404(self, rsa_key_pair):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        app = _make_app(mock_db, mock_redis)

        token = _make_token(rsa_key_pair["private_key"], permissions=["task:read"])

        with patch("app.routes.tasks.task_service.get_task", return_value=None):
            with TestClient(app) as client:
                resp = client.get(
                    f"/api/tasks/{uuid.uuid4()}",
                    headers={"Authorization": f"Bearer {token}"},
                )
        assert resp.status_code == 404

    def test_viewer_cannot_access_other_owner_task(self, rsa_key_pair):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        app = _make_app(mock_db, mock_redis)

        viewer_id = uuid.uuid4()
        task = _make_task(owner_id=uuid.uuid4())  # owned by someone else

        token = _make_token(
            rsa_key_pair["private_key"],
            user_id=viewer_id,
            roles=["viewer"],
            permissions=["task:read"],
        )

        with patch("app.routes.tasks.task_service.get_task", return_value=task):
            with TestClient(app) as client:
                resp = client.get(
                    f"/api/tasks/{task.id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
        assert resp.status_code == 403

    def test_viewer_can_access_own_task(self, rsa_key_pair):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        app = _make_app(mock_db, mock_redis)

        viewer_id = uuid.uuid4()
        task = _make_task(owner_id=viewer_id)

        token = _make_token(
            rsa_key_pair["private_key"],
            user_id=viewer_id,
            roles=["viewer"],
            permissions=["task:read"],
        )

        with patch("app.routes.tasks.task_service.get_task", return_value=task):
            with TestClient(app) as client:
                resp = client.get(
                    f"/api/tasks/{task.id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Route tests: PATCH /tasks/{id}
# ---------------------------------------------------------------------------


class TestUpdateTaskRoute:
    def test_update_requires_update_permission(self, rsa_key_pair):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        app = _make_app(mock_db, mock_redis)

        token = _make_token(rsa_key_pair["private_key"], permissions=["task:read"])
        with TestClient(app) as client:
            resp = client.patch(
                f"/api/tasks/{uuid.uuid4()}",
                json={"title": "X"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 403

    def test_update_missing_task_returns_404(self, rsa_key_pair):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        app = _make_app(mock_db, mock_redis)

        token = _make_token(rsa_key_pair["private_key"], permissions=["task:update"])

        with patch("app.routes.tasks.task_service.get_task", return_value=None):
            with TestClient(app) as client:
                resp = client.patch(
                    f"/api/tasks/{uuid.uuid4()}",
                    json={"title": "X"},
                    headers={"Authorization": f"Bearer {token}"},
                )
        assert resp.status_code == 404

    def test_update_success(self, rsa_key_pair):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        app = _make_app(mock_db, mock_redis)

        task = _make_task()
        updated = _make_task(owner_id=task.owner_id)
        updated.id = task.id
        updated.title = "Updated"
        updated.status = TaskStatus.doing

        token = _make_token(rsa_key_pair["private_key"], permissions=["task:update"])

        with patch("app.routes.tasks.task_service.get_task", return_value=task):
            with patch(
                "app.routes.tasks.task_service.update_task", return_value=updated
            ):
                with TestClient(app) as client:
                    resp = client.patch(
                        f"/api/tasks/{task.id}",
                        json={"title": "Updated", "status": "doing"},
                        headers={"Authorization": f"Bearer {token}"},
                    )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"
        assert resp.json()["status"] == "doing"


# ---------------------------------------------------------------------------
# Route tests: DELETE /tasks/{id}
# ---------------------------------------------------------------------------


class TestDeleteTaskRoute:
    def test_delete_requires_delete_permission(self, rsa_key_pair):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        app = _make_app(mock_db, mock_redis)

        token = _make_token(rsa_key_pair["private_key"], permissions=["task:read"])
        with TestClient(app) as client:
            resp = client.delete(
                f"/api/tasks/{uuid.uuid4()}",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 403

    def test_delete_requires_admin_role(self, rsa_key_pair):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        app = _make_app(mock_db, mock_redis)

        token = _make_token(
            rsa_key_pair["private_key"],
            roles=["editor"],
            permissions=["task:delete"],
        )
        with TestClient(app) as client:
            resp = client.delete(
                f"/api/tasks/{uuid.uuid4()}",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 403
        assert "Admin" in resp.json()["detail"]

    def test_delete_missing_task_returns_404(self, rsa_key_pair):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        app = _make_app(mock_db, mock_redis)

        token = _make_token(
            rsa_key_pair["private_key"],
            roles=["admin"],
            permissions=["task:delete"],
        )

        with patch("app.routes.tasks.task_service.get_task", return_value=None):
            with TestClient(app) as client:
                resp = client.delete(
                    f"/api/tasks/{uuid.uuid4()}",
                    headers={"Authorization": f"Bearer {token}"},
                )
        assert resp.status_code == 404

    def test_delete_success_returns_204(self, rsa_key_pair):
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        app = _make_app(mock_db, mock_redis)

        task = _make_task()
        token = _make_token(
            rsa_key_pair["private_key"],
            roles=["admin"],
            permissions=["task:delete"],
        )

        with patch("app.routes.tasks.task_service.get_task", return_value=task):
            with patch(
                "app.routes.tasks.task_service.delete_task", new_callable=AsyncMock
            ):
                with TestClient(app) as client:
                    resp = client.delete(
                        f"/api/tasks/{task.id}",
                        headers={"Authorization": f"Bearer {token}"},
                    )
        assert resp.status_code == 204
