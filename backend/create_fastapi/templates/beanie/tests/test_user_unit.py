import pytest
from apiapp.modules.user.model import User

@pytest.mark.asyncio
async def test_user_password_hashing():
    user = User(
        username="testuser",
        name="Test User",
        hashed_password=""
    )
    user.set_password("securepassword")
    
    assert user.hashed_password != "securepassword"
    assert user.verify_password("securepassword")
    assert not user.verify_password("wrongpassword")

@pytest.mark.asyncio
async def test_username_normalization():
    # Note: Normalization happens via pydantic validation, so we instantiate the model
    user = User(
        username="TestUser",
        name="Test User",
        hashed_password="hash"
    )
    # Beanie/Pydantic validation runs on init usually if configured, 
    # but here let's check the validator logic specifically if needed.
    
    # Direct validator call check
    normalized = User.normalize_username("MixedCaseUser")
    assert normalized == "mixedcaseuser"

    # Model instantiation check
    user_model = User(username="UPPERCASE", name="Upper User", hashed_password="pw")
    assert user_model.username == "uppercase"
