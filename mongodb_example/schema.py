import asyncio
import typing as t
import motor.motor_asyncio
from pydantic import BaseModel, EmailStr, Field
from beanie import init_beanie, Document
from bson import ObjectId
from datetime import datetime


# Database connection URL
MONGO_URI = "mongodb://username:password@localhost:27017/mydatabase?authSource=admin"
DATABASE_NAME = "mydatabase"
COLLECTION_NAME = "documents"

# Database session setup
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]


async def init():
    await init_beanie(database=db, document_models=[CTPModel, LPSModel, BSModel])


# Models and Pydantic schemas


class PromptModel(Document):
    """Mongo ORM model for the Prompt table."""
    prompt_id: str = Field(..., description="Unique identifier for the prompt")
    prompt_text: str = Field(..., description="Text of the prompt")
    prompt_type: str = Field(..., description="Type of the prompt (e.g., 'LPS', 'BS')")
    last_updated: t.Optional[datetime] = Field(default_factory=datetime.utcnow, description="Timestamp of last update")

    class Settings:
        collection = "prompts"

    class Config:
        json_encoders = {ObjectId: str}
        from_attributes = True


class CTPModel(Document):
    """Mongo ORM model for the CTPs table."""
    cpt_id: str = Field(..., description="Unique identifier for the CPT")
    apollo_index_id: str = Field(..., description="Index reference")
    lps_id : t.Optional[int] = Field(default=None, description="LPS identifier")
    bs_id: t.Optional[int] = Field(default=None, description="BS identifier")
    ctp_metadata: t.Dict = Field(..., description="Metadata associated with CPT")
    categories: t.List[str] = Field(default=[], description="List of category labels")
    last_updated: t.Optional[datetime] = Field(default_factory=datetime.utcnow, description="Timestamp of last update")

    class Settings:
        collection = "ctps"

    class Config:
        json_encoders = {ObjectId: str}
        from_attributes = True


class LPSModel(Document):
    """Mongo ORM model for the LPS table."""
    ctp_id: str = Field(..., description="Unique identifier for the CTP")
    lps_content: t.Dict[str, str] = Field(default={}, description="LPS sections and their text content")
    llm_judge_rating: t.Optional[float] = Field(default=0.0, description="LLM judge composite rating for the LPS")
    llm_judge_scores: t.Optional[dict] = Field(default={}, description="LLM judge scores for each section and metric")
    last_updated: t.Optional[datetime] = Field(default_factory=datetime.utcnow, description="Timestamp of last update")

    class Settings:
        collection = "lps"

    class Config:
        json_encoders = {ObjectId: str}
        from_attributes = True


class BSModel(Document):
    """Mongo ORM model for the BS table."""
    ctp_id: str = Field(..., description="Unique identifier for the CTP")
    bs_content: t.Dict[str, str] = Field(default={}, description="BS sections and their text content")
    llm_judge_rating: t.Optional[float] = Field(default=0.0, description="LLM judge composite rating for the BS")
    llm_judge_scores: t.Optional[dict] = Field(default={}, description="LLM judge scores for each section and metric")
    last_updated: t.Optional[datetime] = Field(default_factory=datetime.utcnow, description="Timestamp of last update")

    class Settings:
        collection = "bs"

    class Config:
        json_encoders = {ObjectId: str}
        from_attributes = True


# CRUD operations


async def create_ctp(new_ctp: CTPModel):
    await new_ctp.insert()
    return new_ctp.id


async def get_ctp(cpt_id: str):
    return await CTPModel.find_one(CTPModel.cpt_id == cpt_id)


async def update_ctp(cpt_id: str, lps_id: int = None, bs_id: int = None, new_metadata: dict = None, new_categories: t.List[str] = None):
    if lps_id is None and bs_id is None and new_metadata is None and new_categories is None:
        raise ValueError("At least one field must be updated")
    ctp = await CTPModel.find_one(CTPModel.cpt_id == cpt_id)
    if ctp:
        ctp.lps_id = lps_id
        ctp.bs_id = bs_id
        ctp.ctp_metadata = new_metadata
        ctp.categories = new_categories
        ctp.last_updated = datetime.utcnow()
        await ctp.save()


async def delete_ctp(cpt_id: int):
    ctp = await CTPModel.find_one(CTPModel.cpt_id == cpt_id)
    if ctp:
        await ctp.delete()


async def create_lps(new_lps: LPSModel):
    await new_lps.insert()
    return new_lps.id


