"""Section API endpoints for section management.

This module provides REST API endpoints for section CRUD operations
including listing, creating, updating, and deleting sections.
"""

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import Ac