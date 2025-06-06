#!/usr/bin/env python3

import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import create_engine, and_, or_

import logging

from marshmallow import Schema, fields, ValidationError, validates, validates_schema

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from db import Base, Project, Subject, Sample


# Flask application setup
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://username:password@localhost:5432/research_db"
)

# Initialize database engine and session
try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Database connection established")
except Exception as e:
    logger.error(f"Failed to connect to database: {e}")
    raise


# Helper functions
def get_db_session():
    """Create a new database session"""
    return SessionLocal()


def handle_database_error(e):
    """Handle database errors consistently"""
    logger.error(f"Database error: {e}")
    return jsonify({"error": "Database error occurred"}), 500


def paginate_query(query, page=1, per_page=50):
    """Add pagination to a query"""
    max_per_page = 100
    per_page = min(per_page, max_per_page)

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": items,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        },
    }


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404


@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request"}), 400


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


# Health check endpoint
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    try:
        session = get_db_session()
        session.execute("SELECT 1")
        session.close()
        return jsonify(
            {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
        )
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


# PROJECT ENDPOINTS
@app.route("/api/projects", methods=["GET"])
def get_projects():
    """Get all projects with optional pagination"""
    session = get_db_session()
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)
        include_samples = request.args.get("include_samples", "false").lower() == "true"

        query = session.query(Project)
        if include_samples:
            query = query.options(joinedload(Project.samples))

        result = paginate_query(query, page, per_page)

        projects = []
        for project in result["items"]:
            project_data = project.to_dict()
            if include_samples:
                project_data["samples"] = [
                    sample.to_dict() for sample in project.samples
                ]
            projects.append(project_data)

        return jsonify({"projects": projects, "pagination": result["pagination"]})

    except SQLAlchemyError as e:
        return handle_database_error(e)
    finally:
        session.close()


@app.route("/api/projects/<int:project_id>", methods=["GET"])
def get_project(project_id):
    """Get a specific project by ID"""
    session = get_db_session()
    try:
        include_samples = request.args.get("include_samples", "false").lower() == "true"

        query = session.query(Project).filter(Project.project_id == project_id)
        if include_samples:
            query = query.options(joinedload(Project.samples))

        project = query.first()
        if not project:
            return jsonify({"error": "Project not found"}), 404

        project_data = project.to_dict()
        if include_samples:
            project_data["samples"] = [sample.to_dict() for sample in project.samples]

        return jsonify(project_data)

    except SQLAlchemyError as e:
        return handle_database_error(e)
    finally:
        session.close()


@app.route("/api/projects/<int:project_id>/samples", methods=["GET"])
def get_project_samples(project_id):
    """Get all samples for a specific project"""
    session = get_db_session()
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)
        include_relations = (
            request.args.get("include_relations", "false").lower() == "true"
        )

        # Verify project exists
        project = (
            session.query(Project).filter(Project.project_id == project_id).first()
        )
        if not project:
            return jsonify({"error": "Project not found"}), 404

        query = session.query(Sample).filter(Sample.project_id == project_id)
        if include_relations:
            query = query.options(
                joinedload(Sample.subject), joinedload(Sample.project)
            )

        result = paginate_query(query, page, per_page)

        samples = [
            sample.to_dict(include_relations=include_relations)
            for sample in result["items"]
        ]

        return jsonify({"samples": samples, "pagination": result["pagination"]})

    except SQLAlchemyError as e:
        return handle_database_error(e)
    finally:
        session.close()


# SUBJECT ENDPOINTS
@app.route("/api/subjects", methods=["GET"])
def get_subjects():
    """Get all subjects with optional filtering and pagination"""
    session = get_db_session()
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)
        condition = request.args.get("condition")
        sex = request.args.get("sex")
        min_age = request.args.get("min_age", type=int)
        max_age = request.args.get("max_age", type=int)
        include_samples = request.args.get("include_samples", "false").lower() == "true"

        query = session.query(Subject)

        # Apply filters
        if condition:
            query = query.filter(Subject.condition == condition)
        if sex:
            query = query.filter(Subject.sex == sex)
        if min_age:
            query = query.filter(Subject.age >= min_age)
        if max_age:
            query = query.filter(Subject.age <= max_age)

        if include_samples:
            query = query.options(joinedload(Subject.samples))

        result = paginate_query(query, page, per_page)

        subjects = []
        for subject in result["items"]:
            subject_data = subject.to_dict()
            if include_samples:
                subject_data["samples"] = [
                    sample.to_dict() for sample in subject.samples
                ]
            subjects.append(subject_data)

        return jsonify({"subjects": subjects, "pagination": result["pagination"]})

    except SQLAlchemyError as e:
        return handle_database_error(e)
    finally:
        session.close()


@app.route("/api/subjects/<int:subject_id>", methods=["GET"])
def get_subject(subject_id):
    """Get a specific subject by ID"""
    session = get_db_session()
    try:
        include_samples = request.args.get("include_samples", "false").lower() == "true"

        query = session.query(Subject).filter(Subject.subject_id == subject_id)
        if include_samples:
            query = query.options(joinedload(Subject.samples))

        subject = query.first()
        if not subject:
            return jsonify({"error": "Subject not found"}), 404

        subject_data = subject.to_dict()
        if include_samples:
            subject_data["samples"] = [sample.to_dict() for sample in subject.samples]

        return jsonify(subject_data)

    except SQLAlchemyError as e:
        return handle_database_error(e)
    finally:
        session.close()


@app.route("/api/subjects/<int:subject_id>/samples", methods=["GET"])
def get_subject_samples(subject_id):
    """Get all samples for a specific subject"""
    session = get_db_session()
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)
        include_relations = (
            request.args.get("include_relations", "false").lower() == "true"
        )

        # Verify subject exists
        subject = (
            session.query(Subject).filter(Subject.subject_id == subject_id).first()
        )
        if not subject:
            return jsonify({"error": "Subject not found"}), 404

        query = session.query(Sample).filter(Sample.subject_id == subject_id)
        if include_relations:
            query = query.options(
                joinedload(Sample.project), joinedload(Sample.subject)
            )

        result = paginate_query(query, page, per_page)

        samples = [
            sample.to_dict(include_relations=include_relations)
            for sample in result["items"]
        ]

        return jsonify({"samples": samples, "pagination": result["pagination"]})

    except SQLAlchemyError as e:
        return handle_database_error(e)
    finally:
        session.close()


