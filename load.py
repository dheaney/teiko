#!/usr/bin/env python3

import os
import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging
from typing import Dict, Tuple, Optional

from db import Base, Project, Subject, Sample

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://username:password@localhost:5432/research_db"
)


def create_db_session():
    """Create database session"""
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal(), engine


class DataFrameToDBInserter:
    """Class to handle DataFrame to database insertion with proper relationship handling"""

    def __init__(self):
        self.session, self.engine = create_db_session()
        self.project_cache = {}  # Cache for project lookups
        self.subject_cache = {}  # Cache for subject lookups
        self.stats = {
            "projects_created": 0,
            "subjects_created": 0,
            "samples_created": 0,
            "errors": 0,
            "duplicates_skipped": 0,
        }

    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate the dataframe"""
        logger.info("Cleaning dataframe...")

        # Make a copy to avoid modifying original
        df_clean = df.copy()

        # Convert numeric columns, handling NaN and inf values
        numeric_columns = [
            "age",
            "time_from_treatment_start",
            "b_cell",
            "cd8_t_cell",
            "cd4_t_cell",
            "nk_cell",
            "monocyte",
        ]

        for col in numeric_columns:
            if col in df_clean.columns:
                # Replace inf with NaN
                df_clean[col] = df_clean[col].replace([np.inf, -np.inf], np.nan)
                # Convert to numeric, coercing errors to NaN
                df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")
                # Convert to nullable Int64 (allows NaN in integer columns)
                df_clean[col] = df_clean[col].astype("Int64")

        # Clean string columns
        string_columns = ["condition", "sex"]
        for col in string_columns:
            if col in df_clean.columns:
                # Strip whitespace and convert empty strings to None
                df_clean[col] = df_clean[col].astype(str).str.strip()
                df_clean[col] = df_clean[col].replace(["", "nan", "NaN", "None"], None)

        # Handle response column (convert to boolean)
        if "response" in df_clean.columns:
            # Convert various representations to boolean
            response_map = {
                "true": True,
                "True": True,
                "TRUE": True,
                "1": True,
                1: True,
                "false": False,
                "False": False,
                "FALSE": False,
                "0": False,
                0: False,
                "yes": True,
                "Yes": True,
                "YES": True,
                "y": True,
                "no": False,
                "No": False,
                "NO": False,
                "n": False,
            }
            df_clean["response"] = df_clean["response"].map(response_map)

        if "treatment" in df_clean.columns:
            response_map = {
                "tr1": 1,
                "Tr1": 1,
                "tr 1": 1,
                "1": 1,
                "tr2": 2,
                "Tr2": 2,
                "tr 2": 2,
                "2": 2,
            }
            df_clean["treatment"] = df_clean["treatment"].map(response_map)

        if "sample_type" in df_clean.columns:
            response_map = {
                "PBMC": 1,
                "pbmc": 1,
                "Pbmc": 1,
                "TUMOR": 2,
                "tumor": 2,
                "Tumor": 2,
            }
            df_clean["sample_type"] = df_clean["sample_type"].map(response_map)

        # Ensure required columns exist
        required_columns = ["project", "subject"]
        missing_columns = [
            col for col in required_columns if col not in df_clean.columns
        ]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        logger.info(
            f"Cleaned dataframe: {len(df_clean)} rows, {len(df_clean.columns)} columns"
        )
        return df_clean

    def get_or_create_project(self, project_identifier: str) -> int:
        """Get existing project or create new one"""
        # Use project identifier as cache key
        if project_identifier in self.project_cache:
            return self.project_cache[project_identifier]

        # For this implementation, we'll create a new project for each unique identifier
        # In a real scenario, you might want to look up existing projects first
        try:
            new_project = Project()
            self.session.add(new_project)
            self.session.flush()  # Get the ID without committing

            project_id = new_project.project_id
            self.project_cache[project_identifier] = project_id
            self.stats["projects_created"] += 1

            logger.debug(
                f"Created project {project_id} for identifier '{project_identifier}'"
            )
            return project_id

        except Exception as e:
            logger.error(f"Error creating project for '{project_identifier}': {e}")
            raise

    def get_or_create_subject(
        self,
        subject_identifier: str,
        condition: str,
        age: Optional[int],
        sex: Optional[str],
    ) -> int:
        """Get existing subject or create new one"""
        # Create a cache key that includes subject characteristics
        cache_key = f"{subject_identifier}_{condition}_{age}_{sex}"

        if cache_key in self.subject_cache:
            return self.subject_cache[cache_key]

        # Look for existing subject first (by identifier and characteristics)
        existing_subject = (
            self.session.query(Subject)
            .filter(
                Subject.condition == condition, Subject.age == age, Subject.sex == sex
            )
            .first()
        )

        if existing_subject:
            self.subject_cache[cache_key] = existing_subject.subject_id
            return existing_subject.subject_id

        # Create new subject
        try:
            new_subject = Subject(condition=condition, age=age, sex=sex)
            self.session.add(new_subject)
            self.session.flush()  # Get the ID without committing

            subject_id = new_subject.subject_id
            self.subject_cache[cache_key] = subject_id
            self.stats["subjects_created"] += 1

            logger.debug(
                f"Created subject {subject_id} for identifier '{subject_identifier}'"
            )
            return subject_id

        except Exception as e:
            logger.error(f"Error creating subject for '{subject_identifier}': {e}")
            raise

    def insert_sample(self, row: pd.Series, project_id: int, subject_id: int) -> bool:
        """Insert a single sample"""
        try:
            # Convert pandas NA/NaN to None for database
            def convert_value(val):
                if pd.isna(val):
                    return None
                return val

            sample = Sample(
                project_id=project_id,
                subject_id=subject_id,
                treatment=convert_value(row.get("treatment")),
                response=convert_value(row.get("response")),
                sample_type=convert_value(row.get("sample_type")),
                time_from_treatment_start=convert_value(
                    row.get("time_from_treatment_start")
                ),
                b_cell=convert_value(row.get("b_cell")),
                cd8_t_cell=convert_value(row.get("cd8_t_cell")),
                cd4_t_cell=convert_value(row.get("cd4_t_cell")),
                nk_cell=convert_value(row.get("nk_cell")),
                monocyte=convert_value(row.get("monocyte")),
            )

            self.session.add(sample)
            self.stats["samples_created"] += 1
            return True

        except Exception as e:
            logger.error(f"Error creating sample: {e}")
            self.stats["errors"] += 1
            return False

    def insert_dataframe(self, df: pd.DataFrame, commit_frequency: int = 100) -> Dict:
        """Insert entire dataframe into database"""
        logger.info(f"Starting insertion of {len(df)} rows...")

        try:
            # Clean the dataframe
            df_clean = self.clean_dataframe(df)

            # Process rows in batches
            total_rows = len(df_clean)
            processed_rows = 0

            for index, row in df_clean.iterrows():
                try:
                    # Get or create project
                    project_id = self.get_or_create_project(str(row["project"]))

                    # Get or create subject
                    subject_id = self.get_or_create_subject(
                        str(row["subject"]),
                        row.get("condition"),
                        row.get("age"),
                        row.get("sex"),
                    )

                    # Insert sample
                    self.insert_sample(row, project_id, subject_id)

                    processed_rows += 1

                    # Commit periodically to avoid memory issues
                    if processed_rows % commit_frequency == 0:
                        self.session.commit()
                        logger.info(
                            f"Processed {processed_rows}/{total_rows} rows "
                            f"({processed_rows/total_rows*100:.1f}%)"
                        )

                except Exception as e:
                    logger.error(f"Error processing row {index}: {e}")
                    self.stats["errors"] += 1
                    self.session.rollback()

                    # Re-establish session after rollback
                    self.session.close()
                    self.session, _ = create_db_session()
                    continue

            # Final commit
            self.session.commit()
            logger.info("All data committed successfully!")

            return {
                "success": True,
                "stats": self.stats,
                "total_rows_processed": processed_rows,
            }

        except Exception as e:
            logger.error(f"Fatal error during insertion: {e}")
            self.session.rollback()
            return {"success": False, "error": str(e), "stats": self.stats}
        finally:
            self.session.close()


def load_dataframe_from_csv(file_path: str) -> pd.DataFrame:
    """Load dataframe from CSV file"""
    try:
        df = pd.read_csv(file_path)
        logger.info(f"Loaded dataframe from {file_path}: {df.shape}")
        return df
    except Exception as e:
        logger.error(f"Error loading CSV file: {e}")
        raise


def validate_dataframe_columns(df: pd.DataFrame) -> bool:
    """Validate that dataframe has required columns"""
    expected_columns = [
        "project",
        "subject",
        "condition",
        "age",
        "sex",
        "treatment",
        "response",
        "sample",
        "sample_type",
        "time_from_treatment_start",
        "b_cell",
        "cd8_t_cell",
        "cd4_t_cell",
        "nk_cell",
        "monocyte",
    ]

    missing_columns = [col for col in expected_columns if col not in df.columns]
    extra_columns = [col for col in df.columns if col not in expected_columns]

    if missing_columns:
        logger.warning(f"Missing columns: {missing_columns}")

    if extra_columns:
        logger.info(f"Extra columns (will be ignored): {extra_columns}")

    # Only require essential columns
    required_columns = ["project", "subject"]
    missing_required = [col for col in required_columns if col not in df.columns]

    if missing_required:
        logger.error(f"Missing required columns: {missing_required}")
        return False

    return True


def main():
    """Main function to run the insertion script"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Insert DataFrame data into research database"
    )
    parser.add_argument("csv_file", help="Path to CSV file containing the data")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for processing (default: 1000)",
    )
    parser.add_argument(
        "--commit-frequency",
        type=int,
        default=100,
        help="How often to commit (default: every 100 rows)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate data without inserting"
    )

    args = parser.parse_args()

    try:
        # Load dataframe
        logger.info(f"Loading data from {args.csv_file}")
        df = load_dataframe_from_csv(args.csv_file)

        # Validate columns
        if not validate_dataframe_columns(df):
            logger.error("Column validation failed")
            return 1

        # Show data preview
        logger.info("Data preview:")
        logger.info(f"Shape: {df.shape}")
        logger.info(f"Columns: {list(df.columns)}")
        logger.info("First few rows:")
        logger.info(df.head().to_string())

        if args.dry_run:
            logger.info("Dry run completed - no data was inserted")
            return 0

        # Insert data
        inserter = DataFrameToDBInserter()
        result = inserter.insert_dataframe(df, commit_frequency=args.commit_frequency)

        # Print results
        if result["success"]:
            logger.info("Insertion completed successfully!")
            logger.info(f"Statistics: {result['stats']}")
        else:
            logger.error(f"Insertion failed: {result['error']}")
            logger.info(f"Partial statistics: {result['stats']}")
            return 1

    except Exception as e:
        logger.error(f"Script failed: {e}")
        return 1

    return 0


