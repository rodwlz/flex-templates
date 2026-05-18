# Import all ORM models here so Base.metadata is fully populated
# whenever anything from lib.models is imported.
from lib.models.user import User  # noqa: F401
from lib.models.role import Role  # noqa: F401