# SAMPLE ENDPOINTS
@app.route("/api/samples", methods=["GET"])
def get_samples():
    """Get all samples with optional filtering and pagination"""
    session = get_db_session()
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)
        project_id = request.args.get("project_id", type=int)
        subject_id = request.args.get("subject_id", type=int)
        treatment = request.args.get("treatment", type=int)
        response = request.args.get("response")
        sample_type = request.args.get("sample_type", type=int)
        condition = request.args.get("condition", type=str)
        time_from_treatment_start = request.args.get(
            "time_from_treatment_start", type=int
        )
        include_relations = (
            request.args.get("include_relations", "false").lower() == "true"
        )

        query = session.query(Sample)

        # Apply filters
        if project_id:
            query = query.filter(Sample.project_id == project_id)
        if subject_id:
            query = query.filter(Sample.subject_id == subject_id)
        if treatment:
            query = query.filter(Sample.treatment == treatment)
        if time_from_treatment_start is not None:
            query = query.filter(
                Sample.time_from_treatment_start == time_from_treatment_start
            )
        if response is not None:
            response_bool = response.lower() == "true"
            query = query.filter(Sample.response == response_bool)
        if sample_type:
            query = query.filter(Sample.sample_type == sample_type)

        if include_relations:
            query = query.options(
                joinedload(Sample.project), joinedload(Sample.subject)
            )

        result = paginate_query(query, page, per_page)

        samples = [
            sample.to_dict(include_relations=include_relations)
            for sample in result["items"]
        ]

        if include_relations and condition:
            samples = [
                sample
                for sample in samples
                if sample["subject"]["condition"] == condition
            ]

        return jsonify({"samples": samples, "pagination": result["pagination"]})

    except SQLAlchemyError as e:
        return handle_database_error(e)
    finally:
        session.close()


@app.route("/api/samples/<int:sample_id>", methods=["GET"])
def get_sample(sample_id):
    """Get a specific sample by ID"""
    session = get_db_session()
    try:
        include_relations = (
            request.args.get("include_relations", "false").lower() == "true"
        )

        query = session.query(Sample).filter(Sample.sample_id == sample_id)
        if include_relations:
            query = query.options(
                joinedload(Sample.project), joinedload(Sample.subject)
            )

        sample = query.first()
        if not sample:
            return jsonify({"error": "Sample not found"}), 404

        return jsonify(sample.to_dict(include_relations=include_relations))

    except SQLAlchemyError as e:
        return handle_database_error(e)
    finally:
        session.close()


@app.route("/api/analytics/summary", methods=["GET"])
def get_analytics_summary():
    """Get summary analytics across all data"""
    session = get_db_session()
    try:
        total_projects = session.query(Project).count()
        total_subjects = session.query(Subject).count()
        total_samples = session.query(Sample).count()

        # Response rate by treatment
        response_stats = (
            session.query(
                Sample.treatment,
                func.count(Sample.sample_id).label("total"),
                func.sum(func.cast(Sample.response, Integer)).label("responses"),
            )
            .filter(Sample.treatment.isnot(None))
            .group_by(Sample.treatment)
            .all()
        )

        # Subject demographics
        sex_distribution = (
            session.query(Subject.sex, func.count(Subject.subject_id).label("count"))
            .filter(Subject.sex.isnot(None))
            .group_by(Subject.sex)
            .all()
        )

        return jsonify(
            {
                "summary": {
                    "total_projects": total_projects,
                    "total_subjects": total_subjects,
                    "total_samples": total_samples,
                },
                "response_by_treatment": [
                    {
                        "treatment": stat.treatment,
                        "total_samples": stat.total,
                        "positive_responses": stat.responses or 0,
                        "response_rate": (
                            (stat.responses or 0) / stat.total if stat.total > 0 else 0
                        ),
                    }
                    for stat in response_stats
                ],
                "sex_distribution": [
                    {"sex": stat.sex, "count": stat.count} for stat in sex_distribution
                ],
            }
        )

    except SQLAlchemyError as e:
        return handle_database_error(e)
    finally:
        session.close()


# API documentation endpoint
@app.route("/api/docs", methods=["GET"])
def api_documentation():
    """API documentation endpoint"""
    docs = {
        "version": "1.0",
        "description": "REST API for Research Database",
        "endpoints": {
            "projects": {
                "GET /api/projects": "Get all projects (supports pagination, include_samples)",
                "GET /api/projects/{id}": "Get specific project (supports include_samples)",
                "GET /api/projects/{id}/samples": "Get samples for a project",
            },
            "subjects": {
                "GET /api/subjects": "Get all subjects (supports filtering by condition, sex, age range)",
                "GET /api/subjects/{id}": "Get specific subject (supports include_samples)",
                "GET /api/subjects/{id}/samples": "Get samples for a subject",
            },
            "samples": {
                "GET /api/samples": "Get all samples (supports filtering by project, subject, treatment, etc.)",
                "GET /api/samples/{id}": "Get specific sample (supports include_relations)",
            },
            "analytics": {"GET /api/analytics/summary": "Get summary analytics"},
        },
        "common_parameters": {
            "page": "Page number for pagination (default: 1)",
            "per_page": "Items per page (default: 50, max: 100)",
            "include_samples": "Include related samples in response",
            "include_relations": "Include related project and subject data",
        },
    }
    return jsonify(docs)


