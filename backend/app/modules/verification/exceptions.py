from fastapi import HTTPException, status


class VerificationError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


class TargetNotFoundError(VerificationError):
    def __init__(self, entity_type: str = "record", entity_id: str = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_type.replace('_', ' ').capitalize()} record not found",
        )


class InvalidVerificationStateError(VerificationError):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class MandatoryRemarksRequiredError(VerificationError):
    def __init__(self, action: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Remarks are mandatory with at least 10 characters when action is '{action}'",
        )


class UnauthorizedSupervisorError(VerificationError):
    def __init__(self, detail: str = "Supervisor is not authorized to verify records for this employee"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
