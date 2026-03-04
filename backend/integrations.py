# integrations.py - Jira & Google Sheets Integration Module

import os
import re
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from jira import JIRA
import aiohttp

logger = logging.getLogger(__name__)

# ============== COLUMN MAPPING / NORMALIZATION ==============

# Standard field names that we use internally
STANDARD_FIELDS = {
    # Issue fields
    'key': ['key', 'issue_key', 'ticket', 'ticket_id', 'issue_id', 'id', 'jira_key'],
    'summary': ['summary', 'title', 'name', 'issue_title', 'task_name', 'description_short'],
    'status': ['status', 'state', 'issue_status', 'current_status', 'workflow_status'],
    'issue_type': ['issue_type', 'issuetype', 'type', 'ticket_type', 'task_type', 'item_type'],
    'priority': ['priority', 'severity', 'urgency', 'importance'],
    'assignee': ['assignee', 'assigned_to', 'owner', 'responsible', 'assigned'],
    'reporter': ['reporter', 'created_by', 'author', 'reported_by'],
    'created': ['created', 'created_at', 'creation_date', 'date_created', 'create_date'],
    'updated': ['updated', 'updated_at', 'last_updated', 'modified', 'modified_at'],
    'resolved': ['resolved', 'resolved_at', 'resolution_date', 'completed_at', 'done_date'],
    'due_date': ['due_date', 'duedate', 'deadline', 'target_date', 'due'],
    'story_points': ['story_points', 'storypoints', 'points', 'estimate', 'effort', 'sp', 'story points'],
    'sprint': ['sprint', 'sprint_name', 'iteration', 'sprint_id'],
    'epic': ['epic', 'epic_name', 'epic_key', 'epic_link', 'parent_epic'],
    'labels': ['labels', 'tags', 'categories'],
    'components': ['components', 'component', 'module', 'area'],
    'blocked': ['blocked', 'is_blocked', 'flagged', 'impediment'],
    'blocker_reason': ['blocker_reason', 'blocked_reason', 'impediment_reason', 'block_description'],
    
    # Sprint/Velocity fields
    'sprint_name': ['sprint_name', 'sprint', 'iteration_name', 'iteration'],
    'sprint_state': ['sprint_state', 'state', 'sprint_status', 'status'],
    'sprint_start': ['sprint_start', 'start_date', 'start', 'begin_date'],
    'sprint_end': ['sprint_end', 'end_date', 'end', 'finish_date'],
    'velocity': ['velocity', 'completed_points', 'done_points', 'delivered'],
    'committed': ['committed', 'planned_points', 'commitment', 'planned'],
    'spillover': ['spillover', 'carryover', 'incomplete', 'not_done'],
    
    # Risk fields
    'risk_name': ['risk_name', 'risk', 'risk_title', 'name', 'title'],
    'risk_description': ['risk_description', 'description', 'details', 'risk_details'],
    'risk_probability': ['risk_probability', 'probability', 'likelihood', 'chance'],
    'risk_impact': ['risk_impact', 'impact', 'severity', 'consequence'],
    'risk_status': ['risk_status', 'status', 'state', 'mitigation_status'],
    'risk_owner': ['risk_owner', 'owner', 'responsible', 'assigned_to'],
    'mitigation': ['mitigation', 'mitigation_plan', 'action', 'response'],

    # ClickUp-specific fields
    'task_id': ['task_id', 'clickup_id', 'cu_id'],
    'list_name': ['list_name', 'list', 'clickup_list'],
    'space_name': ['space_name', 'space', 'clickup_space'],
    'folder_name': ['folder_name', 'folder', 'clickup_folder'],
    'time_estimate': ['time_estimate', 'estimated_time', 'time_estimate_ms'],
    'time_spent': ['time_spent', 'time_logged', 'time_tracked', 'hours_spent'],
    'tags': ['tags', 'tag_names', 'clickup_tags'],
    'watchers': ['watchers', 'followers', 'watching'],
    'date_created': ['date_created', 'created', 'created_at', 'creation_date'],
    'date_closed': ['date_closed', 'closed_at', 'completed_at', 'done_date'],
    'start_date': ['start_date', 'started', 'begin_date'],
}