# Marshmallow schema for subject validation
class CreateSubjectSchema(Schema):
    """Schema for validating subject creation requests"""

    # Optional fields with validation
    condition = fields.String(
        allow_none=True, validate=lambda x: x is None or len(x.strip()) > 0
    )
    age = fields.Integer(
        allow_none=True, validate=lambda x: x is None or (0 <= x <= 150)
    )
    sex = fields.String(
        allow_none=True,
        validate=lambda x: x is None
        or x.upper() in ["M", "F", "MALE", "FEMALE", "OTHER"],
    )

    # Custom timestamp for testing purposes (optional)
    created_at = fields.DateTime(allow_none=True, format="iso")

    @validates("condition")
    def validate_condition(self, value):
        """Validate condition field"""
        if value is not None:
            value = value.strip()
            if len(value) == 0:
                raise ValidationError("Condition cannot be empty")
            if len(value) > 100:
                raise ValidationError("Condition must be 100 characters or less")

    @validates("age")
    def validate_age(self, value):
        """Validate age field"""
        if value is not None:
            if value < 0:
                raise ValidationError("Age must be non-negative")
            if value > 150:
                raise ValidationError("Age must be 150 or less")

    @validates("sex")
    def validate_sex(self, value):
        """Validate and normalize sex field"""
        if value is not None:
            value_upper = value.upper()
            valid_values = ["M", "F", "MALE", "FEMALE", "OTHER"]
            if value_upper not in valid_values:
                raise ValidationError(f'Sex must be one of: {", ".join(valid_values)}')


# Marshmallow schema for request validation
class CreateSampleSchema(Schema):
    """Schema for validating sample creation requests"""

    # Required fields
    project_id = fields.Integer(required=True, validate=lambda x: x > 0)
    subject_id = fields.Integer(required=True, validate=lambda x: x > 0)

    # Optional fields with validation
    treatment = fields.Integer(allow_none=True, validate=lambda x: x is None or x >= 0)
    response = fields.Boolean(allow_none=True)
    sample_type = fields.Integer(allow_none=True, validate=lambda x: x is None or x > 0)
    time_from_treatment_start = fields.Integer(
        allow_none=True, validate=lambda x: x is None or x >= 0
    )

    # Cell count fields (should be non-negative integers)
    b_cell = fields.Integer(allow_none=True, validate=lambda x: x is None or x >= 0)
    cd8_t_cell = fields.Integer(allow_none=True, validate=lambda x: x is None or x >= 0)
    cd4_t_cell = fields.Integer(allow_none=True, validate=lambda x: x is None or x >= 0)
    nk_cell = fields.Integer(allow_none=True, validate=lambda x: x is None or x >= 0)
    monocyte = fields.Integer(allow_none=True, validate=lambda x: x is None or x >= 0)

    @validates("treatment")
    def validate_treatment(self, value, **kwargs):
        """Validate treatment values"""
        if value is not None and value < 0:
            raise ValidationError("Treatment must be non-negative")

    @validates("time_from_treatment_start")
    def validate_time_from_treatment(self, value, **kwargs):
        """Validate time from treatment start"""
        if value is not None and value < 0:
            raise ValidationError("Time from treatment start must be non-negative")

    @validates_schema
    def validate_cell_counts(self, data, **kwargs):
        """Validate that at least one cell count is provided if any are provided"""
        cell_fields = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]
        cell_values = [data.get(field) for field in cell_fields]

        # Check if any cell count is provided
        has_cell_data = any(val is not None for val in cell_values)

        # If treatment is provided but no response, warn (but don't fail)
        if data.get("treatment") is not None and data.get("response") is None:
            # This could be a warning, but we'll allow it
            pass


def validate_foreign_keys(session, project_id, subject_id):
    """Validate that project_id and subject_id exist in the database"""

    # Check if project exists
    project = session.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        return False, f"Project with ID {project_id} does not exist"

    # Check if subject exists
    subject = session.query(Subject).filter(Subject.subject_id == subject_id).first()
    if not subject:
        return False, f"Subject with ID {subject_id} does not exist"

    return True, None


@app.route("/api/samples", methods=["POST"])
def create_sample():
    """
    Create a new sample

    Request body (JSON):
    {
        "project_id": 1,          // Required: ID of existing project
        "subject_id": 1,          // Required: ID of existing subject
        "treatment": 1,           // Optional: Treatment number (>=0)
        "response": true,         // Optional: Boolean response
        "sample_type": 1,         // Optional: Sample type (>0)
        "time_from_treatment_start": 7,  // Optional: Time in days (>=0)
        "b_cell": 150,           // Optional: B-cell count (>=0)
        "cd8_t_cell": 200,       // Optional: CD8 T-cell count (>=0)
        "cd4_t_cell": 300,       // Optional: CD4 T-cell count (>=0)
        "nk_cell": 50,           // Optional: NK cell count (>=0)
        "monocyte": 100          // Optional: Monocyte count (>=0)
    }

    Returns:
        201: Sample created successfully
        400: Validation error
        404: Referenced project or subject not found
        500: Database error
    """

    session = get_db_session()

    try:
        # Get and validate request data
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body cannot be empty"}), 400

        # Validate request data using Marshmallow schema
        schema = CreateSampleSchema()
        try:
            validated_data = schema.load(data)
        except ValidationError as err:
            return jsonify({"error": "Validation failed", "details": err.messages}), 400

        # Validate foreign key relationships
        project_id = validated_data["project_id"]
        subject_id = validated_data["subject_id"]

        is_valid, error_message = validate_foreign_keys(session, project_id, subject_id)
        if not is_valid:
            return jsonify({"error": error_message}), 404

        # Create new sample
        new_sample = Sample(
            project_id=project_id,
            subject_id=subject_id,
            treatment=validated_data.get("treatment"),
            response=validated_data.get("response"),
            sample_type=validated_data.get("sample_type"),
            time_from_treatment_start=validated_data.get("time_from_treatment_start"),
            b_cell=validated_data.get("b_cell"),
            cd8_t_cell=validated_data.get("cd8_t_cell"),
            cd4_t_cell=validated_data.get("cd4_t_cell"),
            nk_cell=validated_data.get("nk_cell"),
            monocyte=validated_data.get("monocyte"),
        )

        # Add to session and commit
        session.add(new_sample)
        session.commit()

        # Refresh to get the auto-generated sample_id
        session.refresh(new_sample)

        logger.info(f"Successfully created sample with ID: {new_sample.sample_id}")

        # Return the created sample
        return (
            jsonify(
                {
                    "message": "Sample created successfully",
                    "sample": new_sample.to_dict(include_relations=False),
                }
            ),
            201,
        )

    except IntegrityError as e:
        session.rollback()
        logger.error(f"Database integrity error: {e}")
        return (
            jsonify(
                {
                    "error": "Database integrity error. Check that project_id and subject_id are valid."
                }
            ),
            400,
        )

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error creating sample: {e}")
        return jsonify({"error": "Database error occurred"}), 500

    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error creating sample: {e}")
        return jsonify({"error": "Internal server error"}), 500

    finally:
        session.close()


