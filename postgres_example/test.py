import unittest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from schema import (
    Base,
    UserCreate, PromptCreate, ChatCreate, UpdateChat, TermDefinitionCreate, LayGlossaryCreate, CTPsCreate, LPSCreate, BSCreate,
    create_user, get_user, get_all_users, update_user, delete_user,
    create_prompt, get_prompt, get_all_prompts, update_prompt, delete_prompt,
    create_chat_message, get_chat_messages_for_user_session, get_chat_messages_for_last_session, get_all_chat_messages_for_user, update_chat_message_rating, delete_chat_message, delete_chat_session, delete_user_chats,
    create_term_definition, get_term_definition, get_all_term_definitions, update_term_definition, delete_term_definition, create_lay_glossary, delete_lay_glossary,
    create_ctp, get_ctp, get_all_ctps, update_ctp, delete_ctp,
    create_lps, get_lps, get_all_lps, update_lps, delete_lps,
    create_bs, get_bs, get_all_bs, update_bs, delete_bs
)


# Database connection URL
DATABASE_URL = "sqlite:///:memory:"  # In-memory SQLite database for testing


class TestSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(DATABASE_URL, echo=False)
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        """Create a new session for each test."""
        self.db = self.Session()

    def tearDown(self):
        """Rollback transactions and close the session after each test."""
        self.db.rollback()
        self.db.close()

    def test_create_and_get_user(self):
        new_user = UserCreate(name="Jack Doe", email="jack@example.com", role="power_user")
        db_user = create_user(self.db, new_user)
        fetched_user = get_user(self.db, db_user.id)
        self.assertEqual(db_user.name, fetched_user.name)

    def test_get_all_users(self):
        new_user = UserCreate(name="Alice Doe", email="alice@example.com", role="user")
        db_user = create_user(self.db, new_user)
        all_users = get_all_users(self.db)
        all_users2 = self.db.execute(text("SELECT * FROM users")).fetchall()
        self.assertIn(db_user, all_users)
        self.assertEqual(len(all_users), len(all_users2))

    def test_update_user(self):
        new_user = UserCreate(name="John Doe", email="john@example.com", role="power_user")
        db_user = create_user(self.db, new_user)
        updated_user = UserCreate(name="Jane Doe", email="doe@example.com", role="user")
        update_user(self.db, db_user.id, updated_user)
        fetched_user = get_user(self.db, db_user.id)
        self.assertEqual(fetched_user.name, "Jane Doe")

    def test_delete_user(self):
        new_user = UserCreate(name="Jill Doe", email="jill@example.com", role="power_user")
        db_user = create_user(self.db, new_user)
        self.assertTrue(delete_user(self.db, db_user.id))
        fetched_user = get_user(self.db, db_user.id)
        self.assertIsNone(fetched_user)

    def test_create_and_get_prompt(self):
        new_prompt = PromptCreate(prompt_uri="example_prompt")
        db_prompt = create_prompt(self.db, new_prompt)
        fetched_prompt = get_prompt(self.db, db_prompt.id)
        self.assertEqual(db_prompt.prompt_uri, fetched_prompt.prompt_uri)

    def test_get_all_prompts(self):
        new_prompt = PromptCreate(prompt_uri="example_prompt")
        db_prompt = create_prompt(self.db, new_prompt)
        all_prompts = get_all_prompts(self.db)
        all_prompts2 = self.db.execute(text("SELECT * FROM prompts")).fetchall()
        self.assertIn(db_prompt, all_prompts)
        self.assertEqual(len(all_prompts), len(all_prompts2))

    def test_update_prompt(self):
        new_prompt = PromptCreate(prompt_uri="example_prompt")
        db_prompt = create_prompt(self.db, new_prompt)
        updated_prompt = PromptCreate(prompt_uri="updated_prompt")
        update_prompt(self.db, db_prompt.id, updated_prompt)
        fetched_prompt = get_prompt(self.db, db_prompt.id)
        self.assertEqual(fetched_prompt.prompt_uri, "updated_prompt")

    def test_delete_prompt(self):
        new_prompt = PromptCreate(prompt_uri="example_prompt")
        db_prompt = create_prompt(self.db, new_prompt)
        self.assertTrue(delete_prompt(self.db, db_prompt.id))
        fetched_prompt = get_prompt(self.db, db_prompt.id)
        self.assertIsNone(fetched_prompt)

    def test_create_and_get_chat_message(self):
        new_chat = ChatCreate(user_id=1, chat_session_id=1, message="example_message", message_is_from_user=True, user_rating=0)
        db_chat = create_chat_message(self.db, new_chat)
        fetched_chat = get_chat_messages_for_user_session(self.db, db_chat.user_id, db_chat.chat_session_id)
        self.assertEqual(db_chat.message, fetched_chat[0].message)
        fetched_chat2 = get_chat_messages_for_last_session(self.db, db_chat.user_id)
        self.assertEqual(db_chat.message, fetched_chat2[0].message)
        fetched_chat3 = get_all_chat_messages_for_user(self.db, db_chat.user_id)
        self.assertEqual(db_chat.message, fetched_chat3[0].message)

    def test_update_chat_message(self):
        new_chat = ChatCreate(user_id=1, chat_session_id=1, message="example_message", message_is_from_user=True, user_rating=0)
        db_chat = create_chat_message(self.db, new_chat)
        update_chat = UpdateChat(chat_id=db_chat.id, user_rating=1)
        update_chat_message_rating(self.db, update_chat)
        fetched_chat = get_chat_messages_for_user_session(self.db, db_chat.user_id, db_chat.chat_session_id)
        self.assertEqual(fetched_chat[0].user_rating, 1)

    def test_delete_chat_message(self):
        new_chat = ChatCreate(user_id=1, chat_session_id=1, message="example_message", message_is_from_user=True, user_rating=0)
        db_chat = create_chat_message(self.db, new_chat)
        self.assertTrue(delete_chat_message(self.db, db_chat.id))
        fetched_chat = get_chat_messages_for_user_session(self.db, db_chat.user_id, db_chat.chat_session_id)
        for m in fetched_chat:
            self.assertNotEqual(m.id, db_chat.id)

    def test_delete_chat_session(self):
        new_chat = ChatCreate(user_id=1, chat_session_id=1, message="example_message", message_is_from_user=True, user_rating=0)
        db_chat = create_chat_message(self.db, new_chat)
        delete_chat_session(self.db, db_chat.user_id, db_chat.chat_session_id)
        fetched_chat = get_chat_messages_for_user_session(self.db, db_chat.user_id, db_chat.chat_session_id)
        self.assertEqual(len(fetched_chat), 0)

    def test_delete_user_chats(self):
        new_chat = ChatCreate(user_id=1, chat_session_id=1, message="example_message", message_is_from_user=True, user_rating=0)
        db_chat = create_chat_message(self.db, new_chat)
        delete_user_chats(self.db, db_chat.user_id)
        fetched_chat = get_all_chat_messages_for_user(self.db, db_chat.user_id)
        self.assertEqual(len(fetched_chat), 0)

    def test_create_and_get_term_definition(self):
        new_term = TermDefinitionCreate(term="example_term", definition="example_definition")
        db_term = create_term_definition(self.db, new_term)
        fetched_term = get_term_definition(self.db, db_term.id)
        self.assertEqual(db_term.term, fetched_term.term)

    def test_get_all_term_definitions(self):
        new_term = TermDefinitionCreate(term="example_term", definition="example_definition")
        db_term = create_term_definition(self.db, new_term)
        all_terms = get_all_term_definitions(self.db)
        all_terms2 = self.db.execute(text("SELECT * FROM lay_glossary")).fetchall()
        self.assertIn(db_term, all_terms)
        self.assertEqual(len(all_terms), len(all_terms2))

    def test_update_term_definition(self):
        new_term = TermDefinitionCreate(term="example_term", definition="example_definition")
        db_term = create_term_definition(self.db, new_term)
        updated_term = TermDefinitionCreate(term="updated_term", definition="updated_definition")
        update_term_definition(self.db, db_term.id, updated_term)
        fetched_term = get_term_definition(self.db, db_term.id)
        self.assertEqual(fetched_term.term, "updated_term")

    def test_delete_term_definition(self):
        new_term = TermDefinitionCreate(term="example_term", definition="example_definition")
        db_term = create_term_definition(self.db, new_term)
        self.assertTrue(delete_term_definition(self.db, db_term.id))
        fetched_term = get_term_definition(self.db, db_term.id)
        self.assertIsNone(fetched_term)

    def test_create_and_get_lay_glossary(self):
        new_term1 = TermDefinitionCreate(term="example_term1", definition="example_definition1")
        new_term2 = TermDefinitionCreate(term="example_term2", definition="example_definition2")
        db_definitions = LayGlossaryCreate(term_definitions=[new_term1, new_term2])
        create_lay_glossary(self.db, db_definitions)
        all_terms = get_all_term_definitions(self.db)
        all_terms2 = self.db.execute(text("SELECT * FROM lay_glossary")).fetchall()
        self.assertEqual(len(all_terms), len(all_terms2))

    def test_delete_lay_glossary(self):
        new_term1 = TermDefinitionCreate(term="example_term1", definition="example_definition1")
        new_term2 = TermDefinitionCreate(term="example_term2", definition="example_definition2")
        db_definitions = LayGlossaryCreate(term_definitions=[new_term1, new_term2])
        create_lay_glossary(self.db, db_definitions)
        delete_lay_glossary(self.db)
        all_terms = get_all_term_definitions(self.db)
        self.assertEqual(len(all_terms), 0)

    def test_create_and_get_ctp(self):
        new_ctp = CTPsCreate(cpt_id="example_cpt_id", apollo_index_id="example_apollo_index_id", ctp_metadata={}, categories=[])
        db_ctp = create_ctp(self.db, new_ctp)
        fetched_ctp = get_ctp(self.db, db_ctp.id)
        self.assertEqual(db_ctp.cpt_id, fetched_ctp.cpt_id)

    def test_get_all_ctps(self):
        new_ctp = CTPsCreate(cpt_id="example_cpt_id", apollo_index_id="example_apollo_index_id", ctp_metadata={}, categories=[])
        db_ctp = create_ctp(self.db, new_ctp)
        all_ctps = get_all_ctps(self.db)
        all_ctps2 = self.db.execute(text("SELECT * FROM ctps")).fetchall()
        self.assertIn(db_ctp, all_ctps)
        self.assertEqual(len(all_ctps), len(all_ctps2))

    def test_update_ctp(self):
        new_ctp = CTPsCreate(cpt_id="example_cpt_id", apollo_index_id="example_apollo_index_id", ctp_metadata={}, categories=[])
        db_ctp = create_ctp(self.db, new_ctp)
        updated_ctp = CTPsCreate(cpt_id="updated_cpt_id", apollo_index_id="updated_apollo_index_id", ctp_metadata={}, categories=[])
        update_ctp(self.db, db_ctp.id, updated_ctp)
        fetched_ctp = get_ctp(self.db, db_ctp.id)
        self.assertEqual(fetched_ctp.cpt_id, "updated_cpt_id")

    def test_delete_ctp(self):
        new_ctp = CTPsCreate(cpt_id="example_cpt_id", apollo_index_id="example_apollo_index_id", ctp_metadata={}, categories=[])
        db_ctp = create_ctp(self.db, new_ctp)
        delete_ctp(self.db, db_ctp.id)
        fetched_ctp = get_ctp(self.db, db_ctp.id)
        self.assertIsNone(fetched_ctp)

    def test_create_and_get_lps(self):
        new_ctp = CTPsCreate(cpt_id="example_cpt_id", apollo_index_id="example_apollo_index_id", ctp_metadata={}, categories=[])
        db_ctp = create_ctp(self.db, new_ctp)
        new_lps = LPSCreate(ctp_id=db_ctp.id, lps_uri="example_lps_uri", llm_judge_rating=0.0, llm_judge_scores={})
        db_lps = create_lps(self.db, new_lps)
        fetched_lps = get_lps(self.db, db_lps.id)
        self.assertEqual(db_lps.lps_uri, fetched_lps.lps_uri)

    def test_get_all_lps(self):
        new_ctp = CTPsCreate(cpt_id="example_cpt_id", apollo_index_id="example_apollo_index_id", ctp_metadata={}, categories=[])
        db_ctp = create_ctp(self.db, new_ctp)
        new_lps = LPSCreate(ctp_id=db_ctp.id, lps_uri="example_lps_uri", llm_judge_rating=0.0, llm_judge_scores={})
        db_lps = create_lps(self.db, new_lps)
        all_lps = get_all_lps(self.db)
        all_lps2 = self.db.execute(text("SELECT * FROM lps")).fetchall()
        self.assertIn(db_lps, all_lps)
        self.assertEqual(len(all_lps), len(all_lps2))

    def test_update_lps(self):
        new_ctp = CTPsCreate(cpt_id="example_cpt_id", apollo_index_id="example_apollo_index_id", ctp_metadata={}, categories=[])
        db_ctp = create_ctp(self.db, new_ctp)
        new_lps = LPSCreate(ctp_id=db_ctp.id, lps_uri="example_lps_uri", llm_judge_rating=0.0, llm_judge_scores={})
        db_lps = create_lps(self.db, new_lps)
        updated_lps = LPSCreate(ctp_id=db_ctp.id, lps_uri="updated_lps_uri", llm_judge_rating=0.0, llm_judge_scores={})
        update_lps(self.db, db_lps.id, updated_lps)
        fetched_lps = get_lps(self.db, db_lps.id)
        self.assertEqual(fetched_lps.lps_uri, "updated_lps_uri")

    def test_delete_lps(self):
        new_ctp = CTPsCreate(cpt_id="example_cpt_id", apollo_index_id="example_apollo_index_id", ctp_metadata={}, categories=[])
        db_ctp = create_ctp(self.db, new_ctp)
        new_lps = LPSCreate(ctp_id=db_ctp.id, lps_uri="example_lps_uri", llm_judge_rating=0.0, llm_judge_scores={})
        db_lps = create_lps(self.db, new_lps)
        delete_lps(self.db, db_lps.id)
        fetched_lps = get_lps(self.db, db_lps.id)
        self.assertIsNone(fetched_lps)

    def test_create_and_get_bs(self):
        new_ctp = CTPsCreate(cpt_id="example_cpt_id", apollo_index_id="example_apollo_index_id", ctp_metadata={}, categories=[])
        db_ctp = create_ctp(self.db, new_ctp)
        new_bs = BSCreate(ctp_id=db_ctp.id, bs_uri="example_bs_uri", llm_judge_rating=0.0, llm_judge_scores={})
        db_bs = create_bs(self.db, new_bs)
        fetched_bs = get_bs(self.db, db_bs.id)
        self.assertEqual(db_bs.bs_uri, fetched_bs.bs_uri)

    def test_get_all_bs(self):
        new_ctp = CTPsCreate(cpt_id="example_cpt_id", apollo_index_id="example_apollo_index_id", ctp_metadata={}, categories=[])
        db_ctp = create_ctp(self.db, new_ctp)
        new_bs = BSCreate(ctp_id=db_ctp.id, bs_uri="example_bs_uri", llm_judge_rating=0.0, llm_judge_scores={})
        db_bs = create_bs(self.db, new_bs)
        all_bs = get_all_bs(self.db)
        all_bs2 = self.db.execute(text("SELECT * FROM bs")).fetchall()
        self.assertIn(db_bs, all_bs)
        self.assertEqual(len(all_bs), len(all_bs2))

    def test_update_bs(self):
        new_ctp = CTPsCreate(cpt_id="example_cpt_id", apollo_index_id="example_apollo_index_id", ctp_metadata={}, categories=[])
        db_ctp = create_ctp(self.db, new_ctp)
        new_bs = BSCreate(ctp_id=db_ctp.id, bs_uri="example_bs_uri", llm_judge_rating=0.0, llm_judge_scores={})
        db_bs = create_bs(self.db, new_bs)
        updated_bs = BSCreate(ctp_id=db_ctp.id, bs_uri="updated_bs_uri", llm_judge_rating=0.0, llm_judge_scores={})
        update_bs(self.db, db_bs.id, updated_bs)
        fetched_bs = get_bs(self.db, db_bs.id)
        self.assertEqual(fetched_bs.bs_uri, "updated_bs_uri")

    def test_delete_bs(self):
        new_ctp = CTPsCreate(cpt_id="example_cpt_id", apollo_index_id="example_apollo_index_id", ctp_metadata={}, categories=[])
        db_ctp = create_ctp(self.db, new_ctp)
        new_bs = BSCreate(ctp_id=db_ctp.id, bs_uri="example_bs_uri", llm_judge_rating=0.0, llm_judge_scores={})
        db_bs = create_bs(self.db, new_bs)
        delete_bs(self.db, db_bs.id)
        fetched_bs = get_bs(self.db, db_bs.id)
        self.assertIsNone(fetched_bs)


if __name__ == '__main__':
    unittest.main()
