"""
Employee service — business logic for employee CRUD operations.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.core.security import hash_password
from app.services.user_service import get_user_by_email, create_user


def get_all_employees(db: Session) -> list[Employee]:
    """Retrieve all employees."""
    return db.query(Employee).all()


def get_employee_by_id(db: Session, employee_id: int) -> Employee:
    """Retrieve a single employee by ID. Raises 404 if not found."""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with id {employee_id} not found",
        )
    return employee


def create_employee(db: Session, data: EmployeeCreate) -> Employee:
    """Create a new employee and auto-provision a User account for login."""
    # 1. Check for duplicate employee record
    existing_employee = db.query(Employee).filter(Employee.email == data.email).first()
    if existing_employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Employee with email {data.email} already exists",
        )

    # 2. Extract password before converting schema to model dict
    employee_dict = data.model_dump()
    raw_password = employee_dict.pop("password", None)
    
    # 3. Create the User account if it doesn't already exist
    # This enables authentication (login) for the new employee
    if raw_password:
        existing_user = get_user_by_email(db, data.email)
        if not existing_user:
            create_user(
                db,
                email=data.email,
                password=raw_password,
                role="user", # Employees get the default user role
                full_name=data.name
            )

    # 4. Create the Employee profile record
    hashed_password = hash_password(raw_password) if raw_password else None
    employee = Employee(**employee_dict, hashed_password=hashed_password)
    
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def update_employee(db: Session, employee_id: int, data: EmployeeUpdate) -> Employee:
    """Update an existing employee. Supports partial updates."""
    employee = get_employee_by_id(db, employee_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)

    db.commit()
    db.refresh(employee)
    return employee


def delete_employee(db: Session, employee_id: int) -> Employee:
    """Delete an employee by ID. Returns the deleted employee."""
    employee = get_employee_by_id(db, employee_id)
    db.delete(employee)
    db.commit()
    return employee