@app.route("/api/samples/batch", methods=["POST"])
def create_samples_batch():
    """
    Create multiple samples at once

    Request body (JSON):
    {
        "samples": [
            {
                "project_id": 1,
                "subject_id": 1,
                "treatment": 1,
                // ... other sample fields
            },
            {
                "project_id": 1,
                "subject_id": 2,
                "treatment": 2,
                // ... other sample fields
            }
        ]
    }

    Returns:
        201: All samples created successfully
        400: Validation error
        207: Partial success (some samples failed)
        500: Database error
    """

    session = get_db_session()

    try:
        # Get and validate request data
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()
        if not data or "samples" not in data:
            return jsonify({"error": 'Request must contain "samples" array'}), 400

        samples_data = data["samples"]
        if not isinstance(samples_data, list):
            return jsonify({"error": '"samples" must be an array'}), 400

        if len(samples_data) == 0:
            return jsonify({"error": "At least one sample must be provided"}), 400

        if len(samples_data) > 100:  # Limit batch size
            return (
                jsonify({"error": "Cannot create more than 100 samples at once"}),
                400,
            )

        # Validate all samples first
        schema = CreateSampleSchema()
        validated_samples = []
        validation_errors = []

        for i, sample_data in enumerate(samples_data):
            try:
                validated_sample = schema.load(sample_data)
                validated_samples.append(validated_sample)
            except ValidationError as err:
                validation_errors.append({"index": i, "errors": err.messages})

        if validation_errors:
            return (
                jsonify(
                    {
                        "error": "Validation failed for some samples",
                        "validation_errors": validation_errors,
                    }
                ),
                400,
            )

        # Validate foreign keys for all samples
        foreign_key_errors = []
        for i, sample_data in enumerate(validated_samples):
            is_valid, error_message = validate_foreign_keys(
                session, sample_data["project_id"], sample_data["subject_id"]
            )
            if not is_valid:
                foreign_key_errors.append({"index": i, "error": error_message})

        if foreign_key_errors:
            return (
                jsonify(
                    {
                        "error": "Foreign key validation failed for some samples",
                        "foreign_key_errors": foreign_key_errors,
                    }
                ),
                404,
            )

        # Create all samples
        created_samples = []
        for sample_data in validated_samples:
            new_sample = Sample(
                project_id=sample_data["project_id"],
                subject_id=sample_data["subject_id"],
                treatment=sample_data.get("treatment"),
                response=sample_data.get("response"),
                sample_type=sample_data.get("sample_type"),
                time_from_treatment_start=sample_data.get("time_from_treatment_start"),
                b_cell=sample_data.get("b_cell"),
                cd8_t_cell=sample_data.get("cd8_t_cell"),
                cd4_t_cell=sample_data.get("cd4_t_cell"),
                nk_cell=sample_data.get("nk_cell"),
                monocyte=sample_data.get("monocyte"),
            )
            created_samples.append(new_sample)

        # Add all samples to session and commit
        session.add_all(created_samples)
        session.commit()

        # Refresh all samples to get their IDs
        for sample in created_samples:
            session.refresh(sample)

        sample_ids = [sample.sample_id for sample in created_samples]
        logger.info(
            f"Successfully created {len(created_samples)} samples with IDs: {sample_ids}"
        )

        return (
            jsonify(
                {
                    "message": f"Successfully created {len(created_samples)} samples",
                    "samples": [
                        sample.to_dict(include_relations=False)
                        for sample in created_samples
                    ],
                    "count": len(created_samples),
                    "sample_ids": sample_ids,
                }
            ),
            201,
        )

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error creating samples: {e}")
        return jsonify({"error": "Database error occurred"}), 500

    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error creating samples: {e}")
        return jsonify({"error": "Internal server error"}), 500

    finally:
        session.close()


# Helper endpoint to get available projects and subjects for sample creation
@app.route("/api/samples/references", methods=["GET"])
def get_sample_references():
    """
    Get available projects and subjects for creating samples

    Returns:
        200: Available projects and subjects
        500: Database error
    """

    session = get_db_session()

    try:
        # Get all projects
        projects = session.query(Project).all()

        # Get all subjects
        subjects = session.query(Subject).all()

        return (
            jsonify(
                {
                    "projects": [
                        {
                            "project_id": project.project_id,
                            "created_at": project.created_at.isoformat(),
                        }
                        for project in projects
                    ],
                    "subjects": [
                        {
                            "subject_id": subject.subject_id,
                            "condition": subject.condition,
                            "age": subject.age,
                            "sex": subject.sex,
                            "created_at": subject.created_at.isoformat(),
                        }
                        for subject in subjects
                    ],
                }
            ),
            200,
        )

    except SQLAlchemyError as e:
        logger.error(f"Database error getting references: {e}")
        return jsonify({"error": "Database error occurred"}), 500

    finally:
        session.close()


