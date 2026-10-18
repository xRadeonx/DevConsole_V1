# devconsole/services/tilix_service.py
"""DEPRECATED INTERNAL COMPATIBILITY LAYER — do not add code here.

The Tilix implementation moved to
:mod:`devconsole.services.terminal.tilix_backend` in Phase 2 of the desktop
migration.  This module survives so that every existing import path keeps
working unchanged::

    from devconsole.services import tilix_service
    from devconsole.services.tilix_service import scan_tilix_sessions

New code must depend on the backend abstraction instead::

    from devconsole.services.terminal import get_terminal_backend

Module aliasing, and why not plain re-exports
---------------------------------------------
This module *becomes* the implementation module rather than re-exporting names
from it.  That is not a stylistic preference — it is required for correctness.

The characterization suite in ``tests/devconsole/test_tilix_service.py`` patches
attributes **on this module object**::

    mock.patch.object(tilix_service, "BASE_DIR", root)
    mock.patch.object(tilix_service, "Path", _PathProxy())

Both names are read by the implementation at call time — ``BASE_DIR`` decides
which workspace is scanned and where ``start_tilix.sh`` lives, ``Path`` decides
where generated session JSON files are written.  If this module merely did
``from ...tilix_backend import scan_tilix_sessions``, it would hold *copies* of
the function objects living in a different namespace, and patching
``tilix_service.BASE_DIR`` would silently stop having any effect: the tests
would break, and worse, the same disconnect could hide a real behaviour change
in production.

Aliasing keeps a single namespace, so ``tilix_service`` and
``tilix_backend`` are literally the same module object: patching either one
patches the code that actually runs, and no wrapper can drift from the
implementation it wraps.

Deleting this module requires first migrating the patch targets in the test
suite; that is Phase 3 work at the earliest, if ever.
"""

import sys

from devconsole.services.terminal import tilix_backend as _implementation

# CPython re-reads sys.modules[spec.name] after executing a module, so this
# replacement is what `import devconsole.services.tilix_service` returns from
# here on — including `from devconsole.services import tilix_service`.
sys.modules[__name__] = _implementation
