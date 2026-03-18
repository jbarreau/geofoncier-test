class PublicKeyMixin:
    jwt_public_key: str = ""
    jwt_public_key_path: str = ""

    @property
    def public_key_content(self) -> str:
        if self.jwt_public_key:
            return self.jwt_public_key
        if self.jwt_public_key_path:
            with open(self.jwt_public_key_path) as f:
                return f.read()
        raise ValueError(
            "No JWT public key configured (set JWT_PUBLIC_KEY or JWT_PUBLIC_KEY_PATH)"
        )
