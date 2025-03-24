from sqlalchemy import (
    create_engine,
    ForeignKey,
    Column,
    Integer,
    Float,
    String,
    DateTime,
    Boolean,
)
from sqlalchemy.types import TEXT, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB, ARRAY as PG_ARRAY
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
from sqlalchemy.sql.functions import coalesce
from sqlalchemy import inspect
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
import typing as t
import json
import sqlalchemy
import os


# Database connection URL
POSTGRES_URL = "postgresql://postgres:postgres@localhost:5432/postgres"
DATABASE_URL = POSTGRES_URL if os.getenv("ENVIRONMENT") == "prod" else "sqlite:///:memory:"

# Define the base class for all models
Base = declarative_base()

# Database session setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class JSONType(TypeDecorator):
    """A custom JSON type that uses JSONB for PostgreSQL and TEXT for SQLite."""
    impl = TEXT

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)


class ArrayType(TypeDecorator):
    """A custom ARRAY type that stores lists as JSON in SQLite but uses native ARRAY in PostgreSQL."""
    impl = TEXT  # Uses TEXT for SQLite

    def process_bind_param(self, value, dialect):
        """Convert Python list to a CSV string before storing in SQLite."""
        if value is None:
            return None
        if isinstance(value, list):
            return ",".join(map(str, value))  # Convert list to CSV string
        return value  # Already stored correctly

    def process_result_value(self, value, dialect):
        """Convert CSV string back to a Python list when retrieving."""
        if value is None:
            return None
        return value.split(",") if value else []  # Convert CSV string to list


def get_json_column():
    """Return the appropriate JSON column type based on the database engine. JSONB for Postgres and JSONType (TEXT) for SQLite."""
    return JSONB if sqlalchemy.engine.url.make_url(DATABASE_URL).get_backend_name() == "postgresql" else JSONType()


def get_array_column(item_type):
    """Return the appropriate ARRAY column type based on the database engine."""
    return PG_ARRAY(item_type) if sqlalchemy.engine.url.make_url(DATABASE_URL).get_backend_name() == "postgresql" else ArrayType()


# Models and Pydantic schemas


