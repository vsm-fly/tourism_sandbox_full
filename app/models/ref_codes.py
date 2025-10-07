from datetime import datetime
from sqlalchemy import CheckConstraint, UniqueConstraint
from ..extensions import db

class CodeType(db.Model):
    __tablename__ = "code_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<CodeType {self.name!r}>"

class RefCode(db.Model):
    __tablename__ = "ref_codes"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(5), nullable=False, unique=True, index=True)
    name = db.Column(db.String(128), nullable=False)

    type_id = db.Column(db.Integer, db.ForeignKey("code_types.id", ondelete="RESTRICT"), nullable=False)
    type = db.relationship("CodeType", backref=db.backref("codes", lazy="dynamic"))

    status = db.Column(db.Enum("active", "inactive", name="refcode_status"), nullable=False, default="active")

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("code", name="uq_ref_codes_code"),
        # Примечание: CHECK работает в MySQL 8.0.16+; в старых версиях игнорируется.
        CheckConstraint("length(code) = 5", name="ck_ref_codes_code_len5"),
    )

    def __repr__(self) -> str:
        return f"<RefCode {self.code} {self.name!r}>"
