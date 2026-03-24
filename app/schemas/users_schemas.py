from pydantic import BaseModel, Field, field_validator
from email_validator import validate_email, EmailNotValidError

class UserValidate(BaseModel):
    mail: str
    password: str
    
    @field_validator("mail")
    @classmethod
    def validate_mail(cls, value):
        try:
            validated_mail = validate_email(value)
            return validated_mail.normalized
        except EmailNotValidError as e:
            raise ValueError(str(e))
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in value):
            raise ValueError("Password must contain at least one number")
        if not any(c in "!@#$%^&*" for c in value):
            raise ValueError("Password must contain at least one special character")
        return value            
                       
    
    