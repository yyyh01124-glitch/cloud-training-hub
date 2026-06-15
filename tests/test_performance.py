"""Basic performance tests — response times and page completeness."""

import time
import pytest


# Thresholds (milliseconds)
DASHBOARD_MAX_MS = 2000
KANBAN_MAX_MS = 3000
LIST_PAGE_MAX_MS = 2000
DETAIL_PAGE_MAX_MS = 1500


def _measure( client,  url,  method='GET',  data=None,  follow_redirects=False):
    """Return (elapsed_ms, response) for a single request."""
    start = time.perf_counter()
    if method == 'GET':
        r = client.get(url, follow_redirects=follow_redirects)
    else:
        r = client.post(url, data=data, follow_redirects=follow_redirects)
    elapsed = (time.perf_counter() - start) * 1000
    return elapsed, r


class TestDashboardPerformance:

    def test_dashboard_loads_within_time(self, auth_client):
        """Admin dashboard loads within DASHBOARD_MAX_MS ms."""
        elapsed, r = _measure(auth_client, '/', follow_redirects=True)
        assert r.status_code == 200
        assert elapsed < DASHBOARD_MAX_MS, \
            f'Dashboard took {elapsed:.0f}ms (limit {DASHBOARD_MAX_MS}ms)'

    def test_dashboard_contains_expected_sections(self, auth_client):
        """Dashboard page has key content placeholders."""
        _, r = _measure(auth_client, '/', follow_redirects=True)
        body = r.data.decode('utf-8').lower()
        # At least some expected terms should appear
        keywords = ['project', 'task', 'bug', '日报', '项目', '任务', 'dashboard']
        matches = [kw for kw in keywords if kw in body]
        assert len(matches) >= 2, \
            f'Dashboard missing expected content, found only: {matches}'


class TestKanbanBoardPerformance:

    def test_kanban_board_renders_all_columns(self, auth_client):
        """Kanban board loads and contains all six status columns."""
        elapsed, r = _measure(auth_client, '/tasks/board', follow_redirects=True)
        assert r.status_code == 200
        assert elapsed < KANBAN_MAX_MS, \
            f'Kanban board took {elapsed:.0f}ms (limit {KANBAN_MAX_MS}ms)'

        body = r.data.decode('utf-8')
        status_labels = ['待开始', '进行中', '待测试', '已完成', '已延期', '已关闭']
        found = [s for s in status_labels if s in body]
        assert len(found) == len(status_labels), \
            f'Kanban columns missing: expected {status_labels}, found {found}'

    def test_kanban_board_with_project_filter(self, auth_client):
        """Kanban board loads quickly with a project filter parameter."""
        elapsed, r = _measure(auth_client, '/tasks/board?project_id=1',
                              follow_redirects=True)
        assert r.status_code == 200
        assert elapsed < KANBAN_MAX_MS, \
            f'Filtered kanban took {elapsed:.0f}ms (limit {KANBAN_MAX_MS}ms)'


class TestListPagesPerformance:

    def test_course_list_loads_quickly(self, auth_client):
        elapsed, r = _measure(auth_client, '/projects/courses',
                              follow_redirects=True)
        assert r.status_code == 200
        assert elapsed < LIST_PAGE_MAX_MS, \
            f'Course list took {elapsed:.0f}ms'

    def test_project_list_loads_quickly(self, auth_client):
        elapsed, r = _measure(auth_client, '/projects/',
                              follow_redirects=True)
        assert r.status_code == 200
        assert elapsed < LIST_PAGE_MAX_MS, \
            f'Project list took {elapsed:.0f}ms'

    def test_task_list_loads_quickly(self, auth_client):
        elapsed, r = _measure(auth_client, '/tasks/list',
                              follow_redirects=True)
        assert r.status_code == 200
        assert elapsed < LIST_PAGE_MAX_MS, \
            f'Task list took {elapsed:.0f}ms'

    def test_bug_list_loads_quickly(self, auth_client):
        elapsed, r = _measure(auth_client, '/bugs/',
                              follow_redirects=True)
        assert r.status_code == 200
        assert elapsed < LIST_PAGE_MAX_MS, \
            f'Bug list took {elapsed:.0f}ms'

    def test_team_list_loads_quickly(self, auth_client):
        elapsed, r = _measure(auth_client, '/teams/',
                              follow_redirects=True)
        assert r.status_code == 200
        assert elapsed < LIST_PAGE_MAX_MS, \
            f'Team list took {elapsed:.0f}ms'

    def report_list_loads_quickly(self, auth_client):
        elapsed, r = _measure(auth_client, '/reports/',
                              follow_redirects=True)
        assert r.status_code == 200
        assert elapsed < LIST_PAGE_MAX_MS, \
            f'Report list took {elapsed:.0f}ms'

    def test_ai_record_list_loads_quickly(self, auth_client):
        elapsed, r = _measure(auth_client, '/ai-records/',
                              follow_redirects=True)
        assert r.status_code == 200
        assert elapsed < LIST_PAGE_MAX_MS, \
            f'AI record list took {elapsed:.0f}ms'

    def test_crawler_config_list_loads_quickly(self, auth_client):
        elapsed, r = _measure(auth_client, '/crawler/configs',
                              follow_redirects=True)
        assert r.status_code == 200
        assert elapsed < LIST_PAGE_MAX_MS, \
            f'Crawler config list took {elapsed:.0f}ms'

    def test_admin_users_page_loads_quickly(self, auth_client):
        elapsed, r = _measure(auth_client, '/admin/users',
                              follow_redirects=True)
        assert r.status_code == 200
        assert elapsed < LIST_PAGE_MAX_MS, \
            f'Admin users page took {elapsed:.0f}ms'


class TestDetailPagesPerformance:

    def test_login_page_loads_quickly(self, client):
        elapsed, r = _measure(client, '/auth/login')
        assert r.status_code == 200
        assert elapsed < DETAIL_PAGE_MAX_MS, \
            f'Login page took {elapsed:.0f}ms'
