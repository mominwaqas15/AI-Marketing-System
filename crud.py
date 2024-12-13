from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy import select
import model
import datetime
from model import Users, Conversations, Messages, Complements

def get_or_create_user(db: Session, username: str):
    # Fetch the highest user_id from the Users table
    last_user = db.query(model.Users).order_by(model.Users.user_id.desc()).first()
    if last_user is None:
        new_user_id = 1
    else:
        new_user_id = last_user.user_id + 1

    # Insert the new user with the new user_id
    user = model.Users(user_id=new_user_id, username=username)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_chat_message(db: Session, sent_by: str, chat: str, user_id: int, conversation_id: int):
    # Ensure the user exists in the Users table
    user = db.query(model.Users).filter_by(user_id=user_id).first()
    if user is None:
        user = get_or_create_user(db, username="unknown")  # Provide default values
        user_id = user.user_id
    
    # Create the chat message
    db_con_id_add = model.Conversations()
    db_message = model.Messages(sent_by=sent_by, chat=chat, conversation_id=conversation_id)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def create_conversation(db: Session, user_id: int) -> int:
    """
    Create a new conversation for a user and return the conversation ID.

    :param db: Database session.
    :param user_id: ID of the user starting the conversation.
    :return: ID of the newly created conversation.
    """
    new_conversation = Conversations(user_id=user_id)
    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)
    return new_conversation

def get_chat_history(session: Session, chat_id: int) -> list:
    # Query all messages for the given chat_id
    messages = session.query(Messages).filter(Messages.conversation_id == chat_id).order_by(Messages.message_time).all()

    formatted_messages = [{"role": message.sent_by, "content": message.chat} for message in messages]

    return formatted_messages