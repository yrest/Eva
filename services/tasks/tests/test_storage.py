import tempfile
import unittest

from src.storage import FileStorage


class FileStorageRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = FileStorage(base_path=self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initializes_registry_files(self):
        self.assertTrue(self.storage.registry_file.exists())
        self.assertTrue(self.storage.collections_file.exists())
        self.assertTrue(self.storage.skills_file.exists())

    def test_can_register_and_update_skill(self):
        skill = self.storage.add_skill(
            name="search_code",
            description="Search code using vector and filesystem tools",
            tool_names=["search_vectors", "read_file"],
            senses=["vector", "filesystem"],
            triggers=["search", "code"],
        )

        self.assertEqual(skill["name"], "search_code")
        self.assertEqual(len(self.storage.list_skills()), 1)
        self.assertEqual(self.storage.get_skill_by_name("search_code")["id"], skill["id"])

        updated = self.storage.update_skill(skill["id"], {"enabled": False})
        self.assertFalse(updated["enabled"])
        self.assertEqual(self.storage.list_skills(), [])
        self.assertEqual(len(self.storage.list_skills(enabled_only=False)), 1)

    def test_rejects_duplicate_skill_names(self):
        self.storage.add_skill(
            name="search_code",
            description="Search code using vector and filesystem tools",
        )

        with self.assertRaises(ValueError):
            self.storage.add_skill(
                name="search_code",
                description="Duplicate",
            )

    def test_existing_mcp_server_registry_still_works(self):
        server = self.storage.add_server(
            name="Office Desktop",
            type="filesystem",
            url="http://localhost:8005/",
            auth_token="token-123",
            capabilities={"read": True},
        )

        self.assertEqual(server["url"], "http://localhost:8005")
        self.assertEqual(self.storage.get_server(server["id"])["name"], "Office Desktop")
        self.assertEqual(len(self.storage.list_servers()), 1)


if __name__ == "__main__":
    unittest.main()
