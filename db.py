#!/usr/bin/env python3

import os
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    MetaData,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://username:password@localhost:5432/research_db"
)

# SQLAlchemy setup
Base = declarative_base()
metadata = MetaData()


class Project(Base):
    """Project table model"""

    __tablename__ = "projects"

    project_id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to samples
    samples = relationship("Sample", back_populates="project")

    def __repr__(self):
        return f"<Project(project_id={self.project_id}, created_at={self.created_at})>"

    def to_dict(self):
        return {
            "project_id": self.project_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Subject(Base):
    """Subject table model"""

    __tablename__ = "subjects"

    subject_id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    condition = Column(String(100), nullable=True)
    age = Column(Integer, nullable=True)
    sex = Column(String(10), nullable=True)

    # Relationship to samples
    samples = relationship("Sample", back_populates="subject")

    def __repr__(self):
        return f"<Subject(subject_id={self.subject_id}, condition={self.condition}, age={self.age}, sex={self.sex})>"

    def to_dict(self):
        return {
            "subject_id": self.subject_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "condition": self.condition,
            "age": self.age,
            "sex": self.sex,
        }


class Sample(Base):
    """Sample table model"""

    __tablename__ = "samples"

    sample_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.subject_id"), nullable=False)
    treatment = Column(Integer, nullable=True)
    response = Column(Boolean, nullable=True)
    sample_type = Column(Integer, nullable=True)
    time_from_treatment_start = Column(Integer, nullable=True)
    b_cell = Column(Integer, nullable=True)
    cd8_t_cell = Column(Integer, nullable=True)
    cd4_t_cell = Column(Integer, nullable=True)
    nk_cell = Column(Integer, nullable=True)
    monocyte = Column(Integer, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="samples")
    subject = relationship("Subject", back_populates="samples")

    def __repr__(self):
        return f"<Sample(sample_id={self.sample_id}, project_id={self.project_id}, subject_id={self.subject_id})>"

    def to_dict(self, include_relations=False):
        data = {
            "sample_id": self.sample_id,
            "project_id": self.project_id,
            "subject_id": self.subject_id,
            "treatment": self.treatment,
            "response": self.response,
            "sample_type": self.sample_type,
            "time_from_treatment_start": self.time_from_treatment_start,
            "b_cell": self.b_cell,
            "cd8_t_cell": self.cd8_t_cell,
            "cd4_t_cell": self.cd4_t_cell,
            "nk_cell": self.nk_cell,
            "monocyte": self.monocyte,
        }

        if include_relations:
            data["project"] = self.project.to_dict() if self.project else None
            data["subject"] = self.subject.to_dict() if self.subject else None

        return data


def create_database_engine(database_url: str):
    """Create SQLAlchemy engine with connection pooling"""
    try:
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=True,  # Set to False in production
        )
        return engine
    except Exception as e:
        print(f"Error creating database engine: {e}")
        raise


def initialize_database(database_url: str = DATABASE_URL):
    """Initialize the database with tables"""
    try:
        # Create engine
        engine = create_database_engine(database_url)

        # Test connection
        with engine.connect() as conn:
            print("Successfully connected to PostgreSQL database")

        # Create all tables
        print("Creating database tables...")
        Base.metadata.create_all(engine)
        print("Tables created successfully")

        # Create session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        return engine, SessionLocal

    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise


def insert_sample_data(session_factory):
    """Insert sample data for testing"""
    session = session_factory()

    try:
        # Create sample project
        project = Project()
        session.add(project)
        session.flush()  # To get the project_id

        # Create sample subject
        subject = Subject(condition="Control", age=35, sex="F")
        session.add(subject)
        session.flush()  # To get the subject_id

        # Create sample data
        sample = Sample(
            project_id=project.project_id,
            subject_id=subject.subject_id,
            treatment=1,
            response=True,
            sample_type=1,
            time_from_treatment_start=7,
            b_cell=150,
            cd8_t_cell=200,
            cd4_t_cell=300,
            nk_cell=50,
            monocyte=100,
        )
        session.add(sample)

        # Commit the transaction
        session.commit()
        print("Sample data inserted successfully")

        return project.project_id, subject.subject_id, sample.sample_id

    except Exception as e:
        session.rollback()
        print(f"Error inserting sample data: {e}")
        raise
    finally:
        session.close()


def verify_database_setup(session_factory):
    """Verify that the database was set up correctly"""
    session = session_factory()

    try:
        # Check table counts
        project_count = session.query(Project).count()
        subject_count = session.query(Subject).count()
        sample_count = session.query(Sample).count()

        print(f"\nDatabase verification:")
        print(f"Projects: {project_count}")
        print(f"Subjects: {subject_count}")
        print(f"Samples: {sample_count}")

        # Test a join query
        if sample_count > 0:
            sample_with_relations = (
                session.query(Sample).join(Project).join(Subject).first()
            )

            print(f"\nSample query test:")
            print(f"Sample ID: {sample_with_relations.sample_id}")
            print(f"Project created: {sample_with_relations.project.created_at}")
            print(f"Subject condition: {sample_with_relations.subject.condition}")

    except Exception as e:
        print(f"Error verifying database: {e}")
        raise
    finally:
        session.close()


def main():
    """Main function to initialize the database"""
    print("Initializing PostgreSQL database schema...")

    # Check if DATABASE_URL is provided
    if DATABASE_URL == "postgresql://username:password@localhost:5432/research_db":
        print(
            "\nWarning: Using default DATABASE_URL. Please set your actual database connection string."
        )
        print(
            "Example: export DATABASE_URL='postgresql://user:pass@localhost:5432/your_db'"
        )

        # Uncomment the next line to exit if using default URL
        # return

    try:
        # Initialize database
        engine, SessionLocal = initialize_database()

        # Insert sample data
        # print("\nInserting sample data...")
        # insert_sample_data(SessionLocal)

        # Verify setup
        verify_database_setup(SessionLocal)

        print("\nDatabase initialization completed successfully!")
        print("\nYou can now use the SessionLocal factory to create database sessions:")
        print("session = SessionLocal()")

    except Exception as e:
        print(f"\nDatabase initialization failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
