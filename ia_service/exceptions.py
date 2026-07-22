class IAServiceError(Exception):
    pass

class IAServiceUnavailable(IAServiceError):
    pass

class IAServiceUnauthorized(IAServiceError):
    pass

class IAServiceImageTooLarge(IAServiceError):
    pass

class IAServiceBadRequest(IAServiceError):
    pass
