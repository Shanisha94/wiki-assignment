from collections import defaultdict


class AnimalsInMemoryDB:
    def __init__(self):
        self._collateral_adjectives_to_animals: defaultdict[str, list[str]] = defaultdict(list)  # Collateral adjectives to list of animals
        self._animal_images_local_paths: dict[str, str] = {}  # Map animal to its image local file path
        self._animal_image_urls: dict[str, str] = {} # Image URL -> Animal Name

    def insert_image_url(self, image_url: str, animal_name: str):
        self._animal_image_urls[image_url] = animal_name

    def get_animal_name_by_url(self, image_url: str):
        return self._animal_image_urls.get(image_url)

    def insert_image_local_path(self, animal_name: str, local_path: str):
        self._animal_images_local_paths[animal_name] = local_path

    def insert_animal_to_collateral_adjectives(self, adjective, animal):
        self._collateral_adjectives_to_animals[adjective].append(animal)