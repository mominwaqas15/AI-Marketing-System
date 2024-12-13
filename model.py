from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class Users(Base):
    __tablename__ = "Users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(Text, nullable=False)  # Username or identifier
    joined_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

class Conversations(Base):
    __tablename__ = "Conversations"

    conversation_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('Users.user_id'), nullable=False)
    start_time = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)  # Null until conversation ends

class Messages(Base):
    __tablename__ = "Messages"

    message_id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey('Conversations.conversation_id'), nullable=False)
    sent_by = Column(Text, nullable=False)  # "user" or "system"
    chat = Column(Text, nullable=False)  # Actual message text
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

class Complements(Base):
    __tablename__ = "Complements"

    complement_id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey('Conversations.conversation_id'), nullable=False)
    image_path = Column(Text, nullable=False)  # Path to the complemented image
    complement_text = Column(Text, nullable=False)  # Generated complement
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)