def normalize_column_name(col_name: str) -> str:
    """Normalize a column name to lowercase, replace spaces/special chars"""
    return re.sub(r'[^a-z0-9]', '_', col_name.lower().strip()).strip('_')

def map_columns(data: List[Dict], field_mapping: Optional[Dict[str, str]] = None) -> List[Dict]:
    """
    Map columns from various formats to standard field names.
    
    Args:
        data: List of dictionaries with original column names
        field_mapping: Optional custom mapping {original_col: standard_field}
    
    Returns:
        List of dictionaries with standardized field names
    """
    if not data:
        return []
    
    # Build reverse mapping from possible names to standard names
    reverse_mapping = {}
    for standard_field, possible_names in STANDARD_FIELDS.items():
        for name in possible_names:
            reverse_mapping[normalize_column_name(name)] = standard_field
    
    # Add custom mapping if provided
    if field_mapping:
        for original, standard in field_mapping.items():
            reverse_mapping[normalize_column_name(original)] = standard
    
    normalized_data = []
    for row in data:
        normalized_row = {}
        for key, value in row.items():
            normalized_key = normalize_column_name(key)
            # Check if we have a mapping
            if normalized_key in reverse_mapping:
                standard_key = reverse_mapping[normalized_key]
            else:
                standard_key = normalized_key  # Keep original if no mapping
            normalized_row[standard_key] = value
        normalized_data.append(normalized_row)
    
    return normalized_data


def detect_data_type(data: List[Dict]) -> str:
    """Detect the type of data based on columns present"""
    if not data:
        return "unknown"
    
    first_row = data[0]
    columns = set(first_row.keys())
    normalized_columns = {normalize_column_name(c) for c in columns}
    
    # Check for sprint/velocity data
    sprint_indicators = {'sprint', 'velocity', 'committed', 'spillover', 'iteration'}
    if len(sprint_indicators & normalized_columns) >= 2:
        return "sprint_data"
    
    # Check for issue/ticket data
    issue_indicators = {'key', 'summary', 'status', 'assignee', 'issue_type', 'ticket', 'story_points'}
    if len(issue_indicators & normalized_columns) >= 2:
        return "issue_data"
    
    # Check for risk register
    risk_indicators = {'risk', 'probability', 'impact', 'mitigation', 'risk_name', 'likelihood'}
    if len(risk_indicators & normalized_columns) >= 2:
        return "risk_register"
    
    return "general"


# ============== JIRA INTEGRATION ==============