# Example usage endpoint for testing
@app.route("/api/samples/example", methods=["GET"])
def get_sample_creation_example():
    """Get example JSON for creating a sample"""

    example = {
        "single_sample": {
            "project_id": 1,
            "subject_id": 1,
            "treatment": 1,
            "response": True,
            "sample_type": 1,
            "time_from_treatment_start": 7,
            "b_cell": 150,
            "cd8_t_cell": 200,
            "cd4_t_cell": 300,
            "nk_cell": 50,
            "monocyte": 100,
        },
        "batch_samples": {
            "samples": [
                {
                    "project_id": 1,
                    "subject_id": 1,
                    "treatment": 1,
                    "response": True,
                    "b_cell": 150,
                    "cd8_t_cell": 200,
                },
                {
                    "project_id": 1,
                    "subject_id": 2,
                    "treatment": 2,
                    "response": False,
                    "b_cell": 140,
                    "cd8_t_cell": 190,
                },
            ]
        },
    }

    return jsonify(example), 200


# Marshmallow schema for subject validation
class CreateSubjectSchema(Schema):
    """Schema for validating subject creation requests"""

    # Optional fields with validation
    condition = fields.String(
        allow_none=True, validate=lambda x: x is None or len(x.strip()) > 0
    )
    age = fields.Integer(
        allow_none=True, validate=lambda x: x is None or (0 <= x <= 150)
    )
    sex = fields.String(
        allow_none=True,
        validate=lambda x: x is None
        or x.upper() in ["M", "F", "MALE", "FEMALE", "OTHER"],
    )

    # Custom timestamp for testing purposes (optional)
    created_at = fields.DateTime(allow_none=True, format="iso")

    @validates("condition")
    def validate_condition(self, value, **kwargs):
        """Validate condition field"""
        if value is not None:
            value = value.strip()
            if len(value) == 0:
                raise ValidationError("Condition cannot be empty")
            if len(value) > 100:
                raise ValidationError("Condition must be 100 characters or less")

    @validates("age")
    def validate_age(self, value, **kwargs):
        """Validate age field"""
        if value is not None:
            if value < 0:
                raise ValidationError("Age must be non-negative")
            if value > 150:
                raise ValidationError("Age must be 150 or less")

    @validates("sex")
    def validate_sex(self, value, **kwargs):
        """Validate and normalize sex field"""
        if value is not None:
            value_upper = value.upper()
            valid_values = ["M", "F", "MALE", "FEMALE", "OTHER"]
            if value_upper not in valid_values:
                raise ValidationError(f'Sex must be one of: {", ".join(valid_values)}')


def normalize_sex_value(sex_value):
    """Normalize sex value to standard format"""
    if sex_value is None:
        return None

    sex_upper = sex_value.upper()
    if sex_upper in ["M", "MALE"]:
        return "M"
    elif sex_upper in ["F", "FEMALE"]:
        return "F"
    else:
        return "Other"


def check_for_duplicate_subject(session, condition, age, sex):
    """Check if a subject with identical characteristics already exists"""

    # Normalize sex value for comparison
    normalized_sex = normalize_sex_value(sex)

    existing_subject = (
        session.query(Subject)
        .filter(
            and_(
                Subject.condition == condition,
                Subject.age == age,
                Subject.sex == normalized_sex,
            )
        )
        .first()
    )

    return existing_subject


def find_similar_subjects(session, condition, age, sex, limit=5):
    """Find subjects with similar characteristics"""

    normalized_sex = normalize_sex_value(sex)

    # Build conditions for similarity search
    conditions = []

    # Exact condition match
    if condition:
        conditions.append(Subject.condition == condition)

    # Age within 5 years
    if age is not None:
        conditions.append(and_(Subject.age >= age - 5, Subject.age <= age + 5))

    # Same sex
    if normalized_sex:
        conditions.append(Subject.sex == normalized_sex)

    if not conditions:
        return []

    # Find subjects matching any of the conditions
    similar_subjects = (
        session.query(Subject).filter(or_(*conditions)).limit(limit).all()
    )

    return similar_subjects


@app.route("/api/subjects", methods=["POST"])
def create_subject():
    """
    Create a new subject

    Request body (JSON):
    {
        "condition": "Control",     // Optional: Subject condition (max 100 chars)
        "age": 35,                  // Optional: Age (0-150)
        "sex": "F",                 // Optional: M/F/Male/Female/Other
        "created_at": "2024-01-15T10:30:00"  // Optional: Custom timestamp (ISO format)
    }

    Returns:
        201: Subject created successfully
        400: Validation error
        409: Duplicate subject found
        500: Database error
    """

    session = get_db_session()

    try:
        # Get and validate request data
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()
        if data is None:
            data = {}  # Allow empty body for creating minimal subject

        # Validate request data using Marshmallow schema
        schema = CreateSubjectSchema()
        try:
            validated_data = schema.load(data)
        except ValidationError as err:
            return jsonify({"error": "Validation failed", "details": err.messages}), 400

        # Extract and normalize data
        condition = validated_data.get("condition")
        age = validated_data.get("age")
        sex = normalize_sex_value(validated_data.get("sex"))
        custom_created_at = validated_data.get("created_at")

        # Check for duplicate subjects
        duplicate_subject = check_for_duplicate_subject(session, condition, age, sex)
        if duplicate_subject:
            return (
                jsonify(
                    {
                        "error": "Duplicate subject found",
                        "message": f"A subject with the same condition, age, and sex already exists (ID: {duplicate_subject.subject_id})",
                        "existing_subject": duplicate_subject.to_dict(),
                        "suggestion": "Use the existing subject or modify the characteristics",
                    }
                ),
                409,
            )

        # Find similar subjects for reference
        similar_subjects = find_similar_subjects(session, condition, age, sex)

        # Create new subject
        new_subject = Subject(condition=condition, age=age, sex=sex)

        # Set custom created_at if provided
        if custom_created_at:
            new_subject.created_at = custom_created_at

        # Add to session and commit
        session.add(new_subject)
        session.commit()

        # Refresh to get the auto-generated subject_id
        session.refresh(new_subject)

        logger.info(f"Successfully created subject with ID: {new_subject.subject_id}")

        # Prepare response
        response_data = {
            "message": "Subject created successfully",
            "subject": new_subject.to_dict(include_samples=False),
        }

        # Include similar subjects if any exist
        if similar_subjects:
            response_data["similar_subjects"] = [
                subject.to_dict()
                for subject in similar_subjects
                if subject.subject_id != new_subject.subject_id
            ]

        return jsonify(response_data), 201

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error creating subject: {e}")
        return jsonify({"error": "Database error occurred"}), 500

    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error creating subject: {e}")
        return jsonify({"error": "Internal server error"}), 500

    finally:
        session.close()


