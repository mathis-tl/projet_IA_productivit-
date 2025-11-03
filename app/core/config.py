from os import getenv

class Settings:
    JWT_SECRET = getenv("JWT_SECRET", "dev-secret-change-in-prod")
    JWT_EXPIRE_MIN = int(getenv("JWT_EXPIRE_MIN", "15"))  #expire au bout de 15 minutes
    JWT_REFRESH_EXPIRE_MIN = int(getenv("JWT_REFRESH_EXPIRE_MIN", "43200"))  #expire au bout d'1 mois

settings = Settings()