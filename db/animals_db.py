"""This module implements an in-memory database for managing animal-related data.

The database maintains mappings between animals and their associated collateral adjectives,
image file paths, and image URLs. This can serve as a temporary storage solution for
applications that require fast lookups and insertions without a persistent database.
"""
from collections import defaultdict


class AnimalsInMemoryDB:
    """An in-memory database for managing animals, their associated collateral adjectives,
    and image information (both local file paths and URLs).

    Attributes:
        _collateral_adjectives_to_animals (defaultdict[str, list[str]]):
            A mapping of collateral adjectives to a list of corresponding animals.
        _animal_images_local_paths (dict[str, str]):
            A mapping of animal names to their corresponding local image file paths.
        _animal_image_urls (dict[str, str]):
            A mapping of image URLs to corresponding animal names.
    """

    def __init__(self):
        """Initializes the in-memory database with empty data structures."""
        self._collateral_adjectives_to_animals: defaultdict[str, list[str]] = defaultdict(list)
        self._animal_images_local_paths: dict[str, str] = {}
        self._animal_image_urls: dict[str, str] = {}

    def insert_image_url(self, image_url: str, animal_name: str):
        """Inserts an image URL and associates it with a specific animal.

        Args:
            image_url (str): The URL of the animal image.
            animal_name (str): The name of the animal in the image.
        """
        self._animal_image_urls[image_url] = animal_name

    def get_animal_name_by_url(self, image_url: str) -> str | None:
        """Retrieves the animal name associated with a given image URL.

        Args:
            image_url (str): The URL of the animal image.

        Returns:
            str | None: The name of the animal if found, otherwise None.
        """
        return self._animal_image_urls.get(image_url)

    def insert_image_local_path(self, animal_name: str, local_path: str):
        """Stores the local file path of an animal's image.

        Args:
            animal_name (str): The name of the animal.
            local_path (str): The local file path of the image.
        """
        self._animal_images_local_paths[animal_name] = local_path

    def insert_animal_to_collateral_adjectives(self, adjective: str, animal: str):
        """Associates an animal with a collateral adjective.

        Args:
            adjective (str): The collateral adjective.
            animal (str): The name of the animal.
        """
        self._collateral_adjectives_to_animals[adjective].append(animal)

    def get_all_data(self):
        """Prints all stored data in a structured and readable format."""
        print("=== Animals In Memory Database ===\n")

        print("📌 Collateral Adjectives to Animals:")
        if self._collateral_adjectives_to_animals:
            for adjective, animals in self._collateral_adjectives_to_animals.items():
                print(f"  - {adjective}: {', '.join(animals)}")
        else:
            print("  (No data)")

        print("\n📌 Animal Images (Local Paths):")
        if self._animal_images_local_paths:
            for animal, path in self._animal_images_local_paths.items():
                print(f"  - {animal}: {path}")
        else:
            print("  (No data)")

        print("\n📌 Animal Image URLs:")
        if self._animal_image_urls:
            for url, animal in self._animal_image_urls.items():
                print(f"  - {animal}: {url}")
        else:
            print("  (No data)")

        print("\n===================================")
