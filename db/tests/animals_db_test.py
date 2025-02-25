import pytest
from db.animals_db import AnimalsInMemoryDB


@pytest.fixture
def db():
    """Fixture to create a new database instance for each test."""
    return AnimalsInMemoryDB()


def test_insert_image_url(db):
    """Test inserting and retrieving an image URL."""
    db.insert_image_url("https://example.com/lion.jpg", "lion")
    assert db.get_animal_name_by_url("https://example.com/lion.jpg") == "lion"


def test_get_animal_name_by_url_not_found(db):
    """Test retrieving an animal name with a non-existent URL."""
    assert db.get_animal_name_by_url("https://example.com/missing.jpg") is None


def test_insert_image_local_path(db):
    """Test inserting and retrieving a local image path."""
    db.insert_image_local_path("elephant", "/images/elephant.jpg")
    assert db.animal_images_local_paths["elephant"] == "/images/elephant.jpg"


def test_insert_animal_to_collateral_adjectives(db):
    """Test inserting and retrieving animals associated with collateral adjectives."""
    db.insert_animal_to_collateral_adjectives("aquatic", "dolphin")
    db.insert_animal_to_collateral_adjectives("aquatic", "whale")
    assert db.collateral_adjectives_to_animals["aquatic"] == ["dolphin", "whale"]


def test_insert_multiple_collateral_adjectives(db):
    """Test inserting animals under different collateral adjectives."""
    db.insert_animal_to_collateral_adjectives("nocturnal", "owl")
    db.insert_animal_to_collateral_adjectives("nocturnal", "bat")
    db.insert_animal_to_collateral_adjectives("furry", "rabbit")

    assert db.collateral_adjectives_to_animals["nocturnal"] == ["owl", "bat"]
    assert db.collateral_adjectives_to_animals["furry"] == ["rabbit"]


def test_empty_data_retrieval(db):
    """Test retrieving data from an empty database."""
    assert db.get_animal_name_by_url("https://example.com/nonexistent.jpg") is None
    assert db.animal_images_local_paths == {}
    assert db.collateral_adjectives_to_animals == {}


def test_overwrite_image_url(db):
    """Test overwriting an existing image URL."""
    db.insert_image_url("https://example.com/tiger.jpg", "tiger")
    db.insert_image_url("https://example.com/tiger.jpg", "panther")
    assert db.get_animal_name_by_url("https://example.com/tiger.jpg") == "panther"


def test_overwrite_local_path(db):
    """Test overwriting an existing local image path."""
    db.insert_image_local_path("wolf", "/images/wolf1.jpg")
    db.insert_image_local_path("wolf", "/images/wolf2.jpg")
    assert db.animal_images_local_paths["wolf"] == "/images/wolf2.jpg"


def test_persistence_of_data(db):
    """Test that data persists across operations within the same instance."""
    db.insert_image_url("https://example.com/cat.jpg", "cat")
    db.insert_image_local_path("dog", "/images/dog.jpg")
    db.insert_animal_to_collateral_adjectives("majestic", "eagle")

    assert db.get_animal_name_by_url("https://example.com/cat.jpg") == "cat"
    assert db.animal_images_local_paths["dog"] == "/images/dog.jpg"
    assert db.collateral_adjectives_to_animals["majestic"] == ["eagle"]
