import requests
import sys
import json
from datetime import datetime
import time
import io

class DeliveryRiskRadarIntegrationTester:
    def __init__(self, base_url="https://execution-pulse.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None
        self.test_project_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        test_headers = {}
        
        if not files:  # Only set Content-Type for non-file uploads
            test_headers['Content-Type'] = 'application/json'
        
        if headers:
            test_headers.update(headers)
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, data=data, files=files, headers={'Authorization': test_headers.get('Authorization', '')})
                else:
                    response = requests.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if response.text:
                    try:
                        resp_json = response.json()
                        print(f"   Response: {json.dumps(resp_json, indent=2)[:200]}...")
                        return True, resp_json
                    except:
                        return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Raw response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

        return success, {}

    def test_health_check(self):
        """Test basic health check"""
        return self.run_test(
            "Health Check",
            "GET",
            "/api/health",
            200
        )

    def test_register(self):
        """Test user registration"""
        user_data = {
            "email": f"test_{datetime.now().strftime('%H%M%S')}@test.com",
            "password": "TestPass123!",
            "name": "Test User",
            "role": "admin"
        }
        success, response = self.run_test(
            "User Registration",
            "POST",
            "/api/auth/register",
            200,
            data=user_data
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response['user']['id']
            print(f"   Registered user ID: {self.user_id}")
        return success, response

    def test_login(self):
        """Test user login with demo credentials"""
        login_data = {
            "email": "demo@riskradar.com",
            "password": "demo123456"
        }
        success, response = self.run_test(
            "Demo User Login",
            "POST",
            "/api/auth/login",
            200,
            data=login_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response['user']['id']
            print(f"   Logged in as user ID: {self.user_id}")
        return success, response

    def test_profile(self):
        """Test get current user profile"""
        if not self.token:
            print("❌ No token available for profile test")
            return False, {}
        
        return self.run_test(
            "Get User Profile",
            "GET",
            "/api/auth/me",
            200
        )

    def test_create_project(self):
        """Test project creation"""
        if not self.token:
            print("❌ No token available for project creation")
            return False, {}
        
        project_data = {
            "name": f"Test Project {datetime.now().strftime('%H%M%S')}",
            "description": "Test project for risk analysis",
            "team_lead": "John Doe",
            "team_size": 5,
            "start_date": "2025-01-01",
            "target_end_date": "2025-06-30",
            "status": "active"
        }
        
        success, response = self.run_test(
            "Create Project",
            "POST",
            "/api/projects",
            200,
            data=project_data
        )
        
        if success and 'id' in response:
            self.test_project_id = response['id']
            print(f"   Created project ID: {self.test_project_id}")
        
        return success, response

    def test_get_projects(self):
        """Test getting all projects"""
        if not self.token:
            print("❌ No token available for get projects")
            return False, {}
        
        return self.run_test(
            "Get All Projects",
            "GET",
            "/api/projects",
            200
        )

    def test_dashboard_stats(self):
        """Test dashboard stats endpoint"""
        if not self.token:
            print("❌ No token available for dashboard stats")
            return False, {}
        
        return self.run_test(
            "Dashboard Stats",
            "GET",
            "/api/dashboard/stats",
            200
        )

    def test_create_manual_entry(self):
        """Test manual entry creation"""
        if not self.token or not self.test_project_id:
            print("❌ No token or project ID available for manual entry")
            return False, {}
        
        entry_data = {
            "project_id": self.test_project_id,
            "entry_type": "status_report",
            "title": "Weekly Status Update",
            "content": "Project is progressing well. Some minor blockers identified that need urgent attention.",
            "date": "2025-01-15"
        }
        
        return self.run_test(
            "Create Manual Entry",
            "POST",
            "/api/entries",
            200,
            data=entry_data
        )

    def test_get_notifications(self):
        """Test getting notifications"""
        if not self.token:
            print("❌ No token available for notifications")
            return False, {}
        
        return self.run_test(
            "Get Notifications",
            "GET",
            "/api/notifications",
            200
        )

    def test_jira_test_connection(self):
        """Test Jira test connection endpoint (should fail without config)"""
        if not self.token:
            print("❌ No token available for Jira test")
            return False, {}
        
        success, response = self.run_test(
            "Jira Test Connection (No Config)",
            "POST",
            "/api/jira/test-connection",
            400  # Expected to fail without configuration
        )
        return success, response

    def test_jira_boards(self):
        """Test Jira boards endpoint (should fail without config)"""
        if not self.token:
            print("❌ No token available for Jira boards test")
            return False, {}
        
        success, response = self.run_test(
            "Jira Boards (No Config)",
            "GET",
            "/api/jira/boards",
            400  # Expected to fail without configuration
        )
        return success, response

    def test_jira_sync(self):
        """Test Jira sync endpoint (should fail without config)"""
        if not self.token or not self.test_project_id:
            print("❌ No token or project ID for Jira sync test")
            return False, {}
        
        sync_data = {
            "project_id": self.test_project_id
        }
        
        success, response = self.run_test(
            "Jira Sync (No Config)",
            "POST", 
            "/api/jira/sync",
            400,  # Expected to fail without configuration
            data=sync_data
        )
        return success, response

    def test_google_sheets_status(self):
        """Test Google Sheets OAuth status"""
        if not self.token:
            print("❌ No token available for Google Sheets status test")
            return False, {}
        
        success, response = self.run_test(
            "Google Sheets OAuth Status",
            "GET",
            "/api/oauth/sheets/status",
            200
        )
        
        if success:
            print(f"   Sheets connected: {response.get('connected', False)}")
        return success, response

    def test_upload_preview_columns(self):
        """Test file upload preview columns endpoint"""
        if not self.token:
            print("❌ No token available for upload preview test")
            return False, {}
        
        # Create a test CSV file
        csv_content = "issue_key,summary,status,assignee,story_points\nTEST-1,Test Issue,Done,John Doe,5\nTEST-2,Another Issue,In Progress,Jane Smith,3"
        
        files = {
            'file': ('test.csv', io.StringIO(csv_content), 'text/csv')
        }
        
        success, response = self.run_test(
            "Upload Preview Columns",
            "POST",
            "/api/uploads/preview-columns",
            200,
            files=files
        )
        
        if success:
            print(f"   Detected columns: {response.get('columns', [])}")
            print(f"   Detected type: {response.get('detected_type', 'unknown')}")
        return success, response

    def test_upload_with_mapping(self):
        """Test file upload with column mapping"""
        if not self.token or not self.test_project_id:
            print("❌ No token or project ID for upload mapping test")
            return False, {}
        
        # Create a test CSV file
        csv_content = "ticket_id,description,current_state,owner,points\nTICK-1,Sample Task,Complete,Alice,8\nTICK-2,Another Task,Working,Bob,5"
        
        data = {
            'project_id': self.test_project_id,
            'data_type': 'auto',
            'column_mapping': json.dumps({
                'ticket_id': 'key',
                'description': 'summary', 
                'current_state': 'status',
                'owner': 'assignee',
                'points': 'story_points'
            })
        }
        
        files = {
            'file': ('mapped_test.csv', io.StringIO(csv_content), 'text/csv')
        }
        
        success, response = self.run_test(
            "Upload with Column Mapping",
            "POST",
            "/api/uploads/with-mapping",
            200,
            data=data,
            files=files
        )
        
        if success:
            print(f"   Records uploaded: {response.get('records_count', 0)}")
            print(f"   Data type: {response.get('data_type', 'unknown')}")
        return success, response

    def test_jira_settings_get(self):
        """Test get Jira settings"""
        if not self.token:
            print("❌ No token available for Jira settings test")
            return False, {}
        
        success, response = self.run_test(
            "Get Jira Settings",
            "GET",
            "/api/settings/jira",
            200
        )
        return success, response

    def test_google_sheets_settings_get(self):
        """Test get Google Sheets settings"""
        if not self.token:
            print("❌ No token available for Google Sheets settings test")
            return False, {}
        
        success, response = self.run_test(
            "Get Google Sheets Settings", 
            "GET",
            "/api/settings/google-sheets",
            200
        )
        return success, response

    def test_analyze_project_risk(self):
        """Test project risk analysis"""
        if not self.token or not self.test_project_id:
            print("❌ No token or project ID available for risk analysis")
            return False, {}
        
        success, response = self.run_test(
            "Analyze Project Risk",
            "POST",
            f"/api/projects/{self.test_project_id}/analyze",
            200
        )
        
        if success:
            print(f"   Risk Level: {response.get('risk_level', 'N/A')}")
            print(f"   Risk Score: {response.get('risk_score', 'N/A')}%")
        return success, response

    def test_generate_executive_report(self):
        """Test executive PDF report generation"""
        if not self.token:
            print("❌ No token available for executive report generation")
            return False, {}
        
        report_data = {
            "organization_name": "Test Organization",
            "include_projects": None  # Include all projects
        }
        
        success, response = self.run_test(
            "Generate Executive PDF Report",
            "POST",
            "/api/reports/executive",
            200,
            data=report_data
        )
        
        if success:
            print(f"   PDF report generated successfully")
        return success, response

    def test_generate_project_report(self):
        """Test single project PDF report generation"""
        if not self.token or not self.test_project_id:
            print("❌ No token or project ID available for project report")
            return False, {}
        
        success, response = self.run_test(
            "Generate Project PDF Report",
            "POST",
            f"/api/reports/project/{self.test_project_id}",
            200
        )
        
        if success:
            print(f"   Project PDF report generated successfully")
        return success, response

    def test_get_report_history(self):
        """Test report history endpoint"""
        if not self.token:
            print("❌ No token available for report history")
            return False, {}
        
        success, response = self.run_test(
            "Get Report History",
            "GET",
            "/api/reports/history",
            200
        )
        
        if success:
            print(f"   Found {len(response)} report(s) in history")
        return success, response

    def test_invalid_endpoints(self):
        """Test some invalid scenarios"""
        print("\n🔍 Testing Invalid Scenarios...")
        
        # Test invalid login
        invalid_login = self.run_test(
            "Invalid Login",
            "POST",
            "/api/auth/login",
            401,
            data={"email": "invalid@test.com", "password": "wrong"}
        )
        
        # Test unauthorized access
        temp_token = self.token
        self.token = "invalid_token"
        unauthorized = self.run_test(
            "Unauthorized Access",
            "GET",
            "/api/auth/me",
            401
        )
        self.token = temp_token
        
        # Test non-existent project
        nonexistent_project = self.run_test(
            "Non-existent Project",
            "GET",
            "/api/projects/invalid-id",
            404
        )
        
        return invalid_login[0] and unauthorized[0] and nonexistent_project[0]

def main():
    print("🚀 Starting Delivery Risk Radar Integration Tests...")
    print("="*70)
    
    tester = DeliveryRiskRadarIntegrationTester()
    
    # Test sequence - focused on PDF report generation features
    tests = [
        ("Health Check", tester.test_health_check),
        ("Demo User Login", tester.test_login),
        ("Create Test Project", tester.test_create_project),
        ("Create Manual Entry", tester.test_create_manual_entry),
        ("Analyze Project Risk", tester.test_analyze_project_risk),
        ("Generate Executive Report", tester.test_generate_executive_report),
        ("Generate Project Report", tester.test_generate_project_report),
        ("Get Report History", tester.test_get_report_history),
        ("Google Sheets Status", tester.test_google_sheets_status),
        ("Get Jira Settings", tester.test_jira_settings_get),
        ("Get Google Sheets Settings", tester.test_google_sheets_settings_get),
    ]
    
    failed_tests = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            if isinstance(success, tuple):
                success = success[0]
            if not success:
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            failed_tests.append(test_name)
        
        time.sleep(0.5)  # Small delay between tests
    
    # Print final results
    print("\n" + "="*70)
    print("📊 INTEGRATION TEST RESULTS SUMMARY")
    print("="*70)
    print(f"Total tests run: {tester.tests_run}")
    print(f"Tests passed: {tester.tests_passed}")
    print(f"Tests failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run*100):.1f}%")
    
    if failed_tests:
        print(f"\n❌ Failed tests: {', '.join(failed_tests)}")
    else:
        print("\n✅ All integration tests passed!")
    
    print("="*70)
    
    return 0 if len(failed_tests) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())