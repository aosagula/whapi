from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.account import PizzeriaRole

# Roles asignables a empleados (owner es exclusivo del dueño via Account)
EMPLOYEE_ROLES = {PizzeriaRole.admin, PizzeriaRole.cashier, PizzeriaRole.cook, PizzeriaRole.delivery}


class EmpleadoInvite(BaseModel):
    """Datos para invitar un empleado a una pizzeria."""

    name: str
    email: EmailStr
    password: str
    role: PizzeriaRole

    def validate_role(self) -> None:
        if self.role not in EMPLOYEE_ROLES:
            raise ValueError(f"El rol '{self.role}' no se puede asignar a empleados")


class EmpleadoRoleUpdate(BaseModel):
    """Actualiza el rol de un empleado en la pizzeria."""

    role: PizzeriaRole

    def validate_role(self) -> None:
        if self.role not in EMPLOYEE_ROLES:
            raise ValueError(f"El rol '{self.role}' no se puede asignar a empleados")


class EmpleadoRead(BaseModel):
    """Representacion publica de un empleado con su rol en la pizzeria."""

    id: int
    account_id: int
    name: str
    email: EmailStr
    is_active: bool
    role: PizzeriaRole
    created_at: datetime

    model_config = {"from_attributes": True}