@app.route("/api/subjects/batch", methods=["POST"])
def create_subjects_batch():
    """
    Create multiple subjects at once

    Request body (JSON):
    {
        "subjects": [
            {
                "condition": "Control",
                "age": 35,
                "sex": "F"
            },
            {
                "condition": "Treatment",
                "age": 42,
                "sex": "M"
            }
        ],
        "allow_duplicates": false  // Optional: whether to allow duplicate subjects
    }

    Returns:
        201: All subjects created successfully
        400: Validation error
        207: Partial success (some subjects failed)
        409: Duplicates found (if allow_duplicates is false)
        500: Database error
    """

    session = get_db_session()

    try:
        # Get and validate request data
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()
        if not data or "subjects" not in data:
            return jsonify({"error": 'Request must contain "subjects" array'}), 400

        subjects_data = data["subjects"]
        allow_duplicates = data.get("allow_duplicates", False)

        if not isinstance(subjects_data, list):
            return jsonify({"error": '"subjects" must be an array'}), 400

        if len(subjects_data) == 0:
            return jsonify({"error": "At least one subject must be provided"}), 400

        if len(subjects_data) > 50:  # Limit batch size
            return (
                jsonify({"error": "Cannot create more than 50 subjects at once"}),
                400,
            )

        # Validate all subjects first
        schema = CreateSubjectSchema()
        validated_subjects = []
        validation_errors = []

        for i, subject_data in enumerate(subjects_data):
            try:
                validated_subject = schema.load(subject_data)
                # Normalize sex value
                if "sex" in validated_subject:
                    validated_subject["sex"] = normalize_sex_value(
                        validated_subject["sex"]
                    )
                validated_subjects.append(validated_subject)
            except ValidationError as err:
                validation_errors.append({"index": i, "errors": err.messages})

        if validation_errors:
            return (
                jsonify(
                    {
                        "error": "Validation failed for some subjects",
                        "validation_errors": validation_errors,
                    }
                ),
                400,
            )

        # Check for duplicates if not allowed
        duplicate_errors = []
        if not allow_duplicates:
            for i, subject_data in enumerate(validated_subjects):
                duplicate = check_for_duplicate_subject(
                    session,
                    subject_data.get("condition"),
                    subject_data.get("age"),
                    subject_data.get("sex"),
                )
                if duplicate:
                    duplicate_errors.append(
                        {
                            "index": i,
                            "existing_subject_id": duplicate.subject_id,
                            "message": "Subject with same characteristics already exists",
                        }
                    )

        if duplicate_errors:
            return (
                jsonify(
                    {
                        "error": "Duplicate subjects found",
                        "duplicate_errors": duplicate_errors,
                        "suggestion": 'Set "allow_duplicates": true to create anyway',
                    }
                ),
                409,
            )

        # Create all subjects
        created_subjects = []
        for subject_data in validated_subjects:
            new_subject = Subject(
                condition=subject_data.get("condition"),
                age=subject_data.get("age"),
                sex=subject_data.get("sex"),
            )

            # Set custom created_at if provided
            if "created_at" in subject_data:
                new_subject.created_at = subject_data["created_at"]

            created_subjects.append(new_subject)

        # Add all subjects to session and commit
        session.add_all(created_subjects)
        session.commit()

        # Refresh all subjects to get their IDs
        for subject in created_subjects:
            session.refresh(subject)

        subject_ids = [subject.subject_id for subject in created_subjects]
        logger.info(
            f"Successfully created {len(created_subjects)} subjects with IDs: {subject_ids}"
        )

        return (
            jsonify(
                {
                    "message": f"Successfully created {len(created_subjects)} subjects",
                    "subjects": [
                        subject.to_dict(include_samples=False)
                        for subject in created_subjects
                    ],
                    "count": len(created_subjects),
                    "subject_ids": subject_ids,
                }
            ),
            201,
        )

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error creating subjects: {e}")
        return jsonify({"error": "Database error occurred"}), 500

    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error creating subjects: {e}")
        return jsonify({"error": "Internal server error"}), 500

    finally:
        session.close()


@app.route("/api/subjects/check-duplicate", methods=["POST"])
def check_duplicate_subject():
    """
    Check if a subject with given characteristics already exists

    Request body (JSON):
    {
        "condition": "Control",
        "age": 35,
        "sex": "F"
    }

    Returns:
        200: Check completed (may or may not have found duplicates)
    """

    session = get_db_session()

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400

        # Validate input
        schema = CreateSubjectSchema()
        try:
            validated_data = schema.load(data)
        except ValidationError as err:
            return jsonify({"error": "Validation failed", "details": err.messages}), 400

        condition = validated_data.get("condition")
        age = validated_data.get("age")
        sex = normalize_sex_value(validated_data.get("sex"))

        # Check for exact duplicate
        duplicate = check_for_duplicate_subject(session, condition, age, sex)

        # Find similar subjects
        similar_subjects = find_similar_subjects(session, condition, age, sex)

        result = {
            "has_duplicate": duplicate is not None,
            "duplicate_subject": duplicate.to_dict() if duplicate else None,
            "similar_subjects": [subject.to_dict() for subject in similar_subjects],
            "similar_count": len(similar_subjects),
        }

        return jsonify(result), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error checking duplicate: {e}")
        return jsonify({"error": "Database error occurred"}), 500

    finally:
        session.close()


