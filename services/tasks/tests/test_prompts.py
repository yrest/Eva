import unittest

from src.prompts import build_system_prompt


class BuildSystemPromptTests(unittest.TestCase):
    def test_includes_registered_skills(self):
        prompt = build_system_prompt(
            registered_servers=[
                {"id": "fs-1", "name": "Office Desktop", "type": "filesystem", "url": "http://fs"},
                {"id": "vec-1", "name": "Local Qdrant", "type": "vector", "url": "http://vec"},
            ],
            collection_schemas={
                "filesystem_code": {
                    "description": "Indexed code",
                    "schema": {"path": "str", "language": "str"},
                }
            },
            registered_skills=[
                {
                    "name": "index_filesystems",
                    "description": "Index files from filesystems into vectors",
                    "tool_names": ["list_directory", "read_file", "embed_text", "upsert_vectors"],
                    "senses": ["filesystem", "vector"],
                    "triggers": ["index", "filesystems"],
                }
            ],
        )

        self.assertIn("REGISTERED SKILLS:", prompt)
        self.assertIn("index_filesystems", prompt)
        self.assertIn("Tools: list_directory, read_file, embed_text, upsert_vectors", prompt)
        self.assertIn("Senses: filesystem, vector", prompt)
        self.assertIn("Triggers: index, filesystems", prompt)


if __name__ == "__main__":
    unittest.main()
