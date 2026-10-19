from __future__ import annotations

import types
import unittest

from devconsole.services.process_observer import PsutilObserver, compare_with_procfs
from devconsole.services.runtime.process_identity import ProcessFacts


class _Addr:
    def __init__(self, port):
        self.port = port


class _Conn:
    def __init__(self, port, status="LISTEN"):
        self.status = status
        self.laddr = _Addr(port)


class _FakeProcess:
    def __init__(self, pid):
        self.pid = pid

    def ppid(self):
        return 10

    def exe(self):
        return "/usr/bin/python3"

    def cmdline(self):
        return ["python3", "manage.py", "runserver", "127.0.0.1:8020"]

    def cwd(self):
        return "/tmp/project"

    def username(self):
        return "developer"

    def net_connections(self, kind="inet"):
        return [_Conn(8020), _Conn(5000, status="ESTABLISHED")]


class _FakePsutil:
    __version__ = "test"
    CONN_LISTEN = "LISTEN"

    @staticmethod
    def pids():
        return [20, 10]

    @staticmethod
    def pid_exists(pid):
        return pid == 20

    Process = _FakeProcess


class _FakeProcInspector:
    @staticmethod
    def read_facts(pid):
        return ProcessFacts(
            pid=pid,
            ppid=10,
            executable="/usr/bin/python3",
            command_line=("python3", "manage.py", "runserver", "127.0.0.1:8020"),
            cwd="/tmp/project",
            listening_ports=(8020,),
        )


class ProcessObserverTests(unittest.TestCase):
    def test_unavailable_backend_fails_read_only(self):
        observer = PsutilObserver(psutil_module=False)
        self.assertFalse(observer.available)
        self.assertEqual([], observer.list_pids())
        self.assertFalse(observer.is_alive(1))
        self.assertIn("unavailable", observer.observe(1).errors[0])

    def test_observer_reads_process_facts_without_mutation_api(self):
        observer = PsutilObserver(psutil_module=_FakePsutil)
        facts = observer.observe(20)
        self.assertEqual(10, facts.ppid)
        self.assertEqual((8020,), facts.listening_ports)
        self.assertEqual("/usr/bin/python3", facts.executable)
        self.assertNotIn("terminate", dir(observer))
        self.assertNotIn("kill", dir(observer))

    def test_list_and_liveness(self):
        observer = PsutilObserver(psutil_module=_FakePsutil)
        self.assertEqual([10, 20], observer.list_pids())
        self.assertTrue(observer.is_alive(20))
        self.assertFalse(observer.is_alive(21))

    def test_shadow_comparison_reports_equivalence(self):
        observer = PsutilObserver(psutil_module=_FakePsutil)
        result = compare_with_procfs(20, observer=observer, proc_inspector=_FakeProcInspector())
        self.assertTrue(result.comparable)
        self.assertTrue(result.equivalent)
        self.assertEqual({}, result.differences)

    def test_shadow_comparison_is_non_authoritative_when_unavailable(self):
        observer = PsutilObserver(psutil_module=False)
        result = compare_with_procfs(20, observer=observer, proc_inspector=_FakeProcInspector())
        self.assertFalse(result.comparable)
        self.assertFalse(result.equivalent)


if __name__ == "__main__":
    unittest.main()
