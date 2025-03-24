import pytest
import asyncio
import unittest
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient
from datetime import datetime

from schema import CTPModel, LPSModel, BSModel, PromptModel


@pytest.mark.asyncio
class TestCTPModel(unittest.TestCase):
    """Class-based unit tests for CTPModel CRUD operations."""

    async def setup(self):
        """Setup an in-memory MongoDB instance and initialize the collection before each test."""
        self.client = AsyncMongoMockClient()
        self.db = self.client["test_database"]
        await init_beanie(database=self.db, document_models=[CTPModel])

    async def teardown(self):
        """Cleanup after each test to ensure isolation."""
        await self.db.drop_collection("ctps")

    async def test_create_ctp(self):
        """Test inserting a new CTP document."""
        new_ctp = CTPModel(
            cpt_id="ctp123",
            apollo_index_id="index123",
            lps_id=None,
            bs_id=None,
            ctp_metadata={"key": "value"},
            categories=["category1", "category2"],
            last_updated=datetime.utcnow(),
        )
        await new_ctp.insert()
        found_ctp = await CTPModel.find_one(CTPModel.cpt_id == "ctp123")
        assert found_ctp is not None
        assert found_ctp.cpt_id == "ctp123"
        assert found_ctp.ctp_metadata["key"] == "value"

    async def test_update_ctp(self):
        """Test updating an existing CTP document."""
        ctp = CTPModel(
            cpt_id="ctp123",
            apollo_index_id="index123",
            lps_id=None,
            bs_id=None,
            ctp_metadata={"key": "value"},
            categories=["category1", "category2"],
            last_updated=datetime.utcnow(),
        )
        await ctp.insert()
        # Update the document
        ctp.ctp_metadata["key"] = "Updated metadata"
        ctp.last_updated = datetime.utcnow()
        await ctp.save()
        await asyncio.sleep(0.1)  # Ensure the last_updated field is updated
        updated_ctp = await CTPModel.find_one(CTPModel.cpt_id == "ctp123")
        assert updated_ctp is not None
        assert updated_ctp.ctp_metadata["key"] == "Updated metadata"

    async def test_delete_ctp(self):
        """Test deleting a CTP document."""
        ctp = CTPModel(
            cpt_id="ctp123",
            apollo_index_id="index123",
            lps_id=None,
            bs_id=None,
            ctp_metadata={"key": "value"},
            categories=["category1", "category2"],
            last_updated=datetime.utcnow(),
        )
        await ctp.insert()
        # Ensure it's inserted
        ctp_in_db = await CTPModel.find_one(CTPModel.cpt_id == "ctp123")
        assert ctp_in_db is not None
        # Delete the document
        await ctp_in_db.delete()
        # Verify deletion
        deleted_ctp = await CTPModel.find_one(CTPModel.cpt_id == "ctp123")
        assert deleted_ctp is None


@pytest.mark.asyncio
class TestLPSModel(unittest.TestCase):
    """Class-based unit tests for LPSModel CRUD operations."""

    async def setup(self):
        """Setup an in-memory MongoDB instance and initialize the collection before each test."""
        self.client = AsyncMongoMockClient()
        self.db = self.client["test_database"]
        await init_beanie(database=self.db, document_models=[LPSModel])

    async def teardown(self):
        """Cleanup after each test to ensure isolation."""
        await self.db.drop_collection("lps")

    async def test_create_lps(self):
        """Test inserting a new LPS document."""
        new_lps = LPSModel(
            ctp_id="ctp123",
            lps_metadata={"key": "value"},
            last_updated=datetime.utcnow(),
        )
        await new_lps.insert()
        found_lps = await LPSModel.find_one(LPSModel.ctp_id == "ctp123")
        assert found_lps is not None
        assert found_lps.ctp_id == "ctp123"
        assert found_lps.lps_metadata["key"] == "value"

    async def test_update_lps(self):
        """Test updating an existing LPS document."""
        lps = LPSModel(
            ctp_id="ctp123",
            lps_metadata={"key": "value"},
            last_updated=datetime.utcnow(),
        )
        await lps.insert()
        # Update the document
        lps.lps_metadata["key"] = "Updated metadata"
        lps.last_updated = datetime.utcnow()
        await lps.save()
        await asyncio.sleep(0.1)
        # Ensure the last_updated field is updated
        updated_lps = await LPSModel.find_one(LPSModel.ctp_id == "ctp123")
        assert updated_lps is not None
        assert updated_lps.lps_metadata["key"] == "Updated metadata"

    async def test_delete_lps(self):
        """Test deleting an LPS document."""
        lps = LPSModel(
            ctp_id="ctp123",
            lps_metadata={"key": "value"},
            last_updated=datetime.utcnow(),
        )
        await lps.insert()
        # Ensure it's inserted
        lps_in_db = await LPSModel.find_one(LPSModel.ctp_id == "ctp123")
        assert lps_in_db is not None
        # Delete the document
        await lps_in_db.delete()
        # Verify deletion
        deleted_lps = await LPSModel.find_one(LPSModel.ctp_id == "ctp123")
        assert deleted_lps is None


@pytest.mark.asyncio
class TestBSModel(unittest.TestCase):
    """Class-based unit tests for BSModel CRUD operations."""

    async def setup(self):
        """Setup an in-memory MongoDB instance and initialize the collection before each test."""
        self.client = AsyncMongoMockClient()
        self.db = self.client["test_database"]
        await init_beanie(database=self.db, document_models=[BSModel])

    async def teardown(self):
        """Cleanup after each test to ensure isolation."""
        await self.db.drop_collection("bs")

    async def test_create_bs(self):
        """Test inserting a new BS document."""
        new_bs = BSModel(
            ctp_id="ctp123",
            bs_content={"key": "value"},
            llm_judge_rating=4.5,
            llm_judge_scores={"score1": 10, "score2": 20},
            last_updated=datetime.utcnow(),
        )
        await new_bs.insert()
        found_bs = await BSModel.find_one(BSModel.ctp_id == "ctp123")
        assert found_bs is not None
        assert found_bs.ctp_id == "ctp123"
        assert found_bs.bs_content["key"] == "value"

    async def test_update_bs(self):
        """Test updating an existing BS document."""
        bs = BSModel(
            ctp_id="ctp123",
            bs_content={"key": "value"},
            llm_judge_rating=4.5,
            llm_judge_scores={"score1": 10, "score2": 20},
            last_updated=datetime.utcnow(),
        )
        await bs.insert()
        # Update the document
        bs.bs_content["key"] = "Updated metadata"
        bs.last_updated = datetime.utcnow()
        await bs.save()
        await asyncio.sleep(0.1)
        # Ensure the last_updated field is updated
        updated_bs = await BSModel.find_one(BSModel.ctp_id == "ctp123")
        assert updated_bs is not None
        assert updated_bs.bs_content["key"] == "Updated metadata"

    async def test_delete_bs(self):
        """Test deleting a BS document."""
        bs = BSModel(
            ctp_id="ctp123",
            bs_content={"key": "value"},
            llm_judge_rating=4.5,
            llm_judge_scores={"score1": 10, "score2": 20},
            last_updated=datetime.utcnow(),
        )
        await bs.insert()
        # Ensure it's inserted
        bs_in_db = await BSModel.find_one(BSModel.ctp_id == "ctp123")
        assert bs_in_db is not None
        # Delete the document
        await bs_in_db.delete()
        # Verify deletion
        deleted_bs = await BSModel.find_one(BSModel.ctp_id == "ctp123")
        assert deleted_bs is None
