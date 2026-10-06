import logging
import os

logger = logging.getLogger(__name__)

async def send_otp_sms(mobile: str, otp: str) -> bool:
    # Guarantee OTP is written to both backend/otp.txt and root otp.txt regardless of CWD
    current_dir = os.path.dirname(os.path.abspath(__file__))  # backend/app/shared
    backend_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))  # backend
    root_dir = os.path.abspath(os.path.join(backend_dir, ".."))  # root

    for target in [
        os.path.join(backend_dir, "otp.txt"),
        os.path.join(root_dir, "otp.txt"),
        "otp.txt"
    ]:
        try:
            with open(target, "w") as f:
                f.write(f"Your OTP is: {otp}")
        except Exception:
            pass

    print(f"\n===================================\n--- MOCK SMS to {mobile} | OTP: {otp} ---\n===================================\n", flush=True)

    # Secure logging
    masked_mobile = f"XXXXXX{mobile[-4:]}" if len(mobile) >= 4 else "XXXX"
    logger.info(f"OTP SMS dispatched to {masked_mobile}")

    return True
