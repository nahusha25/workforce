import logging

logger = logging.getLogger(__name__)

async def send_otp_sms(mobile: str, otp: str) -> bool:
    # In a real environment, this calls an SMS provider like Twilio, AWS SNS, etc.
    # For testing purposes only, write the OTP to a file so it's guaranteed to be visible
    with open("otp.txt", "w") as f:
        f.write(f"Your OTP is: {otp}")
    print(f"===================================\n--- MOCK SMS to {mobile} | OTP: {otp} ---\n===================================", flush=True)
    
    # Secure logging
    masked_mobile = f"XXXXXX{mobile[-4:]}" if len(mobile) >= 4 else "XXXX"
    logger.info(f"OTP SMS dispatched to {masked_mobile}")
    
    return True