class JiraClient:
    """Jira API client for syncing data"""
    
    def __init__(self, instance_url: str, email: str, api_token: str):
        self.instance_url = instance_url.rstrip('/')
        self.email = email
        self.api_token = api_token
        self._jira = None
    
    @property
    def jira(self):
        if self._jira is None:
            self._jira = JIRA(
                server=self.instance_url,
                basic_auth=(self.email, self.api_token)
            )
        return self._jira
    
    def test_connection(self) -> Dict:
        """Test Jira connection and return server info"""
        try:
            server_info = self.jira.server_info()
            return {
                "success": True,
                "server_title": server_info.get("serverTitle"),
                "version": server_info.get("version"),
                "base_url": server_info.get("baseUrl")
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_boards(self) -> List[Dict]:
        """Get all boards"""
        try:
            boards = self.jira.boards()
            return [{"id": b.id, "name": b.name, "type": b.type} for b in boards]
        except Exception as e:
            logger.error(f"Failed to get boards: {e}")
            return []
    
    def get_sprints(self, board_id: int, state: str = "active,closed") -> List[Dict]:
        """Get sprints for a board"""
        try:
            sprints = self.jira.sprints(board_id, state=state)
            return [{
                "id": s.id,
                "name": s.name,
                "state": s.state,
                "start_date": getattr(s, 'startDate', None),
                "end_date": getattr(s, 'endDate', None),
                "complete_date": getattr(s, 'completeDate', None),
                "goal": getattr(s, 'goal', None)
            } for s in sprints]
        except Exception as e:
            logger.error(f"Failed to get sprints: {e}")
            return []
    
    def get_sprint_issues(self, sprint_id: int) -> List[Dict]:
        """Get all issues in a sprint"""
        try:
            jql = f"sprint = {sprint_id}"
            issues = self.jira.search_issues(jql, maxResults=500, expand='changelog')
            return [self._parse_issue(issue) for issue in issues]
        except Exception as e:
            logger.error(f"Failed to get sprint issues: {e}")
            return []
    
    def get_backlog_issues(self, board_id: int) -> List[Dict]:
        """Get backlog issues for a board"""
        try:
            # Get issues not in any sprint
            jql = f"project in (SELECT project FROM board WHERE id = {board_id}) AND sprint is EMPTY"
            issues = self.jira.search_issues(jql, maxResults=200)
            return [self._parse_issue(issue) for issue in issues]
        except Exception as e:
            logger.error(f"Failed to get backlog: {e}")
            return []
    
    def get_project_issues(self, project_key: str, max_results: int = 500) -> List[Dict]:
        """Get all issues for a project"""
        try:
            jql = f"project = {project_key} ORDER BY created DESC"
            issues = self.jira.search_issues(jql, maxResults=max_results, expand='changelog')
            return [self._parse_issue(issue) for issue in issues]
        except Exception as e:
            logger.error(f"Failed to get project issues: {e}")
            return []
    
    def search_issues(self, jql: str, max_results: int = 100) -> List[Dict]:
        """Search issues using JQL"""
        try:
            issues = self.jira.search_issues(jql, maxResults=max_results, expand='changelog')
            return [self._parse_issue(issue) for issue in issues]
        except Exception as e:
            logger.error(f"Failed to search issues: {e}")
            return []
    
    def get_velocity_data(self, board_id: int, sprint_count: int = 10) -> List[Dict]:
        """Calculate velocity data for recent sprints"""
        sprints = self.get_sprints(board_id, state="closed")
        sprints = sorted(sprints, key=lambda x: x.get('complete_date') or '', reverse=True)[:sprint_count]
        
        velocity_data = []
        for sprint in sprints:
            issues = self.get_sprint_issues(sprint['id'])
            
            completed_points = 0
            committed_points = 0
            
            for issue in issues:
                points = issue.get('story_points') or 0
                if issue.get('status', '').lower() in ['done', 'closed', 'resolved', 'completed']:
                    completed_points += points
                committed_points += points
            
            velocity_data.append({
                "sprint_name": sprint['name'],
                "sprint_id": sprint['id'],
                "start_date": sprint.get('start_date'),
                "end_date": sprint.get('end_date'),
                "committed": committed_points,
                "completed": completed_points,
                "velocity": completed_points
            })
        
        return velocity_data
    
    def get_blocked_issues(self, project_key: Optional[str] = None) -> List[Dict]:
        """Get blocked or flagged issues"""
        try:
            jql_parts = ["(status = Blocked OR flagged is not EMPTY)"]
            if project_key:
                jql_parts.append(f"project = {project_key}")
            jql = " AND ".join(jql_parts)
            
            issues = self.jira.search_issues(jql, maxResults=100)
            return [self._parse_issue(issue) for issue in issues]
        except Exception as e:
            logger.error(f"Failed to get blocked issues: {e}")
            return []
    
    def _parse_issue(self, issue) -> Dict:
        """Parse Jira issue to standard format"""
        fields = issue.fields
        
        # Get story points (check common custom field patterns)
        story_points = None
        for attr in ['customfield_10000', 'customfield_10002', 'customfield_10004', 'customfield_10016']:
            sp = getattr(fields, attr, None)
            if sp is not None:
                try:
                    story_points = float(sp)
                    break
                except (ValueError, TypeError):
                    pass
        
        # Get sprint info
        sprint_name = None
        sprint_field = getattr(fields, 'customfield_10020', None) or getattr(fields, 'sprint', None)
        if sprint_field:
            if isinstance(sprint_field, list) and len(sprint_field) > 0:
                sprint_obj = sprint_field[-1]  # Get latest sprint
                if hasattr(sprint_obj, 'name'):
                    sprint_name = sprint_obj.name
                elif isinstance(sprint_obj, str):
                    # Parse sprint string
                    match = re.search(r'name=([^,\]]+)', sprint_obj)
                    if match:
                        sprint_name = match.group(1)
        
        return {
            "key": issue.key,
            "summary": fields.summary,
            "status": fields.status.name if fields.status else None,
            "issue_type": fields.issuetype.name if fields.issuetype else None,
            "priority": fields.priority.name if fields.priority else None,
            "assignee": fields.assignee.displayName if fields.assignee else None,
            "reporter": fields.reporter.displayName if fields.reporter else None,
            "created": str(fields.created) if fields.created else None,
            "updated": str(fields.updated) if fields.updated else None,
            "resolved": str(fields.resolutiondate) if fields.resolutiondate else None,
            "due_date": str(fields.duedate) if fields.duedate else None,
            "story_points": story_points,
            "sprint": sprint_name,
            "labels": list(fields.labels) if fields.labels else [],
            "components": [c.name for c in fields.components] if fields.components else [],
            "blocked": fields.status.name.lower() == 'blocked' if fields.status else False,
            "epic": getattr(fields, 'epic', {}).get('name') if hasattr(fields, 'epic') and fields.epic else None
        }
    
    def full_sync(self, board_id: Optional[int] = None, project_key: Optional[str] = None) -> Dict:
        """Perform full sync of Jira data"""
        result = {
            "success": True,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "boards": [],
            "sprints": [],
            "issues": [],
            "velocity": [],
            "blocked_issues": [],
            "summary": {}
        }
        
        try:
            # Get boards
            result["boards"] = self.get_boards()
            
            # If no board specified, use first board
            if not board_id and result["boards"]:
                board_id = result["boards"][0]["id"]
            
            if board_id:
                # Get sprints
                result["sprints"] = self.get_sprints(board_id, state="active,closed,future")
                
                # Get velocity data
                result["velocity"] = self.get_velocity_data(board_id)
                
                # Get active sprint issues
                active_sprints = [s for s in result["sprints"] if s.get("state") == "active"]
                for sprint in active_sprints:
                    sprint_issues = self.get_sprint_issues(sprint["id"])
                    result["issues"].extend(sprint_issues)
            
            # Get blocked issues
            result["blocked_issues"] = self.get_blocked_issues(project_key)
            
            # Calculate summary
            all_issues = result["issues"]
            result["summary"] = {
                "total_issues": len(all_issues),
                "blocked_count": len(result["blocked_issues"]),
                "sprints_count": len(result["sprints"]),
                "avg_velocity": sum(v.get("velocity", 0) for v in result["velocity"]) / max(len(result["velocity"]), 1),
                "status_distribution": {}
            }
            
            # Calculate status distribution
            for issue in all_issues:
                status = issue.get("status", "Unknown")
                result["summary"]["status_distribution"][status] = result["summary"]["status_distribution"].get(status, 0) + 1
            
        except Exception as e:
            logger.error(f"Jira sync failed: {e}")
            result["success"] = False
            result["error"] = str(e)
        
        return result


# ============== GOOGLE SHEETS INTEGRATION ==============

class GoogleSheetsClient:
    """Google Sheets client for reading spreadsheet data"""
    
    def __init__(self, credentials):
        """Initialize with Google OAuth credentials"""
        from googleapiclient.discovery import build
        self.service = build('sheets', 'v4', credentials=credentials)
    
    def read_sheet(self, spreadsheet_id: str, range_name: str = "Sheet1") -> List[Dict]:
        """Read data from a Google Sheet and return as list of dicts"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values or len(values) < 2:
                return []
            
            # First row is headers
            headers = values[0]
            data = []
            
            for row in values[1:]:
                # Pad row if it's shorter than headers
                padded_row = row + [''] * (len(headers) - len(row))
                row_dict = dict(zip(headers, padded_row))
                data.append(row_dict)
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to read Google Sheet: {e}")
            raise
    
    def get_sheet_metadata(self, spreadsheet_id: str) -> Dict:
        """Get spreadsheet metadata including sheet names"""
        try:
            result = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            return {
                "title": result.get('properties', {}).get('title'),
                "sheets": [
                    {
                        "id": sheet.get('properties', {}).get('sheetId'),
                        "title": sheet.get('properties', {}).get('title'),
                        "row_count": sheet.get('properties', {}).get('gridProperties', {}).get('rowCount'),
                        "col_count": sheet.get('properties', {}).get('gridProperties', {}).get('columnCount')
                    }
                    for sheet in result.get('sheets', [])
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get sheet metadata: {e}")
            raise


def extract_spreadsheet_id(url_or_id: str) -> str:
    """Extract spreadsheet ID from a Google Sheets URL or return as-is if already an ID"""
    # If it's a URL, extract the ID
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url_or_id)
    if match:
        return match.group(1)
    # Otherwise assume it's already an ID
    return url_or_id


# ============== CLICKUP INTEGRATION ==============

class ClickUpClient:
    """ClickUp API v2 client for syncing tasks, lists, and spaces"""

    BASE_URL = "https://api.clickup.com/api/v2"

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.headers = {
            "Authorization": api_token,
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, params: dict = None, json_data: dict = None) -> Dict:
        """Make a synchronous HTTP request to the ClickUp API"""
        import requests
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=json_data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            if result is None:
                logger.warning(f"ClickUp API returned null JSON for {endpoint}")
                return {}
            return result
        except requests.exceptions.HTTPError as e:
            logger.error(f"ClickUp API error: {e} - {e.response.text if e.response else ''}")
            return None
        except Exception as e:
            logger.error(f"ClickUp request failed: {e}")
            return None

    def test_connection(self) -> Dict:
        """Test ClickUp connection and return user/workspace info"""
        try:
            data = self._request("GET", "/user")
            user = data.get("user", {})
            return {
                "success": True,
                "username": user.get("username"),
                "email": user.get("email"),
                "profile_picture": user.get("profilePicture")
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_teams(self) -> List[Dict]:
        """Get all workspaces (teams) the user has access to"""
        try:
            data = self._request("GET", "/team")
            teams = data.get("teams", [])
            return [{
                "id": str(team.get("id")),
                "name": team.get("name"),
                "members_count": len(team.get("members", []))
            } for team in teams]
        except Exception as e:
            logger.error(f"Failed to get ClickUp teams: {e}")
            return []

    def get_spaces(self, team_id: str) -> List[Dict]:
        """Get all spaces in a workspace"""
        try:
            data = self._request("GET", f"/team/{team_id}/space", params={"archived": "false"})
            spaces = data.get("spaces", [])
            return [{
                "id": str(space.get("id")),
                "name": space.get("name"),
                "private": space.get("private", False),
                "statuses": [s.get("status") for s in space.get("statuses", [])]
            } for space in spaces]
        except Exception as e:
            logger.error(f"Failed to get ClickUp spaces: {e}")
            return []

    def get_folders(self, space_id: str) -> List[Dict]:
        """Get all folders in a space"""
        try:
            data = self._request("GET", f"/space/{space_id}/folder", params={"archived": "false"})
            if data is None:
                logger.warning(f"ClickUp API returned None for folders (space_id={space_id})")
                return []
            folders = data.get("folders", [])
            return [{
                "id": str(folder.get("id")),
                "name": folder.get("name"),
                "list_count": len(folder.get("lists", []))
            } for folder in folders]
        except Exception as e:
            logger.error(f"Failed to get ClickUp folders: {e}")
            return []

    def get_lists(self, space_id: str, folder_id: str = None) -> List[Dict]:
        """Get all lists in a space or folder"""
        try:
            if folder_id:
                data = self._request("GET", f"/folder/{folder_id}/list", params={"archived": "false"})
            else:
                data = self._request("GET", f"/space/{space_id}/list", params={"archived": "false"})
            
            if data is None:
                logger.warning(f"ClickUp API returned None for lists (space_id={space_id}, folder_id={folder_id})")
                return []
            
            lists = data.get("lists", [])
            return [{
                "id": str(lst.get("id")),
                "name": lst.get("name"),
                "task_count": lst.get("task_count", 0),
                "status": lst.get("status", {}).get("status") if lst.get("status") else None,
                "folder_id": str(lst.get("folder", {}).get("id", "")) if lst.get("folder") else None
            } for lst in lists]
        except Exception as e:
            logger.error(f"Failed to get ClickUp lists: {e}")
            return []

    def get_tasks(self, list_id: str, include_subtasks: bool = True, page: int = 0) -> List[Dict]:
        """Get all tasks in a list with pagination"""
        try:
            params = {
                "archived": "false",
                "include_closed": "true",
                "subtasks": str(include_subtasks).lower(),
                "page": page
            }
            data = self._request("GET", f"/list/{list_id}/task", params=params)
            tasks = data.get("tasks", [])
            return [self._parse_task(task) for task in tasks]
        except Exception as e:
            logger.error(f"Failed to get ClickUp tasks: {e}")
            return []

    def get_all_tasks(self, list_id: str) -> List[Dict]:
        """Get ALL tasks from a list (handles pagination)"""
        all_tasks = []
        page = 0
        while True:
            tasks = self.get_tasks(list_id, page=page)
            if not tasks:
                break
            all_tasks.extend(tasks)
            if len(tasks) < 100:  # ClickUp returns max 100 per page
                break
            page += 1
        return all_tasks

    def _parse_task(self, task: Dict) -> Dict:
        """Parse a ClickUp task into standardized format"""
        # Extract assignees
        assignees = task.get("assignees", [])
        assignee_names = [a.get("username") or a.get("email", "") for a in assignees]

        # Extract priority
        priority_map = {1: "Urgent", 2: "High", 3: "Normal", 4: "Low"}
        priority_obj = task.get("priority")
        priority = None
        if priority_obj:
            priority = priority_obj.get("priority") if isinstance(priority_obj, dict) else None
            if priority and priority.isdigit():
                priority = priority_map.get(int(priority), priority)

        # Extract status
        status_obj = task.get("status", {})
        status = status_obj.get("status", "Unknown") if isinstance(status_obj, dict) else "Unknown"

        # Extract tags
        tags = [t.get("name", "") for t in task.get("tags", [])]

        # Extract custom fields
        custom_fields = {}
        for cf in task.get("custom_fields", []):
            cf_name = cf.get("name", "")
            cf_value = cf.get("value")
            if cf_value is not None:
                custom_fields[cf_name] = cf_value

        # Time estimate (ClickUp stores in milliseconds)
        time_estimate_ms = task.get("time_estimate")
        time_estimate_hours = round(time_estimate_ms / 3600000, 2) if time_estimate_ms else None

        # Time spent
        time_spent_ms = task.get("time_spent")
        time_spent_hours = round(time_spent_ms / 3600000, 2) if time_spent_ms else None

        # Convert timestamps (ClickUp uses milliseconds since epoch)
        def ms_to_iso(ms_val):
            if ms_val:
                try:
                    return datetime.fromtimestamp(int(ms_val) / 1000, tz=timezone.utc).isoformat()
                except (ValueError, TypeError, OSError):
                    return None
            return None

        # Dependencies
        dependencies = []
        for dep in task.get("dependencies", []):
            dependencies.append({
                "task_id": dep.get("task_id"),
                "depends_on": dep.get("depends_on"),
                "type": dep.get("type")
            })

        return {
            "key": task.get("id"),
            "summary": task.get("name"),
            "status": status,
            "priority": priority,
            "assignee": assignee_names[0] if assignee_names else None,
            "assignees": assignee_names,
            "created": ms_to_iso(task.get("date_created")),
            "updated": ms_to_iso(task.get("date_updated")),
            "due_date": ms_to_iso(task.get("due_date")),
            "start_date": ms_to_iso(task.get("start_date")),
            "resolved": ms_to_iso(task.get("date_closed")),
            "story_points": custom_fields.get("Story Points") or custom_fields.get("Points") or custom_fields.get("Estimate"),
            "time_estimate": time_estimate_hours,
            "time_spent": time_spent_hours,
            "tags": tags,
            "labels": tags,
            "list_name": task.get("list", {}).get("name") if task.get("list") else None,
            "space_name": task.get("space", {}).get("name") if isinstance(task.get("space"), dict) else None,
            "folder_name": task.get("folder", {}).get("name") if isinstance(task.get("folder"), dict) else None,
            "blocked": status.lower() in ["blocked", "on hold", "waiting"],
            "dependencies": dependencies,
            "custom_fields": custom_fields,
            "url": task.get("url")
        }

    def full_sync(self, space_id: str, list_ids: Optional[List[str]] = None) -> Dict:
        """Perform full sync of ClickUp data from a space"""
        result = {
            "success": True,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "space_id": space_id,
            "lists": [],
            "tasks": [],
            "summary": {}
        }

        try:
            # Get all lists in the space
            space_lists = self.get_lists(space_id)

            # Also get lists from folders
            folders = self.get_folders(space_id)
            for folder in folders:
                folder_lists = self.get_lists(space_id, folder_id=folder["id"])
                space_lists.extend(folder_lists)

            result["lists"] = space_lists

            # Filter to specified list IDs if provided
            if list_ids:
                target_lists = [l for l in space_lists if l["id"] in list_ids]
            else:
                target_lists = space_lists

            # Fetch tasks from each list
            all_tasks = []
            for lst in target_lists:
                tasks = self.get_all_tasks(lst["id"])
                all_tasks.extend(tasks)

            result["tasks"] = all_tasks

            # Calculate summary
            status_distribution = {}
            blocked_count = 0
            total_points = 0
            completed_points = 0
            overdue_count = 0
            now = datetime.now(timezone.utc)

            for task in all_tasks:
                status = task.get("status", "Unknown")
                status_distribution[status] = status_distribution.get(status, 0) + 1

                if task.get("blocked"):
                    blocked_count += 1

                points = task.get("story_points")
                if points:
                    try:
                        points = float(points)
                        total_points += points
                        if status.lower() in ["complete", "done", "closed", "resolved", "completed"]:
                            completed_points += points
                    except (ValueError, TypeError):
                        pass

                # Check overdue
                due = task.get("due_date")
                if due and status.lower() not in ["complete", "done", "closed", "resolved", "completed"]:
                    try:
                        due_dt = datetime.fromisoformat(due.replace('Z', '+00:00'))
                        if due_dt < now:
                            overdue_count += 1
                    except (ValueError, TypeError):
                        pass

            result["summary"] = {
                "total_tasks": len(all_tasks),
                "total_lists": len(target_lists),
                "blocked_count": blocked_count,
                "overdue_count": overdue_count,
                "total_points": total_points,
                "completed_points": completed_points,
                "status_distribution": status_distribution
            }

        except Exception as e:
            logger.error(f"ClickUp sync failed: {e}")
            result["success"] = False
            result["error"] = str(e)

        return result
