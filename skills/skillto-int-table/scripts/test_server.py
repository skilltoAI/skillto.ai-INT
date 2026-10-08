import tempfile
import unittest
from pathlib import Path

import server


class TableServerTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        server.ROOT = Path(self.directory.name)
        server.CATALOG = server.ROOT / "catalog.json"
        server.TABLES = server.ROOT / "tables"

    def tearDown(self):
        self.directory.cleanup()

    def test_workspace_review_and_filters(self):
        base = server.table_workspace({"action": "create", "level": "knowledge_base", "name": "Research"})
        project = server.table_workspace({"action": "create", "level": "project", "knowledgeBaseId": base["id"], "name": "Launch"})
        table = server.table_workspace({"action": "create", "level": "table", "knowledgeBaseId": base["id"], "projectId": project["id"], "name": "Assets"})
        table_id = table["id"]
        server.table_define({"tableId": table_id, "fields": [{"name": "date", "label": "Date", "type": "date"}]})
        row = server.table_save_row({"tableId": table_id, "fields": {"title": "Demo", "date": "2026-09-30"}})
        tag = server.table_tags({"tableId": table_id, "action": "create", "name": "Approved"})
        server.table_review({"tableId": table_id, "rowId": row["id"], "score": 4, "note": "Clear", "tagIds": [tag["id"]]})
        result = server.table_query({"tableId": table_id, "search": "demo", "filters": [{"field": "date", "operator": "between", "value": ["2026-09-01", "2026-09-30"]}], "tagIds": [tag["id"]], "scoreStatus": "scored"})
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["rows"][0]["rating"]["score"], 4)
        server.table_tags({"tableId": table_id, "action": "rename", "tagId": tag["id"], "name": "Ready"})
        self.assertEqual(server.table_query({"tableId": table_id, "tagIds": [tag["id"]]})["count"], 1)
        server.table_tags({"tableId": table_id, "action": "delete", "tagId": tag["id"]})
        self.assertEqual(server.table_query({"tableId": table_id})["rows"][0]["tagIds"], [])
        server.table_save_row({"tableId": table_id, "action": "delete", "rowId": row["id"]})
        stored = server.load_table(table_id)
        self.assertEqual(stored["history"][-1]["before"]["id"], row["id"])
        self.assertEqual(server.table_query({"tableId": table_id})["count"], 0)
        with self.assertRaisesRegex(ValueError, "not empty"):
            server.table_workspace({"action": "delete", "level": "table", "knowledgeBaseId": base["id"],
                                    "projectId": project["id"], "id": table_id})

    def test_short_video_info_validation(self):
        table_id = server.identifier()
        server.write_json(server.table_path(table_id), {"id": table_id, "title": "Videos", "fields": [
            {"name": "recentVideos", "type": "short_video_info"}], "tags": [], "rows": [], "history": []})
        video = {"id": "123", "title": "Clip", "videoUrl": "https://www.douyin.com/video/123",
                 "playCount": None, "likeCount": 10, "collectCount": 2, "shareCount": 1, "commentCount": 0}
        row = server.table_save_row({"tableId": table_id, "fields": {"recentVideos": [video]}})
        self.assertEqual(row["fields"]["recentVideos"][0]["playCount"], None)
        with self.assertRaisesRegex(ValueError, "HTTP source URL"):
            server.table_save_row({"tableId": table_id, "fields": {"recentVideos": [{**video, "videoUrl": "javascript:alert(1)"}]}})

    def test_row_multiple_tags_persist_and_can_be_removed_individually(self):
        table_id = server.identifier()
        server.write_json(server.table_path(table_id), {"id": table_id, "title": "Accounts", "fields": [],
                                                        "tags": [], "rows": [], "history": []})
        row = server.table_save_row({"tableId": table_id, "fields": {"accountName": "Demo"}})
        first = server.table_tags({"tableId": table_id, "action": "create", "name": "Creator"})
        second = server.table_tags({"tableId": table_id, "action": "create", "name": "Partner"})
        with self.assertRaisesRegex(ValueError, "already exists"):
            server.table_tags({"tableId": table_id, "action": "create", "name": "creator"})
        server.table_review({"tableId": table_id, "rowId": row["id"], "tagIds": [first["id"], second["id"]]})
        self.assertEqual(server.load_table(table_id)["rows"][0]["tagIds"], [first["id"], second["id"]])
        server.table_review({"tableId": table_id, "rowId": row["id"], "tagIds": [second["id"]]})
        stored = server.load_table(table_id)["rows"][0]
        self.assertEqual(stored["tagIds"], [second["id"]])
        self.assertEqual(stored["fields"]["accountName"], "Demo")
        self.assertEqual([event["action"] for event in stored["history"]][-2:], ["set_row_tags", "set_row_tags"])

    def test_candidate_images_can_be_selected_and_cleared(self):
        table_id = server.identifier()
        server.write_json(server.table_path(table_id), {"id": table_id, "title": "Concepts", "fields": [
            {"name": "outfitA", "type": "image", "candidateGroup": "wardrobe"},
            {"name": "outfitB", "type": "image", "candidateGroup": "wardrobe"},
            {"name": "cover", "type": "image"}], "tags": [], "rows": [], "history": []})
        row = server.table_save_row({"tableId": table_id, "fields": {
            "title": "Demo", "outfitA": "/generated/a.png", "outfitB": "/generated/b.png",
            "cover": "/generated/cover.png"}})
        chosen = server.table_select_candidates({"tableId": table_id, "rowId": row["id"],
                                                  "imageFields": ["outfitA", "outfitB"]})
        self.assertEqual(chosen["fields"]["selectedCandidateImages"], ["outfitA", "outfitB"])
        self.assertEqual(server.table_query({"tableId": table_id})["rows"][0]["fields"]["title"], "Demo")
        with self.assertRaisesRegex(ValueError, "populated candidate"):
            server.table_select_candidates({"tableId": table_id, "rowId": row["id"],
                                             "imageFields": ["cover"]})
        server.table_save_row({"tableId": table_id, "action": "update", "rowId": row["id"],
                               "fields": {"outfitA": "/generated/new-a.png"}})
        stored = server.load_table(table_id)["rows"][0]
        self.assertEqual(stored["fields"]["selectedCandidateImages"], ["outfitB"])
        server.table_select_candidates({"tableId": table_id, "rowId": row["id"], "imageFields": []})
        stored = server.load_table(table_id)["rows"][0]
        self.assertEqual(stored["fields"]["selectedCandidateImages"], [])
        self.assertEqual(stored["history"][-1]["action"], "select_candidate_images")


if __name__ == "__main__":
    unittest.main()