class User(Base):
    """SQLAlchemy ORM model for the User table."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    role = Column(String, default='user')  # Default role is 'user'


class UserCreate(BaseModel):
    """Pydantic model for creating a new user."""
    name: str
    email: EmailStr
    role: t.Literal["user", "power_user"]


class UserOut(BaseModel):
    """Pydantic model for outputting user data."""
    id: int
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True  # This tells Pydantic to convert ORM models to dicts


class Prompt(Base):
    """SQLAlchemy ORM model for the Prompt table."""
    __tablename__ = 'prompts'

    id = Column(Integer, primary_key=True, index=True)
    prompt_uri = Column(String, index=True)


class PromptCreate(BaseModel):
    """Pydantic model for creating a new prompt."""
    prompt_uri: str


class PromptOut(BaseModel):
    """Pydantic model for outputting prompt data."""
    id: int
    prompt_uri: str

    class Config:
        from_attributes = True  # This tells Pydantic to convert ORM models to dicts


class Chat(Base):
    """SQLAlchemy ORM model for the Chat table."""
    __tablename__ = 'chats'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', name="fk_user_id", ondelete="CASCADE"), index=True)
    chat_session_id = Column(Integer, index=True)
    message_id = Column(Integer, index=True)
    message = Column(String)
    message_is_from_user = Column(Boolean)
    user_rating = Column(Integer, nullable=True, default=0)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ChatCreate(BaseModel):
    """Pydantic model for creating a new chat message."""
    user_id: int
    chat_session_id: int
    message: str
    message_is_from_user: bool
    user_rating: int = Field(0, ge=-1, le=1)


class ChatOut(BaseModel):
    """Pydantic model for outputting chat data."""
    id: int
    user_id: int
    chat_session_id: int
    message_id: int
    message: str
    message_is_from_user: bool
    user_rating: int
    timestamp: datetime

    class Config:
        from_attributes = True  # This tells Pydantic to convert ORM models to dicts


class UpdateChat(BaseModel):
    """Pydantic model for updating a chat message."""
    chat_id: int
    user_rating: int = Field(0, ge=-1, le=1)


class LayGlossary(Base):
    """SQLAlchemy ORM model for the LayGlossary table."""
    __tablename__ = 'lay_glossary'

    id = Column(Integer, primary_key=True, index=True)
    term = Column(String, index=True)
    definition = Column(String)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TermDefinitionCreate(BaseModel):
    """Pydantic model for creating a new lay glossary entry."""
    term: str
    definition: str


class TermDefinitionOut(BaseModel):
    """Pydantic model for outputting lay glossary data."""
    id: int
    term: str
    definition: str
    last_updated: datetime

    class Config:
        from_attributes = True  # This tells Pydantic to convert ORM models to dicts


class LayGlossaryCreate(BaseModel):
    """Pydantic model for creating a new lay glossary from many term definitions."""
    term_definitions: t.List[TermDefinitionCreate]


class CTPs(Base):
    """SQLAlchemy ORM model for the CTPs table."""
    __tablename__ = 'ctps'

    id = Column(Integer, primary_key=True, index=True)
    cpt_id = Column(String, index=True)
    apollo_index_id = Column(String, index=True)
    ctp_metadata = Column(get_json_column(), nullable=True, default={})
    categories = Column(get_array_column(String), nullable=True, default=[])
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CTPsCreate(BaseModel):
    """Pydantic model for creating a new CTP entry."""
    cpt_id: str
    apollo_index_id: str
    lps_id: int = None
    bs_id: int = None
    ctp_metadata: dict = {}
    categories: t.List[str] = []


class CTPsOut(BaseModel):
    """Pydantic model for outputting CTP data."""
    id: int
    cpt_id: str
    apollo_index_id: str
    lps_id: int = None
    bs_id: int = None
    ctp_metadata: dict = {}
    categories: t.List[str] = []
    last_updated: datetime

    class Config:
        from_attributes = True  # This tells Pydantic to convert ORM models to dicts


class LPS(Base):
    """SQLAlchemy ORM model for the Lay Protocol Summary (LPS) table."""
    __tablename__ = 'lps'

    id = Column(Integer, primary_key=True, index=True)
    ctp_id = Column(Integer, ForeignKey('ctps.id', name="fk_ctps_id", ondelete="CASCADE"), index=True)
    lps_uri = Column(String, index=True)
    llm_judge_rating = Column(Float, nullable=True, default=0.0)
    llm_judge_scores = Column(get_json_column(), nullable=True, default={})
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LPSCreate(BaseModel):
    """Pydantic model for creating a new Lay Protocol Summary (LPS) entry."""
    ctp_id: int
    lps_uri: str
    llm_judge_rating: float = 0.0
    llm_judge_scores: dict = {}


class LPSOut(BaseModel):
    """Pydantic model for outputting Lay Protocol Summary (LPS) data."""
    id: int
    ctp_id: int
    lps_uri: str
    llm_judge_rating: float = 0.0
    llm_judge_scores: dict = {}
    last_updated: datetime

    class Config:
        from_attributes = True  # This tells Pydantic to convert ORM models to dicts


class BS(Base):
    """SQLAlchemy ORM model for the Brief Summary (BS) table."""
    __tablename__ = 'bs'

    id = Column(Integer, primary_key=True, index=True)
    ctp_id = Column(Integer, ForeignKey('ctps.id', name="fk_ctps_id", ondelete="CASCADE"), index=True)
    bs_uri = Column(String, index=True)
    llm_judge_rating = Column(Float, nullable=True, default=0.0)
    llm_judge_scores = Column(get_json_column(), nullable=True, default={})
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BSCreate(BaseModel):
    """Pydantic model for creating a new Brief Summary (BS) entry."""
    ctp_id: int
    bs_uri: str
    llm_judge_rating: float = 0.0
    llm_judge_scores: dict = {}


class BSOut(BaseModel):
    """Pydantic model for outputting Brief Summary (BS) data."""
    id: int
    ctp_id: int
    bs_uri: str
    llm_judge_rating: float = 0.0
    llm_judge_scores: dict = {}
    last_updated: datetime

    class Config:
        from_attributes = True  # This tells Pydantic to convert ORM models to dicts


# CRUD operations


def create_all_tables():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)


def drop_all_tables():
    """Drop all tables in the database."""
    inspector = inspect(engine)
    if inspector.has_table('users'):  # Check if any table exists
        Base.metadata.drop_all(bind=engine)


def create_user(db_session, user: UserCreate):
    """Create a new user in the database."""
    db_user = User(name=user.name, email=user.email, role=user.role)
    db_session.add(db_user)
    db_session.commit()
    db_session.refresh(db_user)
    return db_user


def get_user(db_session, user_id: int):
    """Fetch a user by ID from the database."""
    return db_session.query(User).filter(User.id == user_id).first()


def get_all_users(db_session):
    """Fetch all users from the database."""
    return db_session.query(User).all()


def update_user(db_session, user_id: int, user: UserCreate):
    """Update an existing user in the database."""
    db_user = db_session.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.name = user.name
        db_user.email = user.email
        db_user.role = user.role
        db_session.commit()
        db_session.refresh(db_user)
        return db_user
    return None


def delete_user(db_session, user_id: int):
    """Delete a user from the database."""
    db_user = db_session.query(User).filter(User.id == user_id).first()
    if db_user:
        db_session.delete(db_user)
        db_session.commit()
        return True
    return False


def create_prompt(db_session, prompt: PromptCreate):
    """Create a new prompt in the database."""
    db_prompt = Prompt(prompt_uri=prompt.prompt_uri)
    db_session.add(db_prompt)
    db_session.commit()
    db_session.refresh(db_prompt)
    return db_prompt


def get_prompt(db_session, prompt_id: int):
    """Fetch a prompt by ID from the database."""
    return db_session.query(Prompt).filter(Prompt.id == prompt_id).first()


def get_all_prompts(db_session):
    """Fetch all prompts from the database."""
    return db_session.query(Prompt).all()


def update_prompt(db_session, prompt_id: int, prompt: PromptCreate):
    """Update an existing prompt in the database."""
    db_prompt = db_session.query(Prompt).filter(Prompt.id == prompt_id).first()
    if db_prompt:
        db_prompt.prompt_uri = prompt.prompt_uri
        db_session.commit()
        db_session.refresh(db_prompt)
        return db_prompt
    return None


def delete_prompt(db_session, prompt_id: int):
    """Delete a prompt from the database."""
    db_prompt = db_session.query(Prompt).filter(Prompt.id == prompt_id).first()
    if db_prompt:
        db_session.delete(db_prompt)
        db_session.commit()
        return True
    return False


def create_chat_message(db_session, chat: ChatCreate):
    """Create a new chat message in the database."""
    max_id = db_session.query(
        coalesce(func.max(Chat.message_id), 0)
    ).filter(
        Chat.user_id == chat.user_id,
        Chat.chat_session_id == chat.chat_session_id
    ).scalar()
    new_msg = Chat(
        user_id=chat.user_id,
        chat_session_id=chat.chat_session_id,
        message_id=max_id + 1,
        message=chat.message,
        message_is_from_user=chat.message_is_from_user,
        user_rating=0,
    )
    db_session.add(new_msg)
    db_session.commit()
    return new_msg


def get_chat_messages_for_user_session(db_session, user_id: int, session_id: int):
    """Fetch all chat messages for a specific user session from the database."""
    return db_session.query(Chat).filter(
        Chat.user_id == user_id,
        Chat.chat_session_id == session_id
    ).all()


def get_chat_messages_for_last_session(db_session, user_id: int):
    """Fetch all chat messages for the last session of a specific user from the database."""
    return db_session.query(Chat).filter(
        Chat.user_id == user_id,
        Chat.chat_session_id == db_session.query(func.max(Chat.chat_session_id)).filter(Chat.user_id == user_id)
    ).all()


def get_all_chat_messages_for_user(db_session, user_id: int):
    """Fetch all chat messages for a specific user from the database."""
    return db_session.query(Chat).filter(Chat.user_id == user_id).all()


def update_chat_message_rating(db_session, update_chat: UpdateChat):
    """Update an existing chat message in the database."""
    db_chat = db_session.query(Chat).filter(Chat.id == update_chat.chat_id).first()
    if db_chat:
        db_chat.user_rating = update_chat.user_rating
        db_session.commit()
        db_session.refresh(db_chat)
        return db_chat
    return None


def delete_chat_message(db_session, chat_id: int):
    """Delete a chat message from the database."""
    db_chat = db_session.query(Chat).filter(Chat.id == chat_id).first()
    if db_chat:
        db_session.delete(db_chat)
        db_session.commit()
        return True
    return False


def delete_chat_session(db_session, user_id: int, session_id: int):
    """Delete all chat messages for a specific user session from the database."""
    db_session.query(Chat).filter(
        Chat.user_id == user_id,
        Chat.chat_session_id == session_id
    ).delete()
    db_session.commit()
    return True


def delete_user_chats(db_session, user_id: int):
    """Delete all chat messages for a specific user from the database."""
    db_session.query(Chat).filter(Chat.user_id == user_id).delete()
    db_session.commit()
    return True


def create_term_definition(db_session, glossary: TermDefinitionCreate):
    """Create a new lay glossary entry in the database."""
    db_glossary = LayGlossary(term=glossary.term, definition=glossary.definition)
    db_session.add(db_glossary)
    db_session.commit()
    db_session.refresh(db_glossary)
    return db_glossary


def get_term_definition(db_session, term_id: int):
    """Fetch a lay glossary entry by ID from the database."""
    return db_session.query(LayGlossary).filter(LayGlossary.id == term_id).first()


def get_all_term_definitions(db_session):
    """Fetch all lay glossary entries from the database."""
    return db_session.query(LayGlossary).all()


def update_term_definition(db_session, term_id: int, glossary: TermDefinitionCreate):
    """Update an existing lay glossary entry in the database."""
    db_glossary = db_session.query(LayGlossary).filter(LayGlossary.id == term_id).first()
    if db_glossary:
        db_glossary.term = glossary.term
        db_glossary.definition = glossary.definition
        db_session.commit()
        db_session.refresh(db_glossary)
        return db_glossary
    return None


def delete_term_definition(db_session, term_id: int):
    """Delete a lay glossary entry from the database."""
    db_glossary = db_session.query(LayGlossary).filter(LayGlossary.id == term_id).first()
    if db_glossary:
        db_session.delete(db_glossary)
        db_session.commit()
        return True
    return False


def create_lay_glossary(db_session, glossary: LayGlossaryCreate):
    """Create a new lay glossary from many term definitions."""
    for term_definition in glossary.term_definitions:
        db_glossary = LayGlossary(
            term=term_definition.term,
            definition=term_definition.definition
        )
        db_session.add(db_glossary)
    db_session.commit()
    return True


def delete_lay_glossary(db_session):
    """Delete all lay glossary entries from the database."""
    db_session.query(LayGlossary).delete()
    db_session.commit()
    return True


def create_ctp(db_session, ctp: CTPsCreate):
    """Create a new CTP entry in the database."""
    db_ctp = CTPs(
        cpt_id=ctp.cpt_id,
        apollo_index_id=ctp.apollo_index_id,
        ctp_metadata=ctp.ctp_metadata,
        categories=ctp.categories
    )
    db_session.add(db_ctp)
    db_session.commit()
    db_session.refresh(db_ctp)
    return db_ctp

def get_ctp(db_session, ctp_id: int):
    """Fetch a CTP entry by ID from the database."""
    return db_session.query(CTPs).filter(CTPs.id == ctp_id).first()


def get_all_ctps(db_session):
    """Fetch all CTP entries from the database."""
    return db_session.query(CTPs).all()


def update_ctp(db_session, ctp_id: int, ctp: CTPsCreate):
    """Update an existing CTP entry in the database."""
    db_ctp = db_session.query(CTPs).filter(CTPs.id == ctp_id).first()
    if db_ctp:
        db_ctp.cpt_id = ctp.cpt_id
        db_ctp.apollo_index_id = ctp.apollo_index_id
        db_ctp.ctp_metadata = ctp.ctp_metadata
        db_ctp.categories = ctp.categories
        db_session.commit()
        db_session.refresh(db_ctp)
        return db_ctp
    return None


def delete_ctp(db_session, ctp_id: int):
    """Delete a CTP entry from the database."""
    db_ctp = db_session.query(CTPs).filter(CTPs.id == ctp_id).first()
    if db_ctp:
        db_session.delete(db_ctp)
        db_session.commit()
        return True
    return False


def create_lps(db_session, lps: LPSCreate):
    """Create a new Lay Protocol Summary (LPS) entry in the database."""
    db_lps = LPS(
        ctp_id=lps.ctp_id,
        lps_uri=lps.lps_uri,
        llm_judge_rating=lps.llm_judge_rating,
        llm_judge_scores=lps.llm_judge_scores
    )
    db_session.add(db_lps)
    db_session.commit()
    db_session.refresh(db_lps)
    return db_lps


def get_lps(db_session, lps_id: int):
    """Fetch a Lay Protocol Summary (LPS) entry by ID from the database."""
    return db_session.query(LPS).filter(LPS.id == lps_id).first()


def get_all_lps(db_session):
    """Fetch all Lay Protocol Summary (LPS) entries from the database."""
    return db_session.query(LPS).all()


def update_lps(db_session, lps_id: int, lps: LPSCreate):
    """Update an existing Lay Protocol Summary (LPS) entry in the database."""
    db_lps = db_session.query(LPS).filter(LPS.id == lps_id).first()
    if db_lps:
        db_lps.ctp_id = lps.ctp_id
        db_lps.lps_uri = lps.lps_uri
        db_lps.llm_judge_rating = lps.llm_judge_rating
        db_lps.llm_judge_scores = lps.llm_judge_scores
        db_session.commit()
        db_session.refresh(db_lps)
        return db_lps
    return None


def delete_lps(db_session, lps_id: int):
    """Delete a Lay Protocol Summary (LPS) entry from the database."""
    db_lps = db_session.query(LPS).filter(LPS.id == lps_id).first()
    if db_lps:
        db_session.delete(db_lps)
        db_session.commit()
        return True
    return False


def create_bs(db_session, bs: BSCreate):
    """Create a new Brief Summary (BS) entry in the database."""
    db_bs = BS(
        ctp_id=bs.ctp_id,
        bs_uri=bs.bs_uri,
        llm_judge_rating=bs.llm_judge_rating,
        llm_judge_scores=bs.llm_judge_scores
    )
    db_session.add(db_bs)
    db_session.commit()
    db_session.refresh(db_bs)
    return db_bs


def get_bs(db_session, bs_id: int):
    """Fetch a Brief Summary (BS) entry by ID from the database."""
    return db_session.query(BS).filter(BS.id == bs_id).first()


def get_all_bs(db_session):
    """Fetch all Brief Summary (BS) entries from the database."""
    return db_session.query(BS).all()


def update_bs(db_session, bs_id: int, bs: BSCreate):
    """Update an existing Brief Summary (BS) entry in the database."""
    db_bs = db_session.query(BS).filter(BS.id == bs_id).first()
    if db_bs:
        db_bs.ctp_id = bs.ctp_id
        db_bs.bs_uri = bs.bs_uri
        db_bs.llm_judge_rating = bs.llm_judge_rating
        db_bs.llm_judge_scores = bs.llm_judge_scores
        db_session.commit()
        db_session.refresh(db_bs)
        return db_bs
    return None


def delete_bs(db_session, bs_id: int):
    """Delete a Brief Summary (BS) entry from the database."""
    db_bs = db_session.query(BS).filter(BS.id == bs_id).first()
    if db_bs:
        db_session.delete(db_bs)
        db_session.commit()
        return True
    return False


# Example usage in a script or FastAPI endpoint
if __name__ == "__main__":
    db = SessionLocal()

    # Refresh tables
    drop_all_tables()
    create_all_tables()

    # Create a new user using Pydantic model to validate input
    new_user = UserCreate(name="John Doe", email="john@example.com", role="power_user")
    db_user = create_user(db, new_user)
    # Fetch the user from the database
    user_from_db = get_user(db, db_user.id)
    # Convert the database model into Pydantic model
    user_out = UserOut.model_validate(user_from_db)
    print(user_out)
    # Fetch all users
    all_users = get_all_users(db)
    print(all_users)
    # Update a user
    updated_user = UserCreate(name="Jane Doe", email="doe@example.com", role="user")
    updated_user_entry = update_user(db, db_user.id, updated_user)
    # Fetch the updated user from the database
    updated_user_from_db = get_user(db, updated_user_entry.id)
    # Convert the database model into Pydantic model
    updated_user_out = UserOut.model_validate(updated_user_from_db)
    print(updated_user_out)
    # Delete a user
    delete_user(db, updated_user_entry.id)
    # Fetch all users after deletion
    all_users_after_deletion = get_all_users(db)
    print(all_users_after_deletion)

    # Create a new prompt
    new_prompt = PromptCreate(prompt_uri="example_prompt")
    db_prompt = create_prompt(db, new_prompt)
    # Fetch the prompt from the database
    prompt_from_db = get_prompt(db, db_prompt.id)
    # Convert the database model into Pydantic model
    prompt_out = PromptOut.model_validate(prompt_from_db)
    print(prompt_out)
    # Fetch all prompts
    all_prompts = get_all_prompts(db)
    print(all_prompts)
    # Update a prompt
    updated_prompt = PromptCreate(prompt_uri="updated_prompt")
    updated_prompt_entry = update_prompt(db, db_prompt.id, updated_prompt)
    # Fetch the updated prompt from the database
    updated_prompt_from_db = get_prompt(db, updated_prompt_entry.id)
    # Convert the database model into Pydantic model
    updated_prompt_out = PromptOut.model_validate(updated_prompt_from_db)
    print(updated_prompt_out)
    # Delete a prompt
    delete_prompt(db, updated_prompt_entry.id)
    # Fetch all prompts after deletion
    all_prompts_after_deletion = get_all_prompts(db)
    print(all_prompts_after_deletion)

    # Create a new chat message
    new_chat = ChatCreate(
        user_id=db_user.id,
        chat_session_id=1,
        message="Hello, this is a test message.",
        message_is_from_user=True,
        user_rating=0
    )
    db_chat = create_chat_message(db, new_chat)
    # Fetch the chat message from the database
    chat_from_db = get_chat_messages_for_user_session(db, new_chat.user_id, new_chat.chat_session_id)
    # Convert the database model into Pydantic model
    chat_out = [ChatOut.model_validate(chat) for chat in chat_from_db]
    print(chat_out)
    # Fetch all chat messages for the last session
    all_chat_messages = get_chat_messages_for_last_session(db, new_chat.user_id)
    print(all_chat_messages)
    # Update a chat message rating
    update_chat = UpdateChat(chat_id=db_chat.id, user_rating=1)
    updated_chat = update_chat_message_rating(db, update_chat)
    # Fetch the updated chat message from the database
    updated_chat_from_db = get_chat_messages_for_user_session(db, new_chat.user_id, new_chat.chat_session_id)
    # Convert the database model into Pydantic model
    updated_chat_out = [ChatOut.model_validate(chat) for chat in updated_chat_from_db]
    print(updated_chat_out)
    # Delete a chat message
    delete_chat_message(db, db_chat.id)
    # Fetch all chat messages after deletion
    all_chat_messages_after_deletion = get_all_chat_messages_for_user(db, new_chat.user_id)
    print(all_chat_messages_after_deletion)

    # Create a new lay glossary entry
    new_glossary = TermDefinitionCreate(term="example_term", definition="example_definition")
    db_glossary = create_term_definition(db, new_glossary)
    # Fetch the glossary entry from the database
    glossary_from_db = get_term_definition(db, db_glossary.id)
    # Convert the database model into Pydantic model
    glossary_out = TermDefinitionOut.model_validate(glossary_from_db)
    print(glossary_out)
    # Fetch all glossary entries
    all_glossaries = get_all_term_definitions(db)
    print(all_glossaries)
    # Update a glossary entry
    updated_glossary = TermDefinitionCreate(term="updated_term", definition="updated_definition")
    updated_glossary_entry = update_term_definition(db, db_glossary.id, updated_glossary)
    # Fetch the updated glossary entry from the database
    updated_glossary_from_db = get_term_definition(db, updated_glossary_entry.id)
    # Convert the database model into Pydantic model
    updated_glossary_out = TermDefinitionOut.model_validate(updated_glossary_from_db)
    print(updated_glossary_out)
    # Delete a glossary entry
    delete_term_definition(db, updated_glossary_entry.id)
    # Fetch all glossary entries after deletion
    all_glossaries_after_deletion = get_all_term_definitions(db)
    print(all_glossaries_after_deletion)

    # Create a new CTP entry
    new_ctp = CTPsCreate(
        cpt_id="example_cpt_id",
        apollo_index_id="example_apollo_index_id",
        ctp_metadata={},
        categories=[]
    )
    db_ctp = create_ctp(db, new_ctp)
    # Fetch the CTP entry from the database
    ctp_from_db = get_ctp(db, db_ctp.id)
    # Convert the database model into Pydantic model
    ctp_out = CTPsOut.model_validate(ctp_from_db)
    print(ctp_out)
    # Fetch all CTP entries
    all_ctps = get_all_ctps(db)
    print(all_ctps)
    # Update a CTP entry
    updated_ctp = CTPsCreate(
        cpt_id="updated_cpt_id",
        apollo_index_id="updated_apollo_index_id",
        ctp_metadata={},
        categories=[]
    )
    updated_ctp_entry = update_ctp(db, db_ctp.id, updated_ctp)
    # Fetch the updated CTP entry from the database
    updated_ctp_from_db = get_ctp(db, updated_ctp_entry.id)
    # Convert the database model into Pydantic model
    updated_ctp_out = CTPsOut.model_validate(updated_ctp_from_db)
    print(updated_ctp_out)
    # Delete a CTP entry
    delete_ctp(db, updated_ctp_entry.id)
    # Fetch all CTP entries after deletion
    all_ctps_after_deletion = get_all_ctps(db)
    print(all_ctps_after_deletion)

    # Need a CTP entry to create LPS and BS entries
    new_ctp = CTPsCreate(
        cpt_id="example_cpt_id",
        apollo_index_id="example_apollo_index_id",
        ctp_metadata={},
        categories=[]
    )
    db_ctp = create_ctp(db, new_ctp)

    # Create a new LPS entry
    new_lps = LPSCreate(
        ctp_id=db_ctp.id,
        lps_uri="example_lps_uri",
        llm_judge_rating=0.0,
        llm_judge_scores={}
    )
    db_lps = create_lps(db, new_lps)
    # Fetch the LPS entry from the database
    lps_from_db = get_lps(db, db_lps.id)
    # Convert the database model into Pydantic model
    lps_out = LPSOut.model_validate(lps_from_db)
    print(lps_out)
    # Fetch all LPS entries
    all_lps = get_all_lps(db)
    print(all_lps)
    # Update a LPS entry
    updated_lps = LPSCreate(
        ctp_id=db_ctp.id,
        lps_uri="updated_lps_uri",
        llm_judge_rating=0.0,
        llm_judge_scores={}
    )
    updated_lps_entry = update_lps(db, db_lps.id, updated_lps)
    # Fetch the updated LPS entry from the database
    updated_lps_from_db = get_lps(db, updated_lps_entry.id)
    # Convert the database model into Pydantic model
    updated_lps_out = LPSOut.model_validate(updated_lps_from_db)
    print(updated_lps_out)
    # Delete a LPS entry
    delete_lps(db, updated_lps_entry.id)
    # Fetch all LPS entries after deletion
    all_lps_after_deletion = get_all_lps(db)
    print(all_lps_after_deletion)

    # Create a new BS entry
    new_bs = BSCreate(
        ctp_id=db_ctp.id,
        bs_uri="example_bs_uri",
        llm_judge_rating=0.0,
        llm_judge_scores={}
    )
    db_bs = create_bs(db, new_bs)
    # Fetch the BS entry from the database
    bs_from_db = get_bs(db, db_bs.id)
    # Convert the database model into Pydantic model
    bs_out = BSOut.model_validate(bs_from_db)
    print(bs_out)
    # Fetch all BS entries
    all_bs = get_all_bs(db)
    print(all_bs)
    # Update a BS entry
    updated_bs = BSCreate(
        ctp_id=db_ctp.id,
        bs_uri="updated_bs_uri",
        llm_judge_rating=0.0,
        llm_judge_scores={}
    )
    updated_bs_entry = update_bs(db, db_bs.id, updated_bs)
    # Fetch the updated BS entry from the database
    updated_bs_from_db = get_bs(db, updated_bs_entry.id)
    # Convert the database model into Pydantic model
    updated_bs_out = BSOut.model_validate(updated_bs_from_db)
    print(updated_bs_out)
    # Delete a BS entry
    delete_bs(db, updated_bs_entry.id)
    # Fetch all BS entries after deletion
    all_bs_after_deletion = get_all_bs(db)
    print(all_bs_after_deletion)

    # Close the database session
    db.close()
