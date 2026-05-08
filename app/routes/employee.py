"""
Employee CRUD routes.
Full REST API: GET (all), GET (by id), POST, PUT, DELETE.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeOut
from app.services.employee_service import (
    get_all_employees,
    get_employee_by_id,
    create_employee,
    update_employee,
    delete_employee,
)
from app.deps import get_db, get_current_user, require_super_admin
from app.models.user import User

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get(
    "/",
    response_model=list[EmployeeOut],
    summary="Get all employees",
)
def list_employees(db: Session = Depends(get_db)):
    """Retrieve all employees. Public endpoint."""
    return get_all_employees(db)


@router.get(
    "/{employee_id}",
    response_model=EmployeeOut,
    summary="Get employee by ID",
)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    """Retrieve a single employee by their ID."""
    return get_employee_by_id(db, employee_id)


@router.post(
    "/",
    response_model=EmployeeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new employee",
)
def create(
    data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new employee. Requires authentication."""
    return create_employee(db, data)


@router.put(
    "/{employee_id}",
    response_model=EmployeeOut,
    summary="Update an employee",
)
def update(
    employee_id: int,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing employee. Requires authentication."""
    return update_employee(db, employee_id, data)


@router.delete(
    "/{employee_id}",
    response_model=EmployeeOut,
    summary="Delete an employee",
)
def delete(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an employee by ID. Requires authentication."""
    return delete_employee(db, employee_id)