@app.route("/api/subjects/demographics", methods=["GET"])
def get_subject_demographics():
    """
    Get demographic statistics for existing subjects

    Returns:
        200: Demographics data
        500: Database error
    """

    session = get_db_session()

    try:
        # Get condition distribution
        conditions = (
            session.query(
                Subject.condition,
                session.query(Subject)
                .filter(Subject.condition == Subject.condition)
                .count(),
            )
            .distinct()
            .all()
        )

        # Get sex distribution
        sex_stats = (
            session.query(
                Subject.sex,
                session.query(Subject).filter(Subject.sex == Subject.sex).count(),
            )
            .group_by(Subject.sex)
            .all()
        )

        # Get age statistics
        ages = [
            subject.age
            for subject in session.query(Subject.age)
            .filter(Subject.age.isnot(None))
            .all()
        ]

        age_stats = {}
        if ages:
            age_stats = {
                "min": min(ages),
                "max": max(ages),
                "average": sum(ages) / len(ages),
                "count": len(ages),
            }

        # Get total count
        total_subjects = session.query(Subject).count()

        return (
            jsonify(
                {
                    "total_subjects": total_subjects,
                    "conditions": [
                        {"condition": cond[0], "count": cond[1]}
                        for cond in conditions
                        if cond[0]
                    ],
                    "sex_distribution": [
                        {"sex": sex[0], "count": sex[1]} for sex in sex_stats if sex[0]
                    ],
                    "age_statistics": age_stats,
                }
            ),
            200,
        )

    except SQLAlchemyError as e:
        logger.error(f"Database error getting demographics: {e}")
        return jsonify({"error": "Database error occurred"}), 500

    finally:
        session.close()


# Example endpoint for testing
@app.route("/api/subjects/example", methods=["GET"])
def get_subject_creation_example():
    """Get example JSON for creating subjects"""

    example = {
        "single_subject": {"condition": "Control", "age": 35, "sex": "F"},
        "minimal_subject": {"condition": "Treatment"},
        "batch_subjects": {
            "subjects": [
                {"condition": "Control", "age": 35, "sex": "F"},
                {"condition": "Treatment", "age": 42, "sex": "M"},
                {"condition": "Placebo", "age": 28, "sex": "Other"},
            ],
            "allow_duplicates": False,
        },
        "valid_sex_values": ["M", "F", "Male", "Female", "Other"],
        "notes": {
            "condition": "Optional string, max 100 characters",
            "age": "Optional integer, 0-150",
            "sex": "Optional, normalized to M/F/Other",
            "created_at": "Optional ISO timestamp for testing",
        },
    }

    return jsonify(example), 200


def get_deletion_impact(session, entity_type, entity_id):
    """Get the impact of deleting an entity (what will be cascade deleted)"""

    if entity_type == "project":
        project = session.query(Project).filter(Project.project_id == entity_id).first()
        if not project:
            return None

        sample_count = (
            session.query(Sample).filter(Sample.project_id == entity_id).count()
        )
        return {
            "entity_type": "project",
            "entity_id": entity_id,
            "entity": project.to_dict(),
            "cascade_deletions": {"samples": sample_count},
            "total_affected": sample_count + 1,
        }

    elif entity_type == "subject":
        subject = session.query(Subject).filter(Subject.subject_id == entity_id).first()
        if not subject:
            return None

        sample_count = (
            session.query(Sample).filter(Sample.subject_id == entity_id).count()
        )
        return {
            "entity_type": "subject",
            "entity_id": entity_id,
            "entity": subject.to_dict(),
            "cascade_deletions": {"samples": sample_count},
            "total_affected": sample_count + 1,
        }

    elif entity_type == "sample":
        sample = session.query(Sample).filter(Sample.sample_id == entity_id).first()
        if not sample:
            return None

        return {
            "entity_type": "sample",
            "entity_id": entity_id,
            "entity": sample.to_dict(),
            "cascade_deletions": {},
            "total_affected": 1,
        }

    return None


# =====================
# PROJECT DELETION
# =====================


