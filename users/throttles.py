from rest_framework.throttling import AnonRateThrottle


class LoginThrottle(AnonRateThrottle):
    """10 intentos por minuto por IP en el endpoint de login."""
    scope = 'login'


class OtpSendThrottle(AnonRateThrottle):
    """3 solicitudes por minuto por IP para enviar códigos OTP (password reset)."""
    scope = 'otp_send'


class OtpVerifyThrottle(AnonRateThrottle):
    """5 verificaciones por minuto por IP para validar códigos OTP (login-2fa, reset confirm)."""
    scope = 'otp_verify'