async def get_lps(ctp_id: str):
    return await LPSModel.find_one(LPSModel.ctp_id == ctp_id)


async def update_lps(ctp_id: str, new_content: dict = None, new_judge_rating: float = None, new_judge_scores: dict = None):
    if new_content is None and new_judge_rating is None and new_judge_scores is None:
        raise ValueError("At least one field must be updated")
    lps = await LPSModel.find_one(LPSModel.ctp_id == ctp_id)
    if lps:
        lps.lps_content = new_content
        lps.llm_judge_rating = new_judge_rating
        lps.llm_judge_scores = new_judge_scores
        lps.last_updated = datetime.utcnow()
        await lps.save()


async def delete_lps(ctp_id: str):
    lps = await LPSModel.find_one(LPSModel.ctp_id == ctp_id)
    if lps:
        await lps.delete()


async def create_bs(new_bs: BSModel):
    await new_bs.insert()
    return new_bs.id


async def get_bs(ctp_id: str):
    return await BSModel.find_one(BSModel.ctp_id == ctp_id)


async def update_bs(ctp_id: str, new_content: dict = None, new_judge_rating: float = None, new_judge_scores: dict = None):
    if new_content is None and new_judge_rating is None and new_judge_scores is None:
        raise ValueError("At least one field must be updated")
    bs = await BSModel.find_one(BSModel.ctp_id == ctp_id)
    if bs:
        bs.bs_content = new_content
        bs.llm_judge_rating = new_judge_rating
        bs.llm_judge_scores = new_judge_scores
        bs.last_updated = datetime.utcnow()
        await bs.save()


async def delete_bs(ctp_id: str):
    bs = await BSModel.find_one(BSModel.ctp_id == ctp_id)
    if bs:
        await bs.delete()


# Example usage


async def main():

    # Initialize the database connection
    await init()

    # Insert a new CTP
    new_ctp = CTPModel(
        cpt_id="cpt_123",
        apollo_index_id="index_123",
        ctp_metadata={"description": "Sample CTP metadata"},
        categories=["finance", "analytics"],
    )
    new_id = await create_ctp(new_ctp)
    print(f"Inserted CTP with ID: {new_id}")
    # Retrieve CTP
    ctp = await get_ctp("cpt_123")
    print(f"Fetched CTP: {ctp}")
    # Update CTP
    await update_ctp("cpt_123", lps_id=1, bs_id=2, new_metadata={"description": "Updated metadata"}, new_categories=["finance"])
    # Retrieve updated CTP
    updated_ctp = await get_ctp("cpt_123")
    print(f"Updated CTP: {updated_ctp}")
    # Delete CTP
    await delete_ctp("cpt_123")
    print("CTP deleted")

    # Insert a new LPS
    new_lps = LPSModel(
        ctp_id="cpt_123",
        lps_content={"section1": "Content of section 1", "section2": "Content of section 2"},
        llm_judge_rating=4.5,
        llm_judge_scores={"section1": 4.0, "section2": 5.0},
    )
    new_lps_id = await create_lps(new_lps)
    print(f"Inserted LPS with ID: {new_lps_id}")
    # Retrieve LPS
    lps = await get_lps("cpt_123")
    print(f"Fetched LPS: {lps}")
    # Update LPS
    await update_lps("cpt_123", new_content={"section1": "Updated content"}, new_judge_rating=4.8)
    # Retrieve updated LPS
    updated_lps = await get_lps("cpt_123")
    print(f"Updated LPS: {updated_lps}")
    # Delete LPS
    await delete_lps("cpt_123")
    print("LPS deleted")

    # Insert a new BS
    new_bs = BSModel(
        ctp_id="cpt_123",
        bs_content={"section1": "Content of section 1", "section2": "Content of section 2"},
        llm_judge_rating=4.5,
        llm_judge_scores={"section1": 4.0, "section2": 5.0},
    )
    new_bs_id = await create_bs(new_bs)
    print(f"Inserted BS with ID: {new_bs_id}")
    # Retrieve BS
    bs = await get_bs("cpt_123")
    print(f"Fetched BS: {bs}")
    # Update BS
    await update_bs("cpt_123", new_content={"section1": "Updated content"}, new_judge_rating=4.8)
    # Retrieve updated BS
    updated_bs = await get_bs("cpt_123")
    print(f"Updated BS: {updated_bs}")
    # Delete BS
    await delete_bs("cpt_123")
    print("BS deleted")

    # Close the database connection
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
