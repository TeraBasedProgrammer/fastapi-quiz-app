from datetime import datetime, timedelta
from typing import Dict, Optional

import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, settings
from app.database import get_async_session


class VerifyAuth0Token:
    """Auth0 token verification class"""

    def __init__(self, token: str) -> None:
        self.token: str = token
        self.config: Settings = settings

        # This gets the JWKS from a given URL and does processing so you can
        # use any of the keys available
        jwks_url = f'https://{self.config.auth0_domain}/.well-known/jwks.json'
        self.jwks_client = jwt.PyJWKClient(jwks_url)

    def verify(self) -> Optional[Dict[str, bool]]:
        # This gets the 'kid' from the passed token
        try:
            self.signing_key = self.jwks_client.get_signing_key_from_jwt(
                self.token
            ).key
        except jwt.exceptions.PyJWKClientError as error:
            raise HTTPException(status_code=401, detail='Invalid token payload')
        except jwt.exceptions.DecodeError as error:
            raise HTTPException(status_code=401, detail='Token decode error')

        try:
            payload = jwt.decode(
                self.token,
                self.signing_key,
                algorithms=self.config.auth0_algorithms,
                audience=self.config.auth0_api_audience,
                issuer=self.config.auth0_issuer,
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail='Invalid token or its signature has expired')

        return {"email": payload['email'], "auth0": True}


class AuthHandler:
    security = HTTPBearer()
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    secret: str = settings.jwt_secret

    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password, scheme="bcrypt")

    def encode_token(self, user_email: str) -> str:
        payload = {
            'exp': datetime.utcnow() + timedelta(days=0, minutes=60),
            'iat': datetime.utcnow(),
            'sub': user_email
        }
        return jwt.encode(
            payload,
            self.secret,
            algorithm='HS256'
        )

    def decode_token(self, token: str) -> Optional[Dict[str, bool]]:
        try:
            payload = jwt.decode(token, self.secret, algorithms=['HS256'])
            return {"email": payload['sub'], "auth0": False}
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail='Signature has expired')
        except jwt.InvalidTokenError as e: 
            # If token doesn't have the default structure, funcion delegates token verification to the auth0 jwt validator
            auth0_decoder = VerifyAuth0Token(token)
            decoded_data = auth0_decoder.verify()
            if decoded_data:
                return decoded_data
            raise HTTPException(status_code=401, detail='Invalid token')

    async def auth_wrapper(self, session: AsyncSession = Depends(get_async_session), 
                           auth: HTTPAuthorizationCredentials = Security(security)) -> Optional[Dict[str, bool]]:
        # Check if there are no registered users to this email address

        # Local import to avoid circular import error
        from app.users.services import UserRepository
        user_data = self.decode_token(auth.credentials)
        
        if user_data['auth0']:
            crud = UserRepository(session)
            await crud.error_or_create(user_data['email'])

        return user_data