# Example usage function
def example_usage():
    """Example of how to use the inserter with a sample dataframe"""
    # Create sample dataframe
    sample_data = {
        "project": ["proj_1", "proj_1", "proj_2", "proj_2"],
        "subject": ["subj_001", "subj_001", "subj_002", "subj_002"],
        "condition": ["Control", "Control", "Treatment", "Treatment"],
        "age": [35, 35, 42, 42],
        "sex": ["F", "F", "M", "M"],
        "treatment": [1, 2, 1, 2],
        "response": [True, False, True, True],
        "sample": ["sample_001", "sample_002", "sample_003", "sample_004"],
        "sample_type": [1, 1, 2, 2],
        "time_from_treatment_start": [7, 14, 7, 14],
        "b_cell": [150, 160, 140, 155],
        "cd8_t_cell": [200, 210, 190, 205],
        "cd4_t_cell": [300, 310, 290, 305],
        "nk_cell": [50, 55, 45, 52],
        "monocyte": [100, 105, 95, 102],
    }

    df = pd.DataFrame(sample_data)
    logger.info("Example dataframe:")
    logger.info(df.to_string())

    # Insert the data
    inserter = DataFrameToDBInserter()
    result = inserter.insert_dataframe(df)

    logger.info(f"Example insertion result: {result}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "example":
        example_usage()
    else:
        exit(main())
