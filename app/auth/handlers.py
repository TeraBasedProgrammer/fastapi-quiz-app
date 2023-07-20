import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from datetime import datetime, timedelta

from app.config import settings

class VerifyAuth0Token():
    """Auth0 token verification class"""

    def __init__(self, token):
        self.token = token
        self.config = settings

        # This gets the JWKS from a given URL and does processing so you can
        # use any of the keys available
        jwks_url = f'https://{self.config.auth0_domain}/.well-known/jwks.json'
        self.jwks_client = jwt.PyJWKClient(jwks_url)

    def verify(self):
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
            print("invalid token error")
            raise HTTPException(status_code=401, detail='Invalid token or its signature has expired')

        return {"email": payload['email'], "auth0": True}


class AuthHandler():
    security = HTTPBearer()
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    secret = settings.jwt_secret

    def get_password_hash(self, password):
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password, scheme="bcrypt")

    def encode_token(self, user_email):
        payload = {
            'exp': datetime.utcnow() + timedelta(days=0, minutes=10),
            'iat': datetime.utcnow(),
            'sub': user_email
        }
        return jwt.encode(
            payload,
            self.secret,
            algorithm='HS256'
        )

    def decode_token(self, token):
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

    def auth_wrapper(self, auth: HTTPAuthorizationCredentials = Security(security)):
        return self.decode_token(auth.credentials)