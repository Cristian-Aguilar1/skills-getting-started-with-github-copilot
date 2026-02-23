"""Integration tests for Mergington High School Activities API.

Tests follow the AAA (Arrange-Act-Assert) pattern:
- Arrange: Set up test data and fixtures
- Act: Perform the action being tested
- Assert: Verify the results
"""

import pytest
from urllib.parse import urlencode
from fastapi.testclient import TestClient
from src.app import app, activities


# Create test client
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test."""
    # Store original activities
    original_activities = {
        key: {
            "description": value["description"],
            "schedule": value["schedule"],
            "max_participants": value["max_participants"],
            "participants": value["participants"].copy(),
        }
        for key, value in activities.items()
    }

    yield

    # Restore original activities after test
    for key in activities:
        activities[key]["participants"] = original_activities[key]["participants"].copy()


class TestRootEndpoint:
    """Tests for GET / endpoint."""

    def test_root_redirects_to_static_index(self):
        # Arrange: Prepare the GET request to root

        # Act: Send request to root endpoint
        response = client.get("/", follow_redirects=False)

        # Assert: Verify redirect status and location
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Tests for GET /activities endpoint."""

    def test_get_all_activities_returns_dict(self):
        # Arrange: No setup needed, activities are pre-loaded

        # Act: Fetch all activities
        response = client.get("/activities")

        # Assert: Verify response structure
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_activity_has_required_fields(self):
        # Arrange: Fetch activities
        response = client.get("/activities")
        activities_data = response.json()

        # Act: Get the first activity
        first_activity_name = list(activities_data.keys())[0]
        first_activity = activities_data[first_activity_name]

        # Assert: Verify all required fields are present
        assert "description" in first_activity
        assert "schedule" in first_activity
        assert "max_participants" in first_activity
        assert "participants" in first_activity
        assert isinstance(first_activity["participants"], list)

    def test_activities_contain_participants(self):
        # Arrange: Request activities
        response = client.get("/activities")
        activities_data = response.json()

        # Act: Check if activities have participants
        activities_with_participants = [
            name for name, data in activities_data.items() if len(data["participants"]) > 0
        ]

        # Assert: Verify some activities have participants
        assert len(activities_with_participants) > 0


class TestSignupEndpoint:
    """Tests for POST /activities/{activity_name}/signup endpoint."""

    def test_signup_new_participant_succeeds(self):
        # Arrange: Prepare test data
        activity_name = "Chess Club"
        new_email = "newstudent@mergington.edu"
        initial_count = len(activities[activity_name]["participants"])

        # Act: Sign up new participant
        response = client.post(
            f"/activities/{activity_name}/signup?email={new_email}"
        )

        # Assert: Verify signup was successful
        assert response.status_code == 200
        assert response.json()["message"] == f"Signed up {new_email} for {activity_name}"
        assert new_email in activities[activity_name]["participants"]
        assert len(activities[activity_name]["participants"]) == initial_count + 1

    def test_signup_nonexistent_activity_returns_404(self):
        # Arrange: Use a non-existent activity name
        fake_activity = "Nonexistent Activity"
        email = "student@mergington.edu"

        # Act: Try to sign up for non-existent activity
        response = client.post(
            f"/activities/{fake_activity}/signup?email={email}"
        )

        # Assert: Verify 404 error
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_signup_duplicate_student_returns_400(self):
        # Arrange: Use existing participant from Chess Club
        activity_name = "Chess Club"
        existing_participant = activities[activity_name]["participants"][0]

        # Act: Try to sign up the same participant again
        response = client.post(
            f"/activities/{activity_name}/signup?email={existing_participant}"
        )

        # Assert: Verify 400 error for duplicate signup
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_multiple_different_students(self):
        # Arrange: Prepare multiple new students
        activity_name = "Programming Class"
        students = [
            "alice@mergington.edu",
            "bob@mergington.edu",
            "charlie@mergington.edu",
        ]
        initial_count = len(activities[activity_name]["participants"])

        # Act: Sign up multiple students
        for student in students:
            response = client.post(
                f"/activities/{activity_name}/signup?email={student}"
            )
            assert response.status_code == 200

        # Assert: Verify all students were added
        for student in students:
            assert student in activities[activity_name]["participants"]
        assert len(activities[activity_name]["participants"]) == initial_count + len(students)

    def test_signup_with_special_characters_in_email(self):
        # Arrange: Prepare email with special characters
        activity_name = "Art Studio"
        special_email = "student+tag@mergington.edu"
        encoded_params = urlencode({"email": special_email})

        # Act: Sign up with special character email
        response = client.post(
            f"/activities/{activity_name}/signup?{encoded_params}"
        )

        # Assert: Verify signup succeeds with special character email
        assert response.status_code == 200
        assert special_email in activities[activity_name]["participants"]


class TestUnregisterEndpoint:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint."""

    def test_unregister_existing_participant_succeeds(self):
        # Arrange: Get an existing participant
        activity_name = "Chess Club"
        participant_to_remove = activities[activity_name]["participants"][0]
        initial_count = len(activities[activity_name]["participants"])

        # Act: Unregister the participant
        response = client.delete(
            f"/activities/{activity_name}/unregister?email={participant_to_remove}"
        )

        # Assert: Verify unregister was successful
        assert response.status_code == 200
        assert response.json()["message"] == f"Unregistered {participant_to_remove} from {activity_name}"
        assert participant_to_remove not in activities[activity_name]["participants"]
        assert len(activities[activity_name]["participants"]) == initial_count - 1

    def test_unregister_nonexistent_activity_returns_404(self):
        # Arrange: Use a non-existent activity
        fake_activity = "Nonexistent Activity"
        email = "student@mergington.edu"

        # Act: Try to unregister from non-existent activity
        response = client.delete(
            f"/activities/{fake_activity}/unregister?email={email}"
        )

        # Assert: Verify 404 error
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_unregister_non_participant_returns_400(self):
        # Arrange: Use a student not signed up for the activity
        activity_name = "Basketball Team"
        non_participant = "notstudent@mergington.edu"

        # Act: Try to unregister someone not registered
        response = client.delete(
            f"/activities/{activity_name}/unregister?email={non_participant}"
        )

        # Assert: Verify 400 error
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_unregister_and_signup_again(self):
        # Arrange: Get an existing participant
        activity_name = "Tennis Club"
        participant = activities[activity_name]["participants"][0]

        # Act: Unregister the participant
        response1 = client.delete(
            f"/activities/{activity_name}/unregister?email={participant}"
        )
        assert response1.status_code == 200

        # Act: Sign them up again
        response2 = client.post(
            f"/activities/{activity_name}/signup?email={participant}"
        )

        # Assert: Verify the participant was re-registered
        assert response2.status_code == 200
        assert participant in activities[activity_name]["participants"]

    def test_unregister_multiple_participants(self):
        # Arrange: Get participants from an activity
        activity_name = "Debate Team"
        participants_to_remove = activities[activity_name]["participants"].copy()
        initial_count = len(participants_to_remove)

        # Act: Unregister each participant
        for participant in participants_to_remove:
            response = client.delete(
                f"/activities/{activity_name}/unregister?email={participant}"
            )
            assert response.status_code == 200

        # Assert: Verify all participants were removed
        assert len(activities[activity_name]["participants"]) == 0
        assert len(activities[activity_name]["participants"]) == initial_count - len(participants_to_remove)
