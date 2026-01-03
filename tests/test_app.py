"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        name: {"participants": activity["participants"].copy() if "participants" in activity else []}
        for name, activity in activities.items()
    }
    
    yield
    
    # Restore original state
    for name, activity in activities.items():
        if "participants" in activity:
            activity["participants"] = original_activities[name]["participants"]


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_get_activities_has_required_fields(self, client, reset_activities):
        """Test that activities have required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            assert "description" in activity
            assert "schedule" in activity
            assert "max_participants" in activity
            assert "participants" in activity
            assert isinstance(activity["participants"], list)
    
    def test_chess_club_has_initial_participants(self, client, reset_activities):
        """Test that Chess Club has the initial participants"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert "michael@mergington.edu" in chess_club["participants"]
        assert "daniel@mergington.edu" in chess_club["participants"]


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_new_participant(self, client, reset_activities):
        """Test signing up a new participant"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Signed up" in data["message"]
        assert "newstudent@mergington.edu" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        assert "newstudent@mergington.edu" in activities_response.json()["Chess Club"]["participants"]
    
    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signing up for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_duplicate_participant(self, client, reset_activities):
        """Test that a participant cannot sign up twice for the same activity"""
        # First signup
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": "duplicate@mergington.edu"}
        )
        assert response1.status_code == 200
        
        # Second signup with same email
        response2 = client.post(
            "/activities/Chess Club/signup",
            params={"email": "duplicate@mergington.edu"}
        )
        
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_existing_participant_fails(self, client, reset_activities):
        """Test that an existing participant cannot sign up again"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "michael@mergington.edu"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_with_special_characters_in_activity_name(self, client, reset_activities):
        """Test signup with URL-encoded activity names"""
        # Basketball Team should work
        response = client.post(
            "/activities/Basketball%20Team/signup",
            params={"email": "basketball@mergington.edu"}
        )
        
        assert response.status_code == 200
        
        # Verify participant was added
        activities_response = client.get("/activities")
        assert "basketball@mergington.edu" in activities_response.json()["Basketball Team"]["participants"]


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""
    
    def test_remove_existing_participant(self, client, reset_activities):
        """Test removing an existing participant"""
        # First, verify the participant exists
        activities_before = client.get("/activities").json()
        assert "michael@mergington.edu" in activities_before["Chess Club"]["participants"]
        
        # Remove the participant
        response = client.delete(
            "/activities/Chess Club/participants/michael@mergington.edu"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Removed" in data["message"]
        assert "michael@mergington.edu" in data["message"]
        
        # Verify participant was removed
        activities_after = client.get("/activities").json()
        assert "michael@mergington.edu" not in activities_after["Chess Club"]["participants"]
    
    def test_remove_from_nonexistent_activity(self, client, reset_activities):
        """Test removing a participant from an activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent Club/participants/student@mergington.edu"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_remove_nonexistent_participant(self, client, reset_activities):
        """Test removing a participant that doesn't exist in the activity"""
        response = client.delete(
            "/activities/Chess Club/participants/nonexistent@mergington.edu"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "Participant not found" in data["detail"]
    
    def test_remove_participant_with_special_characters(self, client, reset_activities):
        """Test removing a participant with URL-encoded characters"""
        # First add a participant
        client.post(
            "/activities/Tennis Club/signup",
            params={"email": "test.student@mergington.edu"}
        )
        
        # Remove with URL encoding
        response = client.delete(
            "/activities/Tennis%20Club/participants/test.student%40mergington.edu"
        )
        
        assert response.status_code == 200
        
        # Verify removal
        activities_response = client.get("/activities")
        assert "test.student@mergington.edu" not in activities_response.json()["Tennis Club"]["participants"]
    
    def test_remove_and_readd_participant(self, client, reset_activities):
        """Test that a participant can be removed and re-added"""
        email = "flexible@mergington.edu"
        activity = "Drama Club"
        
        # Add participant
        response1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Remove participant
        response2 = client.delete(
            f"/activities/{activity}/participants/{email}"
        )
        assert response2.status_code == 200
        
        # Re-add participant
        response3 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response3.status_code == 200
        
        # Verify participant is in activity
        activities_response = client.get("/activities")
        assert email in activities_response.json()[activity]["participants"]


class TestIntegration:
    """Integration tests for the API"""
    
    def test_signup_and_remove_workflow(self, client, reset_activities):
        """Test a complete signup and remove workflow"""
        email = "integration@mergington.edu"
        activity = "Robotics Club"
        
        # Get initial state
        initial = client.get("/activities").json()
        initial_count = len(initial[activity]["participants"])
        
        # Sign up
        response1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Verify signup
        after_signup = client.get("/activities").json()
        assert len(after_signup[activity]["participants"]) == initial_count + 1
        assert email in after_signup[activity]["participants"]
        
        # Remove
        response2 = client.delete(
            f"/activities/{activity}/participants/{email}"
        )
        assert response2.status_code == 200
        
        # Verify removal
        final = client.get("/activities").json()
        assert len(final[activity]["participants"]) == initial_count
        assert email not in final[activity]["participants"]
    
    def test_multiple_participants_operations(self, client, reset_activities):
        """Test operations with multiple participants"""
        activity = "Art Studio"
        emails = [
            "artist1@mergington.edu",
            "artist2@mergington.edu",
            "artist3@mergington.edu"
        ]
        
        # Add multiple participants
        for email in emails:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all were added
        all_activities = client.get("/activities").json()
        for email in emails:
            assert email in all_activities[activity]["participants"]
        
        # Remove one
        response = client.delete(
            f"/activities/{activity}/participants/{emails[1]}"
        )
        assert response.status_code == 200
        
        # Verify selective removal
        final = client.get("/activities").json()
        assert emails[0] in final[activity]["participants"]
        assert emails[1] not in final[activity]["participants"]
        assert emails[2] in final[activity]["participants"]
