class BaseAppError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

class AuthError(BaseAppError):
    def __init__(self, message: str):
        super().__init__("AUTH_ERROR", message)

class ForbiddenError(BaseAppError):
    def __init__(self, message: str):
        super().__init__("FORBIDDEN", message)

class NotFoundError(BaseAppError):
    def __init__(self, message: str):
        super().__init__("NOT_FOUND", message)

class ConflictError(BaseAppError):
    def __init__(self, message: str):
        super().__init__("CONFLICT", message)

class BusinessRuleError(BaseAppError):
    def __init__(self, message: str):
        super().__init__("BUSINESS_RULE_VIOLATION", message)
