from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ViewContext:
    """Typed view of the props dict injected into every BaseView.

    Fields use Any until Phase 5B fills in real types (importing concrete
    adapter/service types here would create circular dependencies).

    Usage in views:
        self.ctx.backend       # IBackendAdapter | None
        self.ctx.nav_service   # NavigationService
        self.ctx.vault         # Vault | None
        self.ctx.events        # EventBus | None
        self.ctx.dev_nav       # bool
        self.ctx.params        # dict — path params
        self.ctx.query         # dict — query string params

    IMPORTANT: ctx.params and ctx.query are raw unvalidated dicts (strings from
    the URL). When the view defines Params (a Pydantic model), use self.params
    for type-coerced access. ctx.params is a shallow copy — safe to read, but
    mutations won't affect self.props.
    """

    nav_service: Any
    backend:     Any = None
    nav:         Any = None
    vault:       Any = None
    events:      Any = None
    dev_nav:     bool = False
    params:      dict = field(default_factory=dict)
    query:       dict = field(default_factory=dict)

    @classmethod
    def from_props(cls, props: dict) -> "ViewContext":
        return cls(
            nav_service = props["nav_service"],
            backend     = props.get("backend"),
            nav         = props.get("nav"),
            vault       = props.get("vault"),
            events      = props.get("events"),
            dev_nav     = bool(props.get("dev_nav")),
            params      = dict(props.get("params", {})),
            query       = dict(props.get("query", {})),
        )
