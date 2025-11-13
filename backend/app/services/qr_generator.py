"""Utilities for generating QR codes as data URLs."""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Literal

import qrcode
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q

ErrorCorrectionLevel = Literal["L", "M", "Q", "H"]

_ERROR_CORRECTION_MAP = {
    "L": ERROR_CORRECT_L,
    "M": ERROR_CORRECT_M,
    "Q": ERROR_CORRECT_Q,
    "H": ERROR_CORRECT_H,
}


def generate_qr_data_url(
    data: str,
    *,
    error_correction: ErrorCorrectionLevel = "M",
    module_scale: int = 8,
    margin: int = 2,
) -> str:
    """Generate a PNG QR code as a data URL."""

    if not data:
        raise ValueError("Data is required to generate a QR code")

    try:
        error_correction_level = _ERROR_CORRECTION_MAP[error_correction.upper()]
    except KeyError as exc:  # pragma: no cover - defensive programming
        raise ValueError("Invalid error correction level") from exc

    qr = qrcode.QRCode(
        error_correction=error_correction_level,
        box_size=module_scale,
        border=margin,
    )
    qr.add_data(data)

    try:
        qr.make(fit=True)
    except qrcode.exceptions.DataOverflowError as exc:
        raise ValueError("Data too long to encode as a QR code") from exc

    image = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


__all__ = ["generate_qr_data_url"]