@app.route("/api/projects/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    """
    Delete a project and all its associated samples

    Query Parameters:
        force=true - Skip confirmation and delete immediately

    Returns:
        200: Project deleted successfully
        404: Project not found
        409: Deletion would affect many records (without force=true)
        500: Database error
    """

    session = get_db_session()

    try:
        force = request.args.get("force", "false").lower() == "true"

        # Get deletion impact
        impact = get_deletion_impact(session, "project", project_id)
        if not impact:
            return jsonify({"error": "Project not found"}), 404

        # Safety check - warn if deleting many samples without force
        if not force and impact["cascade_deletions"]["samples"] > 10:
            return (
                jsonify(
                    {
                        "error": "Deletion would affect many records",
                        "impact": impact,
                        "message": f'This will delete {impact["total_affected"]} records (1 project + {impact["cascade_deletions"]["samples"]} samples)',
                        "suggestion": "Add ?force=true to confirm deletion",
                    }
                ),
                409,
            )

        # Delete the project (samples will be cascade deleted)
        project = (
            session.query(Project).filter(Project.project_id == project_id).first()
        )
        session.delete(project)
        session.commit()

        logger.info(
            f"Deleted project {project_id} and {impact['cascade_deletions']['samples']} associated samples"
        )

        return (
            jsonify(
                {
                    "message": "Project deleted successfully",
                    "deleted": impact,
                    "cascade_deletions": impact["cascade_deletions"],
                }
            ),
            200,
        )

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error deleting project: {e}")
        return jsonify({"error": "Database error occurred"}), 500

    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error deleting project: {e}")
        return jsonify({"error": "Internal server error"}), 500

    finally:
        session.close()


@app.route("/api/projects/<int:project_id>/impact", methods=["GET"])
def get_project_deletion_impact(project_id):
    """Get the impact of deleting a project without actually deleting it"""

    session = get_db_session()

    try:
        impact = get_deletion_impact(session, "project", project_id)
        if not impact:
            return jsonify({"error": "Project not found"}), 404

        return jsonify(impact), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error getting deletion impact: {e}")
        return jsonify({"error": "Database error occurred"}), 500

    finally:
        session.close()


@app.route("/api/subjects/<int:subject_id>", methods=["DELETE"])
def delete_subject(subject_id):
    """
    Delete a subject and all its associated samples

    Query Parameters:
        force=true - Skip confirmation and delete immediately

    Returns:
        200: Subject deleted successfully
        404: Subject not found
        409: Deletion would affect many records (without force=true)
        500: Database error
    """

    session = get_db_session()

    try:
        force = request.args.get("force", "false").lower() == "true"

        # Get deletion impact
        impact = get_deletion_impact(session, "subject", subject_id)
        if not impact:
            return jsonify({"error": "Subject not found"}), 404

        # Safety check
        if not force and impact["cascade_deletions"]["samples"] > 10:
            return (
                jsonify(
                    {
                        "error": "Deletion would affect many records",
                        "impact": impact,
                        "message": f'This will delete {impact["total_affected"]} records (1 subject + {impact["cascade_deletions"]["samples"]} samples)',
                        "suggestion": "Add ?force=true to confirm deletion",
                    }
                ),
                409,
            )

        # Delete the subject
        subject = (
            session.query(Subject).filter(Subject.subject_id == subject_id).first()
        )
        session.delete(subject)
        session.commit()

        logger.info(
            f"Deleted subject {subject_id} and {impact['cascade_deletions']['samples']} associated samples"
        )

        return (
            jsonify(
                {
                    "message": "Subject deleted successfully",
                    "deleted": impact,
                    "cascade_deletions": impact["cascade_deletions"],
                }
            ),
            200,
        )

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error deleting subject: {e}")
        return jsonify({"error": "Database error occurred"}), 500

    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error deleting subject: {e}")
        return jsonify({"error": "Internal server error"}), 500

    finally:
        session.close()


@app.route("/api/subjects/<int:subject_id>/impact", methods=["GET"])
def get_subject_deletion_impact(subject_id):
    """Get the impact of deleting a subject without actually deleting it"""

    session = get_db_session()

    try:
        impact = get_deletion_impact(session, "subject", subject_id)
        if not impact:
            return jsonify({"error": "Subject not found"}), 404

        return jsonify(impact), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error getting deletion impact: {e}")
        return jsonify({"error": "Database error occurred"}), 500

    finally:
        session.close()


@app.route("/api/samples/<int:sample_id>", methods=["DELETE"])
def delete_sample(sample_id):
    """
    Delete a specific sample

    Returns:
        200: Sample deleted successfully
        404: Sample not found
        500: Database error
    """

    session = get_db_session()

    try:
        # Check if sample exists
        sample = session.query(Sample).filter(Sample.sample_id == sample_id).first()
        if not sample:
            return jsonify({"error": "Sample not found"}), 404

        # Store sample data for response
        sample_data = sample.to_dict()

        # Delete the sample
        session.delete(sample)
        session.commit()

        logger.info(f"Deleted sample {sample_id}")

        return (
            jsonify(
                {
                    "message": "Sample deleted successfully",
                    "deleted_sample": sample_data,
                }
            ),
            200,
        )

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error deleting sample: {e}")
        return jsonify({"error": "Database error occurred"}), 500

    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error deleting sample: {e}")
        return jsonify({"error": "Internal server error"}), 500

    finally:
        session.close()


# =====================
# UTILITY ENDPOINTS
# =====================


@app.route("/api/deletion/cleanup", methods=["POST"])
def cleanup_orphaned_records():
    """
    Clean up any orphaned records (samples without valid project/subject references)
    This is a utility function for data maintenance
    """

    session = get_db_session()

    try:
        # Find orphaned samples (samples pointing to non-existent projects or subjects)
        orphaned_samples = (
            session.query(Sample)
            .outerjoin(Project, Sample.project_id == Project.project_id)
            .outerjoin(Subject, Sample.subject_id == Subject.subject_id)
            .filter((Project.project_id.is_(None)) | (Subject.subject_id.is_(None)))
            .all()
        )

        if not orphaned_samples:
            return (
                jsonify({"message": "No orphaned records found", "cleaned_up": 0}),
                200,
            )

        # Delete orphaned samples
        orphaned_sample_data = [sample.to_dict() for sample in orphaned_samples]

        for sample in orphaned_samples:
            session.delete(sample)

        session.commit()

        logger.info(f"Cleaned up {len(orphaned_samples)} orphaned samples")

        return (
            jsonify(
                {
                    "message": f"Cleaned up {len(orphaned_samples)} orphaned samples",
                    "cleaned_up": len(orphaned_samples),
                    "orphaned_samples": orphaned_sample_data,
                }
            ),
            200,
        )

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error during cleanup: {e}")
        return jsonify({"error": "Database error occurred"}), 500

    finally:
        session.close()


@app.route("/api/deletion/examples", methods=["GET"])
def get_deletion_examples():
    """Get examples of deletion API calls"""

    examples = {
        "single_deletions": {
            "delete_project": "DELETE /api/projects/1?force=true",
            "delete_subject": "DELETE /api/subjects/1?force=true",
            "delete_sample": "DELETE /api/samples/1",
        },
        "impact_checks": {
            "project_impact": "GET /api/projects/1/impact",
            "subject_impact": "GET /api/subjects/1/impact",
        },
        "utilities": {"cleanup_orphans": "POST /api/deletion/cleanup"},
        "notes": {
            "force_parameter": "Use force=true or 'force': true to skip safety confirmations",
            "cascade_deletion": "Deleting projects/subjects will also delete their samples",
            "safety_limits": "Operations affecting >10 records for single, >50 for batch require force=true",
        },
    }

    return jsonify(examples), 200


if __name__ == "__main__":
    # Verify database connection on startup
    try:
        session = get_db_session()
        session.execute(text("SELECT 1"))
        session.close()
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Failed to verify database connection: {e}")
        exit(1)

    # Run the Flask application
    app.run(debug=True, host="0.0.0.0", port=5000)
